"""Agent system configuration and paradox detection pipeline."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib import error as urlerror
from urllib import request

try:
    from src.prompts import *
    from src.apis import (
        ModelAPIConfig,
        load_model_config,
    )
except ModuleNotFoundError:
    from prompts import *
    from apis import (
        ModelAPIConfig,
        load_model_config,
    )


class AgentAPIError(RuntimeError):
    """Raised when LLM API call fails or returns invalid response."""


class OpenAICompatClient:
    """Minimal OpenAI-compatible client loaded from YAML model config."""

    def __init__(self, config: ModelAPIConfig) -> None:
        self.config = config

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> str:
        if not self.config.api_key:
            raise AgentAPIError("API key is empty in loaded model config.")

        resolved_temperature = (
            self.config.default_temperature if temperature is None else temperature
        )
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": resolved_temperature,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = dict(self.config.headers or {})
        headers["Authorization"] = f"Bearer {self.config.api_key}"
        req = request.Request(
            url=self.config.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
        except urlerror.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AgentAPIError(
                f"{self.config.provider} request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urlerror.URLError as exc:
            raise AgentAPIError(f"{self.config.provider} request failed: {exc}") from exc

        try:
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AgentAPIError(
                f"{self.config.provider} response is not in expected format: {raw}"
            ) from exc


def _extract_json_dict(text: str) -> dict[str, Any]:
    """Parse the first JSON object from model output."""
    cleaned = text.strip().replace("```json", "```")
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    while start != -1:
        depth = 0
        for idx in range(start, len(cleaned)):
            ch = cleaned[idx]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start : idx + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        break
        start = cleaned.find("{", start + 1)

    raise ValueError(f"Could not parse JSON object from model output: {text}")


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _text_or_na(value: Any) -> str:
    text = str(value).strip()
    return text if text else "N/A"


def _phase_1_to_core_vars(phase_1: dict[str, Any]) -> list[str]:
    vars_value = phase_1.get("core_variables")
    vars_list = _as_string_list(vars_value)
    if vars_list:
        return vars_list

    legacy = phase_1.get("variables")
    if isinstance(legacy, dict):
        merged: list[str] = []
        for raw in legacy.values():
            merged.extend(_as_string_list(raw))
        return merged
    return _as_string_list(legacy)


def _s1_internal_knowledge_items(s1_result: dict[str, Any]) -> list[str]:
    raw = s1_result.get("internal_knowledge")
    if not isinstance(raw, list):
        return _as_string_list(raw)

    items: list[str] = []
    for entry in raw:
        if isinstance(entry, dict):
            item_text = str(entry.get("item", "")).strip()
            if item_text:
                items.append(item_text)
        else:
            text = str(entry).strip()
            if text:
                items.append(text)
    return items


class ParadoxDetector:
    """Implements solution v0.1.0 structured prompt chaining."""

    def __init__(
        self,
        client: OpenAICompatClient,
        *,
        output_language: str = "Chinese",
    ) -> None:
        self.client = client
        self.output_language = output_language

    @classmethod
    def from_default(
        cls,
        *,
        output_language: str = "Chinese",
        model_config: str | None = None,
    ) -> "ParadoxDetector":
        loaded_config = load_model_config(model_config)
        return cls(
            client=OpenAICompatClient(loaded_config),
            output_language=output_language,
        )

    def analyze(self, user_input: str) -> dict[str, Any]:
        s1_knowledge = self._run_s1_knowledge_retrieval(user_input)
        phase_1 = self._run_phase_1(user_input, s1_knowledge)
        phase_2 = self._run_phase_2(user_input, phase_1)
        phase_3 = self._run_phase_3(user_input, phase_1, phase_2)
        return self._build_report(
            user_input,
            s1_knowledge,
            phase_1,
            phase_2,
            phase_3,
        )

    def _run_s1_knowledge_retrieval(self, user_input: str) -> dict[str, Any]:
        prompt = S1_KNOWLEDGE_TEMPLATE.format(
            output_language=self.output_language,
            user_input=user_input,
        )
        raw = self.client.chat(system_prompt=BASE_SYSTEM_PROMPT, user_prompt=prompt)
        return _extract_json_dict(raw)

    def _run_phase_1(
        self, user_input: str, s1_knowledge_result: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = PHASE_1_TEMPLATE.format(
            output_language=self.output_language,
            s1_knowledge_json=json.dumps(
                s1_knowledge_result, ensure_ascii=False, indent=2
            ),
            user_input=user_input,
        )
        raw = self.client.chat(system_prompt=BASE_SYSTEM_PROMPT, user_prompt=prompt)
        return _extract_json_dict(raw)

    def _run_phase_2(
        self, user_input: str, phase_1_result: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = PHASE_2_TEMPLATE.format(
            output_language=self.output_language,
            phase_1_json=json.dumps(phase_1_result, ensure_ascii=False, indent=2),
            user_input=user_input,
        )
        raw = self.client.chat(system_prompt=BASE_SYSTEM_PROMPT, user_prompt=prompt)
        return _extract_json_dict(raw)

    def _run_phase_3(
        self,
        user_input: str,
        phase_1_result: dict[str, Any],
        phase_2_result: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = PHASE_3_TEMPLATE.format(
            output_language=self.output_language,
            phase_1_json=json.dumps(phase_1_result, ensure_ascii=False, indent=2),
            phase_2_json=json.dumps(phase_2_result, ensure_ascii=False, indent=2),
            user_input=user_input,
        )
        raw = self.client.chat(system_prompt=BASE_SYSTEM_PROMPT, user_prompt=prompt)
        return _extract_json_dict(raw)

    def _build_report(
        self,
        user_input: str,
        s1_knowledge: dict[str, Any],
        phase_1: dict[str, Any],
        phase_2: dict[str, Any],
        phase_3: dict[str, Any],
    ) -> dict[str, Any]:
        digest_src = json.dumps(
            {
                "user_input": user_input,
                "s1_knowledge": s1_knowledge,
                "phase_1": phase_1,
                "phase_2": phase_2,
                "phase_3": phase_3,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        report_id = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()[:12]

        branches_raw = phase_2.get("branches")
        branches: list[dict[str, str]] = []
        if isinstance(branches_raw, list):
            for item in branches_raw:
                if not isinstance(item, dict):
                    continue
                branches.append(
                    {
                        "name": _text_or_na(item.get("name", "")),
                        "result": _text_or_na(item.get("result", "")),
                        "goal_impact": _text_or_na(item.get("goal_impact", "")),
                    }
                )

        return {
            "report_id": report_id,
            "logical_breakdown": {
                "primary_goal": str(phase_1.get("stated_goal", "")).strip(),
                "core_variables": _phase_1_to_core_vars(phase_1),
                "retrieved_internal_knowledge": _s1_internal_knowledge_items(
                    s1_knowledge
                ),
                "internal_knowledge_used": _as_string_list(
                    phase_1.get("internal_knowledge_used")
                ),
                "knowledge_gaps": _as_string_list(s1_knowledge.get("knowledge_gaps")),
                "hidden_assumptions": _as_string_list(phase_1.get("hidden_assumptions")),
                "reality_gaps": _as_string_list(phase_1.get("reality_gaps")),
            },
            "stress_test_results": branches,
            "paradox_diagnosis": {
                "type": str(phase_3.get("paradox_type", "None")).strip() or "None",
                "reasoning": str(phase_3.get("reasoning", "")).strip(),
                "contradiction_path": _as_string_list(phase_3.get("contradiction_path")),
            },
            "suggested_mitigation": _as_string_list(phase_3.get("mitigation")),
            "raw_phases": {
                "s1_knowledge_retrieval": s1_knowledge,
                "phase_1": phase_1,
                "phase_2": phase_2,
                "phase_3": phase_3,
            },
        }


def format_report(report: dict[str, Any]) -> str:
    lines: list[str] = [f"REPORT ID: {report.get('report_id', 'N/A')}"]

    logical = report.get("logical_breakdown", {})
    lines.append("")
    lines.append("1. LOGICAL BREAKDOWN")
    lines.append(f"- Primary Goal: {logical.get('primary_goal', '')}")
    lines.append(
        f"- Core Variables: {', '.join(logical.get('core_variables', [])) or 'N/A'}"
    )

    retrieved_knowledge = logical.get("retrieved_internal_knowledge", [])
    lines.append("- Retrieved Internal Knowledge (S1):")
    if retrieved_knowledge:
        for item in retrieved_knowledge:
            lines.append(f"  - {item}")
    else:
        lines.append("  - N/A")

    used_knowledge = logical.get("internal_knowledge_used", [])
    lines.append("- Internal Knowledge Used (Phase I):")
    if used_knowledge:
        for item in used_knowledge:
            lines.append(f"  - {item}")
    else:
        lines.append("  - N/A")

    knowledge_gaps = logical.get("knowledge_gaps", [])
    lines.append("- Knowledge Gaps:")
    if knowledge_gaps:
        for item in knowledge_gaps:
            lines.append(f"  - {item}")
    else:
        lines.append("  - N/A")

    assumptions = logical.get("hidden_assumptions", [])
    lines.append("- Hidden Assumptions:")
    if assumptions:
        for item in assumptions:
            lines.append(f"  - {item}")
    else:
        lines.append("  - N/A")

    reality_gaps = logical.get("reality_gaps", [])
    lines.append("- Reality Gaps:")
    if reality_gaps:
        for item in reality_gaps:
            lines.append(f"  - {item}")
    else:
        lines.append("  - N/A")

    lines.append("")
    lines.append("2. STRESS TEST RESULTS (Phase II)")
    branches = report.get("stress_test_results", [])
    if branches:
        for idx, branch in enumerate(branches, start=1):
            name = branch.get("name", f"Branch {idx}")
            result = branch.get("result", "N/A")
            goal_impact = branch.get("goal_impact", "N/A")
            lines.append(f"- Branch {idx}: {name}")
            lines.append(f"  Result: {result}")
            lines.append(f"  Goal Impact: {goal_impact}")
    else:
        lines.append("- N/A")

    diagnosis = report.get("paradox_diagnosis", {})
    lines.append("")
    lines.append("3. PARADOX DIAGNOSIS (Phase III)")
    lines.append(f"- Type: {diagnosis.get('type', 'None')}")
    lines.append(f"- Reasoning: {diagnosis.get('reasoning', '') or 'N/A'}")
    lines.append("- Contradiction Path:")
    path = diagnosis.get("contradiction_path", [])
    if path:
        for step in path:
            lines.append(f"  - {step}")
    else:
        lines.append("  - N/A")

    lines.append("")
    lines.append("4. SUGGESTED MITIGATION")
    mitigations = report.get("suggested_mitigation", [])
    if mitigations:
        for item in mitigations:
            lines.append(f"- {item}")
    else:
        lines.append("- N/A")

    return "\n".join(lines)
