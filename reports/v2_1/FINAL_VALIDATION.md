# V2.1 Final Validation Report (independent-review hardening)

Validation executed: 2026-11-18 · Code commit validated: `c6bd308`
(base V2.1 release: `38fdcde`; this report is committed immediately after).
Host: Windows 11, Python 3.15.2, no GPU; NumPy/mypy native DLLs blocked by
Application Control → pure-Python mypy (`pip install --no-binary mypy`) used for
local type-check reproduction; pyright (npx) used additionally.

## 1. Gate results (actually executed, this tree)

| Gate | Command | Result |
|---|---|---|
| Syntax | `python -m compileall -q ragpipe scripts examples` | OK |
| Lint | `ruff check --select E9,F63,F7,F82 ragpipe scripts examples` | All checks passed |
| Type check (exact CI command) | `mypy --ignore-missing-imports --follow-imports=silent ragpipe/evalstats.py ragpipe/manifest.py ragpipe/redteam.py ragpipe/api.py` | Success: no issues found in 4 source files |
| Tests | `python -m pytest tests/ -q` | **123 passed** in ~10.6 s |
| Dataset schema | load all three splits via `load_adversarial` | OK (104 / 80 / 140) |
| Leakage | `python scripts/check_leakage.py` | OK: families disjoint, no near-duplicates ≥ 0.85 Jaccard |
| Regression | `python scripts/regression_gate.py` | OK: 14 pins, FAR=0.0, detection=0.5833 |
| Red-team | `python -m ragpipe.cli redteam` | 22/22 pairs, rate 1.000 |
| Secret scan | `git grep -nE "AQ\.Ab8RN6I\|AIza[0-9A-Za-z_-]{30}" -- .` | no matches |

GitHub Actions run 44222117920 failed only at the scoped mypy stage
(`evalstats.py:47: Need type annotation for "macros" [var-annotated]`).
Fixed with a genuine annotation (`macros: dict[str, list[float]]`); no
suppression, no disable. Reproduced locally with the exact CI command before
and after the fix (before: 1 error; after: success). Post-push CI verification
is recorded in the release commit message / Actions tab.

## 2. Test-count reconciliation

Actual collected+passed: **123**. Updated consistently: README (2 places),
docs/REVIEWER_GUIDE.md, docs/REPRODUCIBILITY.md, docs/MIGRATION_V2.md,
docs/V21_ENGINEERING_AUDIT.md (historical "98 at audit time" retained as
history). Historical reports (reports/, reports/v2/) keep their as-of counts
and are NOT modified.

## 3. Benchmark provenance (no pooled misleading numbers)

| Measurement | Prompt | Execution mode | n |
|---|---|---|---|
| End-to-end ablation, 4 variants × 12 Q | v2.1 | fresh-live (judge), deterministic retrieval metrics | 48 |
| Grid adversarial 104 × 4 variants | v2.1 | deterministic verification; retrieval from executed live run | 416 |
| Grid development 60 × 4 (3 det + 1 semantic) | v2.1 | deterministic + cached-live | 240 |
| Grid held-out 140 × 4 (3 det + 1 semantic) | v2.1 | deterministic + cached-live | 560 |
| Hardening dev F21–F24 iteration 1 | v2.2 | fresh-live | 20 |
| Hardening dev F21–F24 iteration 2 | v2.2 | fresh-live | 20 |
| Hardening dev F21–F24 final | v2.2 | cached-live replay | 20 |
| Held-out re-measurement with v2.2 | v2.2 | **BLOCKED_BY_QUOTA** (daily generate cap) | 0 |
| Red-team semantic live | — | **not-run** (quota reserved) | 0 |

Per-record `execution_mode` and per-summary `execution_modes` tables are present
in all hardening-era reports; older records are labeled
`unlabeled-pre-hardening`. Manifests carry git commit, dataset hashes, prompt
version+hash, dependency versions, API status.

Headline numbers (see EXECUTIVE_SUMMARY.md for full tables + Wilson CIs):
- End-to-end: faithfulness 1.000, hallucination 0.000, fabrication 0.000,
  refusal 1.000, citation validity 1.000; dense context precision 0.925.
- Held-out (v2.1, hybrid+rerank semantic): detection 1.000 [0.957, 1.000],
  FAR 0.000 [0.000, 0.043] (n=85), FRR 0.000, exact 0.786 [0.711, 0.846].
- Deterministic floors: FAR 0.000 on all splits; detection 0.459–0.629.
- Hardening dev F21–F24 (v2.2): exact 0.950, FAR 0.000, FRR 0.000,
  4 disagreements recorded; remaining miss F22-01 = coreference abstention.

## 4. Held-out integrity

`data/heldout/heldout_fixtures.json` SHA-256 prefix `ce121026dc7415a2` verified
identical before/after the hardening dataset rebuild. Original 12-question
golden set unchanged. Historical reports untouched.

## 5. Remaining limitations (full list: docs/LIMITATIONS.md, 18 items)

Key ones: synthetic single-author labels (no independent human validation yet —
protocol + reserved split added, loader-enforced); small-n Wilson bounds;
judge fallibility and ordinal confidence; two held-out label disputes reserved
for independent adjudication (F19-12, F15-12); evidence-pronoun coreference
abstention (F22-01); held-out v2.2 re-measurement quota-blocked; deterministic
FRR ≈ 0.20 on held-out positives (heuristic floor artifact); pure-Python
retrieval scale limit; local mypy/pyyaml environment constraints.

## 6. Reproduce

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -q
python -m mypy --ignore-missing-imports --follow-imports=silent \
    ragpipe/evalstats.py ragpipe/manifest.py ragpipe/redteam.py ragpipe/api.py
python scripts/check_leakage.py
python scripts/regression_gate.py
python -m ragpipe.cli redteam
python -m ragpipe.cli adversarial --mode deterministic
python scripts/build_final_grid.py     # cached replay, 0 API calls
python scripts/build_v21_summary.py
# live (quota-bounded, resumable):
python -m ragpipe.cli evaluate-v2 --variants bm25,dense,hybrid,hybrid+rerank --resume
python -m ragpipe.cli adversarial --mode semantic --split heldout   # after quota reset
```

## 7. Verdict

All seven release-gate conditions satisfied at commit `c6bd308`: offline CI
sequence green locally (and pushed for Actions verification), counts consistent,
leakage/regression/red-team gates green, historical results unchanged,
README/Reviewer Guide match executed results, limitations documented.
V2.1 is reproducible and defensible; its claims are bounded by the stated
provenance and uncertainty, not by perfect scores.