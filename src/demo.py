"""Direct Q&A demo using model YAML config (no paradox pipeline)."""

from __future__ import annotations

import argparse
import json

try:
    from src.apis import APIConfigError, load_model_config
    from src.agents import AgentAPIError, OpenAICompatClient
except ModuleNotFoundError:
    from apis import APIConfigError, load_model_config
    from agents import AgentAPIError, OpenAICompatClient


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Direct model Q&A demo for comparison with paradox pipeline."
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Question or statement for direct model response.",
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
        "--lang",
        default="Chinese",
        help="Preferred answer language. Default: Chinese",
    )
    parser.add_argument(
        "--system",
        default=None,
        help="Optional custom system prompt for direct Q&A.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional override temperature.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output instead of plain answer text.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive multi-turn mode. Type /exit to quit.",
    )
    return parser


def _default_system_prompt(lang: str) -> str:
    return (
        "You are a general assistant. "
        f"Respond directly, clearly, and rigorously in {lang}."
    )


def _read_question(parts: list[str]) -> str:
    if parts:
        return " ".join(parts).strip()
    return input("请输入你的问题: ").strip()


def _ask_once(
    *,
    client: OpenAICompatClient,
    system_prompt: str,
    question: str,
    temperature: float | None,
) -> str:
    return client.chat(
        system_prompt=system_prompt,
        user_prompt=question,
        temperature=temperature,
    )


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        config = load_model_config(args.config)
        client = OpenAICompatClient(config)
    except APIConfigError as exc:
        print(f"[ERROR] {exc}")
        return 1

    system_prompt = args.system or _default_system_prompt(args.lang)

    if args.interactive:
        print(
            f"[INFO] Interactive mode on | provider={config.provider} "
            f"model={config.model} | /exit 退出"
        )
        while True:
            question = input("Q> ").strip()
            if not question:
                continue
            if question.lower() in {"/exit", "exit", "quit"}:
                return 0
            try:
                answer = _ask_once(
                    client=client,
                    system_prompt=system_prompt,
                    question=question,
                    temperature=args.temperature,
                )
            except AgentAPIError as exc:
                print(f"[ERROR] {exc}")
                continue
            print(f"A> {answer}")

    question = _read_question(args.question)
    if not question:
        parser.error("Input question cannot be empty.")

    try:
        answer = _ask_once(
            client=client,
            system_prompt=system_prompt,
            question=question,
            temperature=args.temperature,
        )
    except AgentAPIError as exc:
        print(f"[ERROR] {exc}")
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "provider": config.provider,
                    "model": config.model,
                    "question": question,
                    "answer": answer,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
