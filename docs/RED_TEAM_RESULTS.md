# Red-Team Results (V2.1)

## Program design

`ragpipe/redteam.py` renders claims from structured scenario tuples and applies
paired mutations whose expected semantic relation is known by construction:

| Mutation | Relation | Deterministic-decidable |
|---|---|---|
| negation_flip | contradicts | yes |
| double_negation | equivalent | no (scope resolution needs semantic stage) |
| agent_patient_swap | contradicts | no (needs role tuples) |
| entity_substitution | contradicts | no (needs entity semantics) |
| number_manipulation | contradicts | yes |
| unit_manipulation | contradicts | yes |
| modality_escalation | unsupported | yes |
| passive_paraphrase | equivalent | no (surface order vs roles) |

Metamorphic properties: equivalent → verification outcome preserved;
contradicts → outcome changed AND not SUPPORTED; unsupported → not SUPPORTED.
Both mutation directions are covered by the fixture datasets (negation
removal/insertion pairs, swap pairs with SUPPORTED controls).

## Executed results — deterministic mode (offline, zero API calls)

- Pairs executed: 22 (8 scenarios × decidable mutations)
- Passed: 22 / 22 (pass rate 1.000)
- Command: `python -m ragpipe.cli redteam --mode deterministic`
- Raw records: `reports/v2_1/redteam_deterministic.json`

Interpretation: the deterministic layer preserves outcomes under equivalent
numeric/unit paraphrases and changes outcomes (never to SUPPORTED) under
negation/number/unit/modality mutations. This is a metamorphic consistency
result on the scenario bank, not a coverage claim over natural language.

## Not run (labeled)

- `redteam --mode semantic` (live): NOT RUN in this release — daily quota was
  reserved for the ablation grid and held-out benchmark. The semantic-stage
  role/paraphrase properties are instead exercised by the held-out fixture
  families (F11–F20 include swap, passive-paraphrase and double-negation cases)
  and by mocked-judge unit tests.
- Mocked semantic red-team runs exist only inside `tests/` and are never
  reported as benchmark results.

## Known failure modes surfaced by the program

- Surface word-order role heuristics false-positive on passive paraphrases;
  resolved in semantic mode by normalized event tuples (tuple equivalence
  clears surface flags).
- Cue-parity negation cannot parse embedded scopes ("not merely", "not only");
  these return UNCERTAIN via `negation_scope_ambiguous` rather than guessing.
- Entity substitution is only detectable semantically; deterministic mode
  abstains (UNCERTAIN) instead of approving.