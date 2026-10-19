import argparse
import json
import sys
from pathlib import Path

from .extraction import ExtractionError, evaluate, extract


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real local AI extraction against a labeled fictional requirement.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    web = subparsers.add_parser("serve", help="Open the local document review application")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--database", type=Path, help="Explicit local SQLite path, e.g. an isolated QA database")
    command = subparsers.add_parser("evaluate")
    command.add_argument("--case", required=True, type=Path)
    command.add_argument("--report", required=True, type=Path)
    command.add_argument("--model", default="qwen3.5:9b")
    command.add_argument("--target", type=float, default=0.9)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            if not 1 <= args.port <= 65535:
                raise ExtractionError("Choose a port between 1 and 65535.")
            from .server import serve
            serve(args.port, args.database)
            return 0
        if not 0 <= args.target <= 1:
            raise ExtractionError("The target must be between 0 and 1.")
        if args.case.resolve() == args.report.resolve():
            raise ExtractionError("The report must not overwrite the source fixture.")
        source = json.loads(args.case.read_text(encoding="utf-8"))
        if source.get("fictional") is not True:
            raise ExtractionError("This initial evaluation command accepts labeled fictional fixtures only.")
        result = extract(source["source"], source["categories"], args.model)
        score = evaluate(source["expected"], result["extraction"]["lines"])
        passed = score["exact_line_accuracy"] >= args.target and not result["validation_findings"]
        report = {"case_id": source["id"], "fictional": True, **result, "evaluation": score, "target": args.target, "passed": passed}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"report": str(args.report), "elapsed_seconds": result["elapsed_seconds"], "exact_line_accuracy": score["exact_line_accuracy"], "field_accuracy": score["field_accuracy"], "passed": passed}, indent=2))
        return 0 if passed else 2
    except (ExtractionError, OSError, ValueError, KeyError) as error:
        print(f"Operation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
