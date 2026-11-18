# Failure Analysis (V2.1 hardening)

Root-cause analysis of held-out misses from the executed grid traces
(`reports/v2_1/grid_mixed-replay_*.json`, prompt v2.1, held-out hybrid+rerank).
Held-out data was NOT modified; fixes were developed and measured on NEW
development families F21–F24 (prompt v2.2), per the no-test-set-optimization rule.

## 1. Scope ambiguity — held-out exact 0.000 (10 cases)

Root causes:
- R1: the semantic judge resolved "not only / not merely" claims to
  NOT_SUPPORTED/CONTRADICTED instead of abstaining; our scope-ambiguity flag
  only forced UNCERTAIN when the semantic verdict was SUPPORTED.
- R2: the scope regex missed gapped forms ("not deleted only after 30 days")
  and modal stacks ("may not be unavailable").

Fixes (v2.2): scope ambiguity now forces UNCERTAIN in ALL modes; regex extended
(gapped not…only/merely/just, modal stacks). Judge prompt makes UNCERTAIN
mandatory for ambiguous scope.
Measured on new dev family F21 (5 cases, fresh-live): 5/5 exact, FAR 0, FRR 0.
Held-out re-measurement with v2.2: BLOCKED_BY_QUOTA (see §6).

## 2. Negation flip — held-out exact 0.667 (7 UNCERTAIN on double negations)

Root causes:
- R3: judge `negation` field carried surface polarity, so double-negated claims
  mismatched evidence-event polarity → disagreement → UNCERTAIN.
- R4: dummy pronoun "It" from "It is not true that…" was extracted as an entity
  and flagged absent from evidence.

Fixes (v2.2): prompt requires RESOLVED logical polarity (double negation
cancelled); dummy-pronoun filter in entity extraction (deterministic and
semantic merge).
Measured on F21-05/F22 double-negation cases: SUPPORTED correctly restored.

## 3. Entity attribution — held-out exact 0.688 (5 misses)

Root cause R5: the judge read exclusivity into silence — evidence attributing a
property to entity A was treated as CONTRADICTING the same property for entity
B, although the evidence never mentions B (correct label: NOT_SUPPORTED).
Fix (v2.2): prompt silence-vs-contradiction rule with examples; deterministic
attribution checks restricted to FUNCTIONAL relations (owns/authored/maintains/
stores/developed/funded — single-holder by documented convention); non-functional
relations (locations, enforcement) and different-relation claims are silence.
Measured on F24 (5 cases): 4/5 exact; F24-05 (maintains vs authored) fixed in the
second iteration via the different-relation silence clause → 5/5.

## 4. Multi-hop — held-out exact 0.727 (3 misses)

Root causes:
- R6: no evidence-chain composition; reversed/missing chains judged by surface
  reading.
- R7: multi-word predicates ("depends on") were not lemma-normalized, so chain
  edges never matched.

Fixes (v2.2): reachability-based chain composition over normalized event tuples
(complete chain → SUPPORTED override, reversed chain → CONTRADICTED override,
missing link → abstain); first-token lemma normalization; prompt chain rules.
Measured on F23 (5 cases): 5/5 exact after fixes, FAR 0, FRR 0.

## 5. Remaining known failure (documented, not hidden)

- F22-01 (dev): evidence-internal pronoun ("It restarts services…") coreference
  still yields judge UNCERTAIN despite prompt instruction. Abstention, not a
  false acceptance. Limitation L16 in docs/LIMITATIONS.md.
- Held-out label disputes (held-out frozen; adjudication reserved for the
  independent split per docs/INDEPENDENT_VALIDATION_PROTOCOL.md):
  - F19-12 "Audit logs are retained for 90 days in PostgreSQL": evidence never
    states the storage backend; NOT_SUPPORTED is defensible, current label
    CONTRADICTED assumes exclusivity. Adjudication pending.
  - F15-12 "Legacy clients must use TLS 1.3": evidence says TLS 1.2 *may* be
    enabled; possibility does not assert actual use, so NOT_SUPPORTED is
    defensible vs current CONTRADICTED label. Adjudication pending.
  These two label disputes mean held-out exact accuracy is a lower bound under
  the current convention; they are NOT silently relabeled.

## 6. Execution provenance of the hardening measurements

| Measurement | Prompt | Mode | Quota |
|---|---|---|---|
| Held-out grid (140×4 variants) | v2.1 | retrieval live; verification deterministic + cached-live replay | executed earlier |
| Dev F21–F24 iteration 1 (20 cases) | v2.2 | fresh-live | 20 calls |
| Dev F21–F24 iteration 2 (20 cases) | v2.2 | fresh-live | 20 calls |
| Dev F21–F24 final (20 cases) | v2.2 | cached-live replay of iteration 2 | 0 calls |
| Held-out re-measurement with v2.2 | v2.2 | BLOCKED_BY_QUOTA | daily generate cap reached |

Final dev F21–F24: exact 0.950, FAR 0.000, FRR 0.000, 4 deterministic↔semantic
disagreements recorded for review. No held-out ID or label was used to tune
checks; all fixes were validated on the new development families only.