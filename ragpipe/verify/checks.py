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
    """Clause-scoped, support-aware negation polarity comparison."""
    flags = []
    claim_neg = bool(negation_cues(claim))
    claim_tokens = content_tokens(claim)
    for sent in sentences(context):
        if overlap(claim_tokens, content_tokens(sent)) < 0.5:
            continue
        clause = max(_clauses(sent),
                     key=lambda c: overlap(claim_tokens, content_tokens(c)))
        if claim_neg != bool(negation_cues(clause)):
            flags.append(f"negation: claim polarity differs from similar sentence '{sent[:80]}'")
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