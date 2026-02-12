"""CLI entrypoint for Paradox Machine MVP."""

from __future__ import annotations

import argparse
import json

from src.apis import APIConfigError
from src.agents import AgentAPIError, ParadoxDetector, format_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Paradox Machine (solution v0.1.0) with YAML model config."
    )
    parser.add_argument(
        "statement",
        nargs="*",
        help="Input statement/scenario to inspect for paradoxes.",
    )
    parser.add_argument(
        "--lang",
        default="Chinese",
        help="Output language requested from the agent. Default: Chinese",
    )
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Model YAML config name or path, e.g. deepseek-chat or "
            "assets/models/deepseek-chat.yaml."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON report instead of formatted text.",
    )
    return parser


def _read_statement(parts: list[str]) -> str:
    if parts:
        return " ".join(parts).strip()
    return input("Please enter the viewpoint or proposal to be examined.: ").strip()


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    statement = _read_statement(args.statement)
    if not statement:
        parser.error("Input statement cannot be empty.")

    try:
        detector = ParadoxDetector.from_default(
            output_language=args.lang,
            model_config=args.config,
        )
        report = detector.analyze(statement)
    except (APIConfigError, AgentAPIError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
