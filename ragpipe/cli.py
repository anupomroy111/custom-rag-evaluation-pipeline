import argparse
import json
import sys
from pathlib import Path

from .config import settings
from .llm import GeminiClient
from .pipeline import RAGPipeline, build_index


def cmd_ingest(args: argparse.Namespace) -> int:
    client = GeminiClient()
    build_index(client, docs_dir=Path(args.docs) if args.docs else None)
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    pipeline = RAGPipeline()
    result = pipeline.run(args.question, mode=args.mode, rerank=not args.no_rerank,
                          top_k=args.top_k)
    print("\n" + result.answer.text + "\n")
    print(f"[mode={result.mode} rerank={result.reranked}]")
    if result.answer.cited_ids:
        print("Cited passages:")
        for c in result.contexts:
            if c.chunk.id in result.answer.cited_ids:
                print(f"  - {c.chunk.doc} (chunk {c.chunk.id}, ordinal {c.chunk.ordinal})")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    from .evaluate.runner import EvalRunner, Variant, load_golden

    variants = [Variant.parse(v) for v in args.variants.split(",")]
    items = load_golden(Path(args.golden) if args.golden else None)
    if args.limit:
        items = items[:args.limit]

    pipeline = RAGPipeline()
    runner = EvalRunner(pipeline)
    report = runner.run(items, variants)
    json_path, md_path = runner.save(report)
    print(f"\nReports written:\n  {json_path}\n  {md_path}")
    return 0


def cmd_evaluate_v2(args: argparse.Namespace) -> int:
    from .evaluate.runner import Variant, load_golden
    from .evaluate.runner_v2 import EvalRunnerV2

    variants = [Variant.parse(v) for v in args.variants.split(",")]
    items = load_golden(Path(args.golden) if args.golden else None)
    if args.limit:
        items = items[:args.limit]
    runner = EvalRunnerV2(RAGPipeline())
    report = runner.run(items, variants, resume=args.resume)
    json_path, md_path = runner.save(report)
    print(f"\nReports written:\n  {json_path}\n  {md_path}")
    return 0


def cmd_grid_v21(args: argparse.Namespace) -> int:
    from .evaluate.ablation_v21 import run_grid, save_grid

    report = run_grid(mode=args.mode)
    json_path, md_path = save_grid(report)
    print(f"\nReports written:\n  {json_path}\n  {md_path}")
    return 0


def cmd_redteam(args: argparse.Namespace) -> int:
    from .redteam import run_redteam
    from .verify.engine import VerificationEngine

    client = GeminiClient() if args.mode == "semantic" else None
    report = run_redteam(VerificationEngine(client), mode=args.mode)
    out = settings.reports_dir / "v2_1"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"redteam_{args.mode}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"red-team pairs={report['n_pairs']} passed={report['passed']} "
          f"rate={report['pass_rate']} -> {path}")
    return 0 if report["passed"] == report["n_pairs"] else 1


def cmd_adversarial(args: argparse.Namespace) -> int:
    from .adversarial import AdversarialBenchmark, load_adversarial

    cases = load_adversarial()
    if args.category:
        cases = [c for c in cases if c.category == args.category]
    if args.limit:
        cases = cases[:args.limit]
    client = GeminiClient() if args.mode == "semantic" else None
    bench = AdversarialBenchmark(client=client, mode=args.mode)
    report = bench.run(cases)
    json_path, md_path = bench.save(report)
    print(f"\nReports written:\n  {json_path}\n  {md_path}")
    return 0


def cmd_probes_v2(args: argparse.Namespace) -> int:
    from .adversarial import load_adversarial, run_probes, save_probes

    cases = load_adversarial()
    if args.limit:
        cases = cases[:args.limit]
    report = run_probes(cases, GeminiClient())
    json_path, md_path = save_probes(report)
    print(f"\nReports written:\n  {json_path}\n  {md_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ragpipe",
        description="Custom RAG & Evaluation Pipeline (hybrid search + reranking + automated eval)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Chunk documents and build the embedding index")
    p_ingest.add_argument("--docs", help=f"Documents directory (default: {settings.docs_dir})")
    p_ingest.set_defaults(func=cmd_ingest)

    p_ask = sub.add_parser("ask", help="Ask a question against the indexed corpus")
    p_ask.add_argument("question")
    p_ask.add_argument("--mode", choices=["bm25", "dense", "hybrid"], default="hybrid")
    p_ask.add_argument("--no-rerank", action="store_true")
    p_ask.add_argument("--top-k", type=int, default=None)
    p_ask.set_defaults(func=cmd_ask)

    p_eval = sub.add_parser("evaluate", help="Run the automated evaluation pipeline")
    p_eval.add_argument("--variants", default="hybrid+rerank",
                        help="Comma-separated: bm25,dense,hybrid, each optionally +rerank")
    p_eval.add_argument("--limit", type=int, default=None, help="Evaluate only the first N questions")
    p_eval.add_argument("--golden", help="Path to golden dataset JSON")
    p_eval.set_defaults(func=cmd_evaluate)

    p_eval2 = sub.add_parser("evaluate-v2", help="V2 end-to-end eval (engine verification)")
    p_eval2.add_argument("--variants", default="hybrid+rerank")
    p_eval2.add_argument("--limit", type=int, default=None)
    p_eval2.add_argument("--resume", action="store_true",
                         help="Reuse completed items from checkpoint_v2.json")
    p_eval2.add_argument("--golden", help="Path to golden dataset JSON")
    p_eval2.set_defaults(func=cmd_evaluate_v2)

    p_grid = sub.add_parser("grid-v21", help="V2.1 ablation grid: variants x datasets")
    p_grid.add_argument("--mode", choices=["offline", "mixed"], default="offline")
    p_grid.set_defaults(func=cmd_grid_v21)

    p_rt = sub.add_parser("redteam", help="Paired mutation + metamorphic red-team suite")
    p_rt.add_argument("--mode", choices=["deterministic", "semantic"], default="deterministic")
    p_rt.set_defaults(func=cmd_redteam)

    p_adv = sub.add_parser("adversarial", help="Adversarial verification benchmark")
    p_adv.add_argument("--mode", choices=["deterministic", "semantic"], default="deterministic")
    p_adv.add_argument("--category", help="Restrict to one category")
    p_adv.add_argument("--limit", type=int, default=None)
    p_adv.set_defaults(func=cmd_adversarial)

    p_probes = sub.add_parser("probes-v2", help="Retrieval-variant probes on adversarial evidence")
    p_probes.add_argument("--limit", type=int, default=None)
    p_probes.set_defaults(func=cmd_probes_v2)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (RuntimeError, FileNotFoundError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())