"""Deterministic, LLM-free evidence checks.

These run BEFORE expensive semantic verification and produce flags, not final
verdicts. A flag is a signal of possible contradiction; final status resolution
happens in the verification engine (semantic cross-check + disagreement rules).
"""

import re

from .schemas import NumericalValue

NEGATION_RE = re.compile(
    r"\b(?:not|never|no|without|cannot|can't|denied|failed to|isn't|aren't|won't|"
    r"doesn't|don't|didn't|did not|does not|will not|is not|are not|was not|were not|"
    r"disabled|excluded|blocked|prohibited|forbidden|lacks?)\b",
    re.IGNORECASE,
)

MODALITY_CUES = {
    "possible": r"\b(?:may|might|could|possibly|perhaps|estimated|alleged|planned|suggests?|"
                r"roughly|approximately)\b",
    "probable": r"\b(?:likely|probably|expected to)\b",
    "definite": r"\b(?:must|will|definitely|always|confirmed|proven|certainly|exactly)\b",
}
MODALITY_RANK = {"possible": 0, "probable": 1, "assertive": 2, "definite": 3}

TIME_UNITS = {"second": 1, "seconds": 1, "sec": 1, "s": 1,
              "minute": 60, "minutes": 60, "min": 60, "mins": 60,
              "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600,
              "day": 86400, "days": 86400, "week": 604800, "weeks": 604800}
DATA_UNITS = {"byte": 1 / 1e6, "bytes": 1 / 1e6, "kb": 1 / 1e3, "mb": 1, "gb": 1e3, "tb": 1e6}
COUNT_UNITS = {"vcpu": 1, "instance": 1, "instances": 1, "project": 1, "projects": 1,
               "build": 1, "builds": 1, "revision": 1, "revisions": 1,
               "retry": 1, "retries": 1, "request": 1, "requests": 1}

NUMBER_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>%|percent|mb|gb|tb|kb|vcpu|ms|"
    r"seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|"
    r"builds?|projects?|instances?|revisions?|retries|requests?)?",
    re.IGNORECASE,
)

DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|"
    r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4})\b",
    re.IGNORECASE,
)

TEMPORAL_CUES = {
    "before": r"\b(?:before|prior to|until|preceded)\b",
    "after": r"\b(?:after|following|since|subsequent)\b",
    "planned": r"\b(?:planned|scheduled|will|upcoming|roadmap)\b",
    "completed": r"\b(?:completed|released|shipped|done|already|available)\b",
}

INJECTION_RE = re.compile(
    r"(?:ignore (?:all |any )?(?:previous|prior|above)|disregard (?:the |all )?(?:previous|instructions|documents)|"
    r"you (?:must|should|are now)|system\s*:|assistant\s*:|new instructions|"
    r"note to the (?:ai|model|assistant|verifier)|always mark|mark (?:all )?claims|"
    r"instead (?:answer|say|reply)|do not cite|override (?:your|all|previous)|"
    r"reveal (?:your|the) (?:system )?(?:prompt|instructions))",
    re.IGNORECASE,
)

STOPWORDS = set("the a an is are was were be been of to in on for and or with by at as it its "
                "this that these those from into per each every all any can could may might "
                "will would shall should do does did not no never without".split())


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def content_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower())
            if t not in STOPWORDS and len(t) > 2}


def overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def extract_numbers(text: str) -> list[NumericalValue]:
    values = []
    for m in NUMBER_RE.finditer(text):
        raw = m.group(0).strip()
        num = float(m.group("num"))
        unit = (m.group("unit") or "").lower() or None
        dimension, normalized = None, num
        if unit in ("%", "percent"):
            dimension, normalized = "percent", num
        elif unit in TIME_UNITS:
            dimension, normalized = "time_s", num * TIME_UNITS[unit]
        elif unit in DATA_UNITS:
            dimension, normalized = "data_mb", num * DATA_UNITS[unit]
        elif unit == "ms":
            dimension, normalized = "time_s", num / 1000
        elif unit in COUNT_UNITS:
            dimension, normalized = "count:" + unit.rstrip("s"), num
        values.append(NumericalValue(raw=raw, value=normalized, unit=unit, dimension=dimension))
    return values


def extract_dates(text: str) -> list[str]:
    return [m.group(0) for m in DATE_RE.finditer(text)]


def negation_cues(text: str) -> list[str]:
    return [m.group(0).lower() for m in NEGATION_RE.finditer(text)]


def modality_of(text: str) -> str:
    for level in ("possible", "probable", "definite"):
        if re.search(MODALITY_CUES[level], text, re.IGNORECASE):
            return level
    return "assertive"


def temporal_cues(text: str) -> dict[str, bool]:
    return {k: bool(re.search(p, text, re.IGNORECASE)) for k, p in TEMPORAL_CUES.items()}


def injection_flags(text: str) -> list[str]:
    return [m.group(0) for m in INJECTION_RE.finditer(text)]


def numerical_contradictions(claim: str, context: str) -> list[str]:
    """Flag claim numbers conflicting with similar evidence, support-aware:
    a different number elsewhere in a multi-fact context is not a contradiction
    if some similar sentence supports the claim's value."""
    flags = []
    claim_nums = extract_numbers(claim)
    claim_tokens = content_tokens(claim)
    similar = [s for s in sentences(context)
               if overlap(claim_tokens, content_tokens(s)) >= 0.5]
    for cn in claim_nums:
        if cn.dimension is None:
            continue
        supported = any(
            sn.dimension == cn.dimension and abs(sn.value - cn.value) <= 1e-9
            for s in similar for sn in extract_numbers(s))
        if supported:
            continue
        for sent in similar:
            for sn in extract_numbers(sent):
                if sn.dimension == cn.dimension and abs(sn.value - cn.value) > 1e-9:
                    flags.append(
                        f"numerical: claim '{cn.raw}' vs context '{sn.raw}' in similar sentence"
                    )
    return flags


def _clauses(sent: str) -> list[str]:
    return [c for c in re.split(r"[,;—–]|\bbut\b", sent) if c.strip()]


def negation_flip_flags(claim: str, context: str) -> list[str]:
    """Clause-scoped, support-aware negation polarity comparison.

    Polarity uses cue-count parity so simple double negations cancel; embedded
    scopes are handled by negation_scope_ambiguous (UNCERTAIN), not guessed.
    """
    flags = []
    claim_neg = len(negation_cues(claim)) % 2 == 1
    claim_tokens = content_tokens(claim)
    for sent in sentences(context):
        if overlap(claim_tokens, content_tokens(sent)) < 0.5:
            continue
        clause = max(_clauses(sent),
                     key=lambda c: overlap(claim_tokens, content_tokens(c)))
        if claim_neg != (len(negation_cues(clause)) % 2 == 1):
            flags.append(f"negation: claim polarity differs from similar sentence '{sent[:80]}'")
    return flags


def numerical_support(claim: str, context: str) -> bool:
    """Positive deterministic evidence: a similar sentence carries the same
    normalized value (unit conversions included) AND the same quantity context
    (core tokens match). Used only to affirm numeric claims in deterministic
    mode; never affirms non-numeric claims."""
    claim_nums = [n for n in extract_numbers(claim) if n.dimension]
    if not claim_nums:
        return False

    def core(text: str) -> set[str]:
        nums = extract_numbers(text)
        drop = set()
        for n in nums:
            drop.update(content_tokens(n.raw))
        # keep function words: extra causal/temporal/scope material ("from",
        # "because", "since") must block affirmation, not be filtered away
        return {t for t in re.findall(r"[a-z0-9_]+", text.lower())
                if t not in drop and not t.isdigit()}

    claim_core = core(claim)
    for sent in sentences(context):
        sent_core = core(sent)
        # the claim's entire core content must be covered by the evidence
        # sentence; extra causal/temporal/scope material blocks affirmation
        if not claim_core or not claim_core <= sent_core:
            continue
        sent_nums = extract_numbers(sent)
        if all(any(sn.dimension == cn.dimension and abs(sn.value - cn.value) <= 1e-9
                   for sn in sent_nums) for cn in claim_nums):
            return True
    return False


DUMMY_PRONOUNS = {"it", "there", "this", "that", "they", "he", "she", "them"}


def clean_entities(entities: list[str]) -> list[str]:
    """Drop dummy pronouns; coreference must be resolved to named entities."""
    return [e for e in entities if e.lower() not in DUMMY_PRONOUNS]


def transitive_chain_flags(claim, events: list) -> list[str]:
    """Multi-hop composition for transitive predicates: a complete evidence
    chain supports the claim; a reversed chain contradicts it; a missing link
    yields no flag (abstain)."""
    transitive = {"depend", "depends", "owned", "contains"}
    cl = lemma(claim.predicate.split()[0]) if claim.predicate else ""
    if cl not in {"depend"} or not (claim.agent and claim.patient):
        return []
    edges = {(e.agent.lower(), e.patient.lower()) for e in events
             if e.predicate and lemma(e.predicate.split()[0]) == cl
             and e.agent and e.patient}
    a, b = claim.agent.lower(), claim.patient.lower()
    if (a, b) in edges:
        return []

    def reachable(src: str, dst: str) -> bool:
        seen, stack = {src}, [src]
        while stack:
            cur = stack.pop()
            for (x, y) in edges:
                if x == cur and y not in seen:
                    if y == dst:
                        return True
                    seen.add(y)
                    stack.append(y)
        return False

    if reachable(a, b):
        return [f"multihop-support: complete chain for '{claim.original_claim[:60]}'"]
    if reachable(b, a):
        return [f"multihop: reversed dependency chain for '{claim.original_claim[:60]}'"]
    return []


def negation_consistency(claim, events: list) -> list[str]:
    """Semantic negation comparison over normalized event tuples (LLM-resolved
    double negation / scope), matched by predicate + shared entities."""
    flags = []
    cl = lemma(claim.predicate)
    claim_ents = {e.lower() for e in claim.entities}
    for ev in events:
        if lemma(ev.predicate) != cl:
            continue
        ev_ents = {e.lower() for e in ev.entities}
        if claim_ents and ev_ents and not (claim_ents & ev_ents):
            continue
        if claim.negation != ev.negation:
            flags.append(f"negation: claim polarity differs from event '{ev.event_id}'")
    return flags


def modality_flags(claim: str, context: str) -> list[str]:
    flags = []
    claim_rank = MODALITY_RANK[modality_of(claim)]
    claim_tokens = content_tokens(claim)
    similar = [s for s in sentences(context)
               if overlap(claim_tokens, content_tokens(s)) >= 0.6]
    # support-aware: any equally-strong or stronger similar sentence clears the flag
    if any(MODALITY_RANK[modality_of(s)] >= claim_rank for s in similar):
        return flags
    for sent in similar:
        sent_rank = MODALITY_RANK[modality_of(sent)]
        if claim_rank > sent_rank + 1:
            # dropping an approximation hedge on an equal number is tolerated
            if (re.search(r"\b(?:roughly|approximately)\b", sent, re.IGNORECASE)
                    and modality_of(claim) == "assertive"
                    and _numbers_equal(claim, sent)):
                continue
            flags.append(
                f"modality: claim '{modality_of(claim)}' overstates context '{modality_of(sent)}'"
            )
    return flags


def _numbers_equal(a: str, b: str) -> bool:
    na = [(n.dimension, n.value) for n in extract_numbers(a) if n.dimension]
    nb = [(n.dimension, n.value) for n in extract_numbers(b) if n.dimension]
    return bool(na) and na == nb


def temporal_flags(claim: str, context: str) -> list[str]:
    flags = []
    claim_tokens = content_tokens(claim)
    cc = temporal_cues(claim)
    similar = [s for s in sentences(context)
               if overlap(claim_tokens, content_tokens(s)) >= 0.6]
    for sent in similar:
        st = temporal_cues(sent)
        if cc["before"] and st["after"] or cc["after"] and st["before"]:
            # support-aware: same-direction evidence elsewhere clears the flag
            if any(temporal_cues(s)["before"] == cc["before"]
                   and temporal_cues(s)["after"] == cc["after"] for s in similar):
                continue
            flags.append(f"temporal: before/after reversal vs '{sent[:80]}'")
        if cc["planned"] and st["completed"] or cc["completed"] and st["planned"]:
            if any(temporal_cues(s)["planned"] == cc["planned"]
                   and temporal_cues(s)["completed"] == cc["completed"] for s in similar):
                continue
            flags.append(f"temporal: planned/completed reversal vs '{sent[:80]}'")
    claim_dates, sent_dates = extract_dates(claim), extract_dates(context)
    if claim_dates and sent_dates and set(claim_dates) != set(sent_dates):
        if set(claim_dates) <= set(sent_dates):
            return flags
        if overlap(claim_tokens, content_tokens(context)) >= 0.6:
            flags.append(f"temporal: dates {claim_dates} vs context {sent_dates}")
    return flags


def role_reversal_flags(subject: str, predicate: str, object_: str, context: str) -> list[str]:
    """Detect object-before-subject ordering around the same predicate,
    support-aware: a sentence with the claim's own order clears the flag."""
    if not (subject and predicate and object_):
        return []
    flags = []
    s, o = subject.lower(), object_.lower()
    pred_tokens = content_tokens(predicate)
    object_candidates = [o, o.replace("'s", ""), o.split()[0].replace("'s", "")]
    for sent in sentences(context):
        low = sent.lower()
        if s not in low:
            continue
        obj = next((c for c in object_candidates if c and c in low), None)
        if obj is None:
            continue
        if not pred_tokens or not (pred_tokens & content_tokens(sent)):
            continue
        if low.find(obj) < low.find(s):
            flags.append(f"role_reversal: object precedes subject in '{sent[:80]}'")
    if flags:
        for sent in sentences(context):
            low = sent.lower()
            if s not in low:
                continue
            obj = next((c for c in object_candidates if c and c in low), None)
            if obj is not None and low.find(s) < low.find(obj):
                return []
    return flags


def clean_evidence(context: str) -> str:
    """Drop injection-bearing sentences: instructions are not evidence."""
    return "\n".join(s for s in sentences(context) if not injection_flags(s))


def entity_flags(claim: str, entities: list[str], context: str) -> list[str]:
    """Flag claim entities absent from every lexically-similar evidence sentence.

    Detects missing attribution evidence (NOT_SUPPORTED signal); distinguishing
    wrong-vs-right attribution between present entities needs semantic SPO analysis.
    """
    flags = []
    claim_tokens = content_tokens(claim)
    similar = [s for s in sentences(context)
               if overlap(claim_tokens, content_tokens(s)) >= 0.3]
    if not similar:
        return flags
    all_sentences = sentences(context)
    for entity in entities:
        # multi-hop evidence may name the entity in a different sentence;
        # only flag when the entity appears nowhere in the context
        if not any(entity.lower() in s.lower() for s in all_sentences):
            flags.append(f"entity: '{entity}' absent from evidence")
    return flags


def map_citations(claim_tokens: set[str], entities: list[str],
                  passages: list[tuple[str, str]]) -> list[str]:
    """Deterministic claim→passage mapping over retrieved ids only."""
    keyed = set(t.lower() for t in entities) | claim_tokens
    scored = []
    for pid, text in passages:
        score = overlap(keyed, content_tokens(text))
        if score > 0.3:
            scored.append((score, pid))
    scored.sort(reverse=True)
    return [pid for _, pid in scored[:2]]


MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def lemma(predicate: str) -> str:
    p = predicate.lower().strip().replace("'s", "")
    for suffix in ("ing", "ed", "s"):
        if p.endswith(suffix) and len(p) > len(suffix) + 2:
            return p[:-len(suffix)]
    return p


def normalize_date(text: str) -> tuple[int, int, int] | None:
    text = text.strip().lower()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.match(r"([a-z]{3})[a-z]*\.?\s+(\d{4})", text)
    if m and m.group(1) in MONTHS:
        return int(m.group(2)), MONTHS[m.group(1)], 1
    m = re.match(r"(\d{1,2})\s+([a-z]{3})[a-z]*\.?\s+(\d{4})", text)
    if m and m.group(2) in MONTHS:
        return int(m.group(3)), MONTHS[m.group(2)], int(m.group(1))
    return None


def negation_scope_ambiguous(text: str) -> bool:
    """Embedded negation/quantifier scopes the cue-parity heuristic cannot parse."""
    return bool(re.search(
        r"\b(?:not (?:unlikely|impossible|uncommon|without)|failed to (?:deny|reject)|"
        r"no reason to (?:doubt|believe)|"
        r"not\b[^.]{0,40}\b(?:only|merely|just)\b|"
        r"\b(?:only|merely|just)\b[^.]{0,40}\bnot\b|"
        r"\b(?:may|might|could)\s+not\s+be\s+(?:un|in|im|ir)[a-z]+|"
        r"doesn't (?:mean|imply)|cannot (?:rule out|exclude))\b", text, re.IGNORECASE))


def role_consistency(claim, events: list) -> list[str]:
    """Agent-patient / subject-object swap detection over normalized tuples."""
    flags = []
    ca, cp = claim.agent.lower(), claim.patient.lower()
    if not (ca and cp and claim.predicate):
        return flags
    cl = lemma(claim.predicate)
    for ev in events:
        if lemma(ev.predicate) != cl:
            continue
        ea, ep = ev.agent.lower(), ev.patient.lower()
        if not (ea and ep):
            continue
        if ca == ep and cp == ea:
            if {ca, cp} == {ea, ep} and (ca, cp) != (ea, ep):
                flags.append(f"role: agent-patient swapped vs event '{ev.event_id}'")
    return flags


FUNCTIONAL_RELATIONS = {"own", "owns", "owned", "author", "authored", "maintain",
                        "maintains", "store", "stores", "develop", "developed",
                        "fund", "funded"}


def attribution_consistency(claim, events: list) -> list[str]:
    """Holder mismatch contradicts only for functional relations (single-holder
    by convention, documented in docs/BENCHMARK_METHODOLOGY.md). Different
    relations or non-functional relations (locations, enforcement) are silence
    → left to the semantic judge's NOT_SUPPORTED rule."""
    flags = []
    for ca in claim.attributions:
        if not (ca.relation and ca.holder and ca.target):
            continue
        if lemma(ca.relation) not in FUNCTIONAL_RELATIONS:
            continue
        for ev in events:
            for ea in ev.attributions:
                if (lemma(ea.relation) == lemma(ca.relation)
                        and ea.target.lower() == ca.target.lower()
                        and ea.holder.lower() != ca.holder.lower()):
                    flags.append(
                        f"attribution: {ca.relation} holder '{ca.holder}' vs evidence "
                        f"'{ea.holder}' for '{ca.target}'")
    return flags


def temporal_consistency(claim, events: list) -> list[str]:
    flags = []
    cc = temporal_cues(claim.original_claim)
    for ev in events:
        ec = {c.lower() for c in ev.temporal_cues}
        if cc["before"] and "after" in ec or cc["after"] and "before" in ec:
            flags.append(f"temporal: before/after reversal vs event '{ev.event_id}'")
        if cc["planned"] and ev.state == "completed":
            flags.append(f"temporal: claim planned vs event completed '{ev.event_id}'")
        if cc["completed"] and ev.state == "planned":
            flags.append(f"temporal: claim completed vs event planned '{ev.event_id}'")
    cd = [normalize_date(d) for d in claim.temporal_references]
    cd = [d for d in cd if d]
    ed = [normalize_date(d) for ev in events for d in ev.temporal_cues
          if normalize_date(d)]
    if cd and ed and set(cd) != set(ed) and not set(cd) <= set(ed):
        flags.append(f"temporal: normalized dates {cd} vs evidence {ed}")
    return flags


def tuple_equivalence(claim, events: list) -> bool:
    """Exact normalized-tuple match: strong paraphrase-equivalence signal."""
    cl = lemma(claim.predicate)
    for ev in events:
        if (lemma(ev.predicate) == cl
                and claim.agent.lower() == ev.agent.lower()
                and claim.patient.lower() == ev.patient.lower()
                and claim.negation == ev.negation
                and MODALITY_RANK.get(claim.modality, 2) == MODALITY_RANK.get(ev.modality, 2)):
            return True
    return False