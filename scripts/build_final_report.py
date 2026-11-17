import json
import glob
import os
import time

def latest(pat):
    return json.load(open(sorted(glob.glob('reports/v2/' + pat))[-1], encoding='utf-8'))

det = latest('adversarial_deterministic_none_*.json')
sem = latest('adversarial_semantic_live_*.json')
pro = latest('probes_*.json')

bm25 = bm25_path = None
for p in sorted(glob.glob('reports/v2/eval_v2_*.json'), reverse=True):
    r = json.load(open(p, encoding='utf-8'))
    if len(r['variants'].get('bm25', {}).get('results', [])) == 12:
        bm25, bm25_path = r, p
        break
dense = dense_path = None
for p in sorted(glob.glob('reports/v2/eval_v2_*.json'), reverse=True):
    r = json.load(open(p, encoding='utf-8'))
    if 'dense' in r['variants']:
        dense, dense_path = r, p
        break

final = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'version': 'v2-final',
    'sources': {
        'adversarial_deterministic': os.path.basename(sorted(glob.glob('reports/v2/adversarial_deterministic_none_*.json'))[-1]),
        'adversarial_semantic_live': os.path.basename(sorted(glob.glob('reports/v2/adversarial_semantic_live_*.json'))[-1]),
        'probes': os.path.basename(sorted(glob.glob('reports/v2/probes_*.json'))[-1]),
        'eval_v2_bm25': os.path.basename(bm25_path),
        'eval_v2_dense_partial': os.path.basename(dense_path),
    },
    'adversarial': {'deterministic': det['summary'], 'semantic_live': sem['summary']},
    'probes': {n: {k: v for k, v in d.items() if k != 'per_case'} for n, d in pro['variants'].items()},
    'ablation_v2': {
        'bm25': {'status': 'live-complete', 'n': 12, 'summary': bm25['variants']['bm25']['summary']},
        'dense': {'status': 'live-partial-insufficient', 'n': len(dense['variants']['dense']['results']),
                  'summary': dense['variants']['dense']['summary']},
        'hybrid': {'status': 'not-run-quota', 'n': 0, 'summary': None},
        'hybrid+rerank': {'status': 'not-run-quota', 'n': 0, 'summary': None},
    },
    'quota_incident': {
        'model': 'gemini-3.5-flash-lite', 'daily_free_limit': 500,
        'exhausted_during': 'evaluate-v2 dense variant, question 2',
        'reset_delay_s_at_failure': 50239,
        'consequence': 'hybrid and hybrid+rerank end-to-end V2 variants not run live; no mocked substitutes presented as benchmarks',
    },
    'verifier_bug_incident': {
        'id': 'B16',
        'description': 'deterministic checks flagged different numbers/negations in multi-fact contexts as contradictions, overriding semantic SUPPORTED verdicts',
        'effect': 'interim bm25 faithfulness 0.838 was a verifier artifact, not model hallucination',
        'fix': 'support-aware contradiction flags (conflict AND no supporting sentence); clause-scoped negation; tightened injection regex',
        'regression_tests': ['test_multifact_context_no_false_numerical_contradiction',
                             'test_clause_scoped_negation_no_false_flag',
                             'test_benign_override_not_injection'],
        'final_bm25_faithfulness': bm25['variants']['bm25']['summary']['faithfulness'],
    },
}
json.dump(final, open('reports/v2/FINAL_V2_REPORT.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)

def f(v):
    return f'{v:.3f}' if isinstance(v, (int, float)) else 'n/a'

s, d = sem['summary'], det['summary']
lines = [
    '# FINAL V2 REPORT — Adversarial & Semantic Faithfulness Testing', '',
    f"Generated: {final['timestamp']} · Model: gemini-3.5-flash-lite (live) · Fixtures: 104 synthetic, author-reviewed", '',
    '## 1. Adversarial verification benchmark (104 cases)', '',
    '| Metric | Deterministic (0 API calls) | Semantic (live judge) |', '|---|---|---|',
    f"| Adversarial detection rate | {f(d['adversarial_detection_rate'])} | {f(s['adversarial_detection_rate'])} |",
    f"| False acceptance rate | {f(d['false_acceptance_rate'])} | {f(s['false_acceptance_rate'])} |",
    f"| False rejection rate | {f(d['false_rejection_rate'])} | {f(s['false_rejection_rate'])} |",
    f"| Exact status accuracy | {f(d['exact_status_accuracy'])} | {f(s['exact_status_accuracy'])} |",
    f"| Uncertain rate | {f(d['uncertain_rate'])} | {f(s['uncertain_rate'])} |",
    f"| Evaluation error rate | {f(d['evaluation_error_rate'])} | {f(s['evaluation_error_rate'])} |",
    f"| Injection cases flagged | {d['injection_flagged']}/{d['injection_cases']} | {s['injection_flagged']}/{s['injection_cases']} |", '',
    f"Semantic contradiction detection: precision {f(s['contradiction_detection']['precision'])}, "
    f"recall {f(s['contradiction_detection']['recall'])}, F1 {f(s['contradiction_detection']['f1'])} "
    f"(TP={s['contradiction_detection']['tp']} FP={s['contradiction_detection']['fp']} FN={s['contradiction_detection']['fn']}). "
    f"Deterministic/semantic disagreements flagged: {s['deterministic_semantic_disagreements']}.", '',
    '### Per-category exact accuracy (semantic live)', '',
    '| Category | n | Accuracy | Uncertain |', '|---|---|---|---|',
]
for cat, c in s['per_category'].items():
    lines.append(f"| {cat} | {c['n']} | {f(c['exact_match_accuracy'])} | {c['uncertain']} |")
lines += ['', '## 2. Retrieval probes on adversarial evidence (no LLM judge)', '',
          '| Variant | n | Evidence hit@10 | MRR | Evidence recall@4 |', '|---|---|---|---|---|']
for n, v in final['probes'].items():
    lines.append(f"| {n} | {v['n']} | {v['evidence_hit_rate_at_10']} | {v['mrr']} | {v['evidence_recall_at_4']} |")
lines += ['', 'Reranking is benchmarked end-to-end (section 3), not in retrieval-only probes.', '',
          '## 3. End-to-end ablation V2 (original 12-question golden set)', '',
          '| Variant | Status | n | Faithfulness | Halluc. (answerable) | Fabrication (unanswerable) | Ctx precision | Ctx recall | Refusal acc | Citation validity |',
          '|---|---|---|---|---|---|---|---|---|---|']
for n, v in final['ablation_v2'].items():
    if v['summary']:
        x = v['summary']
        lines.append(f"| {n} | {v['status']} | {v['n']} | {f(x['faithfulness'])} | {f(x['hallucination_rate_answerable'])} | "
                     f"{f(x['fabrication_rate_unanswerable'])} | {f(x['context_precision'])} | {f(x['context_recall'])} | "
                     f"{f(x['refusal_accuracy'])} | {f(x['citation_validity_rate'])} |")
    else:
        lines.append(f"| {n} | {v['status']} | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
lines += ['',
          '**Quota incident:** the gemini-3.5-flash-lite free tier allows 500 generate requests/day. '
          'The cap was reached during the dense variant (question 2); hybrid and hybrid+rerank were '
          'NOT run live and no mocked numbers are presented as benchmarks. Reset was ~14 h away at failure. '
          'Complete them after reset with:', '',
          '```bash', 'python -m ragpipe.cli evaluate-v2 --variants dense,hybrid,hybrid+rerank', '```', '',
          'The dense row (n=1) is shown only to document partial coverage; it is statistically meaningless.', '',
          '## 4. Verifier bug incident (B16) — why interim numbers were invalid', '',
          'Mid-run inspection showed bm25 faithfulness 0.838. Root cause: deterministic checks flagged '
          'the number of a claim against a *different* number in another sentence of the same multi-fact '
          'context (and negation in unrelated clauses), overriding correct semantic SUPPORTED verdicts. '
          'Fixed with support-aware flags (conflict AND no supporting sentence), clause-scoped negation, '
          'and a tightened injection regex; three regression tests added. Final bm25 faithfulness: '
          f"{f(bm25['variants']['bm25']['summary']['faithfulness'])} "
          '(28 SUPPORTED, 1 UNCERTAIN, 1 disagreement). All reports above were regenerated with the fixed '
          'code via the disk response cache (zero additional quota).', '',
          '## 5. Reproduce', '',
          '```bash',
          'python -m pytest tests/ -q                                  # 98 tests, no API',
          'python -m ragpipe.cli adversarial --mode deterministic      # 0 API calls',
          'python -m ragpipe.cli adversarial --mode semantic           # cached replays are free',
          'python -m ragpipe.cli probes-v2',
          'python -m ragpipe.cli evaluate-v2 --variants bm25,dense,hybrid,hybrid+rerank',
          '```', '',
          'Source reports: ' + ', '.join(final['sources'].values()), '']
open('reports/v2/FINAL_V2_REPORT.md', 'w', encoding='utf-8').write('\n'.join(lines))
print('FINAL report written')