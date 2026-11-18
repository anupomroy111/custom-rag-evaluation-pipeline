"""Red-team paired mutation + metamorphic testing (V2.1 §6).

Scenarios are structured tuples; claims are rendered from them. Mutations are
applied to the tuple, so the expected semantic relation (contradicts /
equivalent / unsupported) is known by construction — no label guessing.

Metamorphic properties checked:
  equivalent   → verification outcome must be preserved
  contradicts  → outcome must change AND must not be SUPPORTED
  unsupported  → outcome must not be SUPPORTED

Deterministic mode can only decide lexical/numeric/modality mutations; role
swaps require the semantic stage (documented, tested in semantic/mocked mode).
"""

from dataclasses import dataclass, field
from typing import Callable

from .verify.engine import VerificationEngine

PAST = {"acquire": "acquired", "approve": "approved", "maintain": "maintained",
        "own": "owned", "review": "reviewed", "ship": "shipped",
        "store": "stored", "delete": "deleted"}
SYMMETRIC = {"met", "married", "equals"}


@dataclass
class Scenario:
    agent: str
    predicate: str
    patient: str
    negation: bool = False
    modality: str = "assertive"
    number: str = ""
    unit: str = ""
    extra: str = ""

    def render(self) -> str:
        verb = PAST.get(self.predicate, self.predicate + "ed")
        modal = {"possible": "may ", "probable": "will likely ",
                 "assertive": "", "definite": "will definitely "}[self.modality]
        neg = "did not " if self.negation else ""
        if self.modality in ("possible", "probable", "definite"):
            verb = self.predicate
            neg = "not " if self.negation else ""
        tail = f" {self.number} {self.unit}".rstrip() if self.number else ""
        return f"{self.agent} {modal}{neg}{verb} {self.patient}{tail}."


@dataclass
class Mutation:
    name: str
    relation: str  # contradicts | equivalent | unsupported
    apply: Callable[["Scenario"], "Scenario"]
    deterministic_decidable: bool = True


def _flip_negation(s: Scenario) -> Scenario:
    return Scenario(**{**s.__dict__, "negation": not s.negation})


def _double_negation(s: Scenario) -> Scenario:
    inner = Scenario(**{**s.__dict__, "negation": not s.negation}).render()
    return Scenario(**{**s.__dict__, "extra": f"It is not true that {inner[0].lower() + inner[1:]}"})


def _swap_roles(s: Scenario) -> Scenario:
    return Scenario(**{**s.__dict__, "agent": s.patient, "patient": s.agent})


def _sub_entity(s: Scenario) -> Scenario:
    return Scenario(**{**s.__dict__, "agent": "Zenith Corp"})


def _number(s: Scenario) -> Scenario:
    return Scenario(**{**s.__dict__, "number": str(int(s.number) + 7)})


def _unit(s: Scenario) -> Scenario:
    swap = {"minutes": "hours", "hours": "minutes", "MB": "GB", "GB": "MB",
            "days": "hours", "seconds": "minutes"}
    return Scenario(**{**s.__dict__, "unit": swap.get(s.unit, s.unit + "s")})


def _escalate(s: Scenario) -> Scenario:
    return Scenario(**{**s.__dict__, "modality": "definite"})


def _passive(s: Scenario) -> Scenario:
    verb = PAST.get(s.predicate, s.predicate + "ed")
    neg = "not " if s.negation else ""
    text = f"{s.patient} was {neg}{verb} by {s.agent}."
    return Scenario(**{**s.__dict__, "extra": text})


MUTATIONS = [
    Mutation("negation_flip", "contradicts", _flip_negation),
    Mutation("double_negation", "equivalent", _double_negation, False),
    Mutation("agent_patient_swap", "contradicts", _swap_roles, False),
    Mutation("entity_substitution", "contradicts", _sub_entity, False),
    Mutation("number_manipulation", "contradicts", _number),
    Mutation("unit_manipulation", "contradicts", _unit),
    Mutation("modality_escalation", "unsupported", _escalate),
    Mutation("passive_paraphrase", "equivalent", _passive, False),
]

BANK = [
    Scenario("Company A", "acquire", "Company B", negation=True),
    Scenario("Alice", "approve", "Bob's request"),
    Scenario("The gateway", "store", "the session cache", number="2", unit="MB"),
    Scenario("The scheduler", "maintain", "the health probes", number="10", unit="seconds"),
    Scenario("The platform", "ship", "the audit export", number="90", unit="days"),
    Scenario("Vault", "store", "application secrets"),
    Scenario("The migration", "cause", "brief downtime", modality="possible"),
    Scenario("Team Alpha", "review", "Team Beta's code"),
]


def render_claim(s: Scenario) -> str:
    return s.extra or s.render()


def run_redteam(engine: VerificationEngine, mode: str = "deterministic",
                scenarios: list[Scenario] | None = None) -> dict:
    records = []
    for si, base in enumerate(scenarios or BANK):
        ctx = [(f"rt{si}-p0", base.render())]
        base_result = engine.verify_claims([render_claim(base)], ctx, mode=mode)
        base_status = base_result.verdicts[0].status.value
        for mut in MUTATIONS:
            if mode == "deterministic" and not mut.deterministic_decidable:
                continue
            if mut.name in ("number_manipulation", "unit_manipulation") and not base.number:
                continue
            mutated = mut.apply(base)
            claim = render_claim(mutated)
            if mut.name == "double_negation":
                claim = mutated.extra
            result = engine.verify_claims([claim], ctx, mode=mode)
            status = result.verdicts[0].status.value
            if mut.relation == "equivalent":
                ok = status == base_status
            elif mut.relation == "contradicts":
                ok = status != base_status and status != "SUPPORTED"
            else:
                ok = status != "SUPPORTED"
            records.append({
                "scenario": si, "mutation": mut.name, "relation": mut.relation,
                "base_status": base_status, "mutated_status": status, "pass": ok,
                "claim": claim,
            })
    passed = sum(1 for r in records if r["pass"])
    return {
        "mode": mode,
        "n_pairs": len(records),
        "passed": passed,
        "pass_rate": round(passed / len(records), 4) if records else None,
        "records": records,
    }