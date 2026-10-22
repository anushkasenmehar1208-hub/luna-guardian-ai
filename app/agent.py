"""Agent orchestration with real tool execution and configurable providers."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import timedelta
from typing import Any, Callable

import httpx

from . import core

Tool = Callable[..., Any]
ToolExecutor = Callable[[str, str, dict[str, Any], str | None], Any]


def _tools(user_id: str) -> dict[str, Tool]:
    return {
        "create_task": lambda **a: core.create_task(user_id, **a),
        "list_tasks": lambda **a: core.list_tasks(user_id, **a),
        "update_task": lambda **a: core.update_task(user_id, **a),
        "complete_task": lambda **a: core.complete_task(user_id, **a),
        "create_study_plan": lambda **a: core.create_study_plan(user_id, **a),
        "get_study_plan": lambda **a: core.get_study_plan(user_id, **a),
        "replan_missed_session": lambda **a: core.replan_missed_session(user_id, **a),
        "get_student_context": lambda **a: core.get_student_context(user_id),
        "update_student_context": lambda **a: core.update_student_context(user_id, **a),
    }


def execute_tool(user_id: str, name: str, arguments: dict[str, Any], request_id: str | None = None) -> Any:
    tools = _tools(user_id)
    if name not in tools:
        raise ValueError(f"Unknown tool: {name}")
    try:
        result = tools[name](**arguments)
        changed = int(
            name
            in {
                "create_task",
                "update_task",
                "complete_task",
                "create_study_plan",
                "replan_missed_session",
                "update_student_context",
            }
        )
        core.log_activity(user_id, name, arguments, "success", result, changed, request_id)
        return result
    except Exception as exc:
        core.log_activity(user_id, name, arguments, "failed", {"error": str(exc)}, 0, request_id)
        raise


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict:
    parameters: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        parameters["required"] = required
    return {"type": "function", "function": {"name": name, "description": description, "parameters": parameters}}


TOOL_SCHEMAS = [
    _schema(
        "create_task",
        "Create and persist an academic task.",
        {
            "title": {"type": "string"},
            "deadline": {"type": "string", "description": "ISO-8601 with offset"},
            "estimated_minutes": {"type": "integer"},
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "description": {"type": "string"},
            "course": {"type": "string"},
        },
        ["title", "deadline", "estimated_minutes"],
    ),
    _schema(
        "list_tasks",
        "List persisted tasks.",
        {"status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}},
    ),
    _schema(
        "update_task",
        "Update an existing task.",
        {
            "task_id": {"type": "integer"},
            "title": {"type": "string"},
            "deadline": {"type": "string"},
            "estimated_minutes": {"type": "integer"},
            "priority": {"type": "integer"},
            "status": {"type": "string"},
        },
        ["task_id"],
    ),
    _schema("complete_task", "Complete a task.", {"task_id": {"type": "integer"}}, ["task_id"]),
    _schema(
        "create_study_plan",
        "Create and persist a deadline-prioritized study plan.",
        {"start_at": {"type": "string"}, "available_minutes": {"type": "integer"}},
        ["start_at", "available_minutes"],
    ),
    _schema("get_study_plan", "Get the latest or specified plan.", {"plan_id": {"type": "integer"}}),
    _schema(
        "replan_missed_session",
        "Mark a session missed and persist a replacement plan.",
        {"session_id": {"type": "integer"}, "start_at": {"type": "string"}, "available_minutes": {"type": "integer"}},
        ["session_id", "start_at", "available_minutes"],
    ),
    _schema("get_student_context", "Read student preferences and commitments.", {}),
    _schema(
        "update_student_context",
        "Persist student preferences and commitments.",
        {
            "timezone_name": {"type": "string"},
            "preferences": {"type": "object"},
            "commitments": {"type": "array", "items": {"type": "object"}},
        },
    ),
]


SYSTEM = """You are Luna Guardian, a concise university study assistant. Use tools for every requested state change.
Never claim an action succeeded unless its tool result says so. Ask for genuinely necessary missing dates or durations.
Dates must be ISO-8601 with timezone offsets. After creating commitments, make a plan when available time is stated.
Explain assumptions clearly. Current UTC time: {now}."""


def _run_openai(
    user_id: str, text: str, request_id: str, tool_executor: ToolExecutor = execute_tool
) -> dict[str, Any]:
    api_key = os.getenv("LUNA_OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("LUNA_OPENAI_API_KEY is required for the openai provider")
    base_url = os.getenv("LUNA_OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LUNA_OPENAI_MODEL", "gpt-4.1-mini")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM.format(now=core.now_utc().isoformat())},
        {"role": "user", "content": text},
    ]
    steps = []
    with httpx.Client(timeout=45) as client:
        for _ in range(8):
            response = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": messages, "tools": TOOL_SCHEMAS, "tool_choice": "auto"},
            )
            response.raise_for_status()
            message = response.json()["choices"][0]["message"]
            messages.append(message)
            calls = message.get("tool_calls", [])
            if not calls:
                return {"message": message.get("content") or "Done.", "steps": steps, "provider": "openai-compatible"}
            for call in calls:
                name = call["function"]["name"]
                args = json.loads(call["function"].get("arguments") or "{}")
                try:
                    result = tool_executor(user_id, name, args, request_id)
                    steps.append({"tool": name, "arguments": args, "status": "success", "result": result})
                    content = json.dumps(result)
                except Exception as exc:
                    steps.append({"tool": name, "arguments": args, "status": "failed", "result": {"error": str(exc)}})
                    content = json.dumps({"error": str(exc)})
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})
    raise RuntimeError("Agent exceeded its tool-call limit")


def _run_bedrock(
    user_id: str, text: str, request_id: str, tool_executor: ToolExecutor = execute_tool
) -> dict[str, Any]:
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Install the optional 'aws' dependencies for Bedrock") from exc
    model = os.getenv("LUNA_BEDROCK_MODEL", "amazon.nova-lite-v1:0")
    client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
    tools = [
        {
            "toolSpec": {
                "name": item["function"]["name"],
                "description": item["function"]["description"],
                "inputSchema": {"json": item["function"]["parameters"]},
            }
        }
        for item in TOOL_SCHEMAS
    ]
    messages = [{"role": "user", "content": [{"text": text}]}]
    steps = []
    for _ in range(8):
        response = client.converse(
            modelId=model,
            system=[{"text": SYSTEM.format(now=core.now_utc().isoformat())}],
            messages=messages,
            toolConfig={"tools": tools},
        )
        output = response["output"]["message"]
        messages.append(output)
        uses = [part["toolUse"] for part in output["content"] if "toolUse" in part]
        if not uses:
            answer = " ".join(part.get("text", "") for part in output["content"]).strip()
            return {"message": answer or "Done.", "steps": steps, "provider": "amazon-bedrock"}
        results = []
        for use in uses:
            try:
                result = tool_executor(user_id, use["name"], use.get("input", {}), request_id)
                steps.append(
                    {"tool": use["name"], "arguments": use.get("input", {}), "status": "success", "result": result}
                )
                results.append({"toolResult": {"toolUseId": use["toolUseId"], "content": [{"json": result}]}})
            except Exception as exc:
                error = {"error": str(exc)}
                steps.append(
                    {"tool": use["name"], "arguments": use.get("input", {}), "status": "failed", "result": error}
                )
                results.append(
                    {"toolResult": {"toolUseId": use["toolUseId"], "status": "error", "content": [{"json": error}]}}
                )
        messages.append({"role": "user", "content": results})
    raise RuntimeError("Agent exceeded its tool-call limit")


def _duration_minutes(text: str) -> int | None:
    match = re.search(
        r"\b(half|one|two|three|four|five|six|\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?)\b", text, re.I
    )
    if not match:
        return None
    words = {"half": 0.5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    value = words.get(match.group(1).lower(), float(match.group(1)) if match.group(1)[0].isdigit() else 0)
    return round(value * 60 if match.group(2).lower().startswith(("h", "hr")) else value)


def _run_local(
    user_id: str, text: str, request_id: str, tool_executor: ToolExecutor = execute_tool
) -> dict[str, Any]:
    """Offline demo planner. It is deterministic and is labelled as such in every response."""
    lowered = text.lower()
    steps = []

    def call(name: str, **args: Any) -> Any:
        try:
            result = tool_executor(user_id, name, args, request_id)
            steps.append({"tool": name, "arguments": args, "status": "success", "result": result})
            return result
        except Exception as exc:
            steps.append({"tool": name, "arguments": args, "status": "failed", "result": {"error": str(exc)}})
            raise

    if "list" in lowered or "show" in lowered or "what" in lowered:
        tasks = call("list_tasks")
        return {
            "message": f"You have {len([t for t in tasks if not t['completed']])} open task(s).",
            "steps": steps,
            "provider": "local-rules",
        }
    complete = re.search(r"complete\s+(?:task\s*)?#?(\d+)", lowered)
    if complete:
        task = call("complete_task", task_id=int(complete.group(1)))
        return {"message": f"Completed “{task['title']}”.", "steps": steps, "provider": "local-rules"}
    missed = re.search(r"miss(?:ed)?\s+(?:session\s*)?#?(\d+)", lowered)
    if missed:
        minutes = _duration_minutes(text) or 120
        plan = call(
            "replan_missed_session",
            session_id=int(missed.group(1)),
            start_at=core.now_utc().isoformat(),
            available_minutes=minutes,
        )
        return {
            "message": f"Marked session #{missed.group(1)} missed and created plan #{plan['plan_id']} with {len(plan['sessions'])} session(s).",
            "steps": steps,
            "provider": "local-rules",
        }

    created = []
    exam = re.search(r"\b([A-Za-z][A-Za-z0-9+#-]*)\s+exam\s+(tomorrow|today)", text, re.I)
    if exam:
        days = 1 if exam.group(2).lower() == "tomorrow" else 0
        deadline = core.now_utc().replace(hour=23, minute=59, second=0, microsecond=0) + timedelta(days=days)
        created.append(
            call(
                "create_task",
                title=f"{exam.group(1).strip().title()} exam preparation",
                deadline=deadline.isoformat(),
                estimated_minutes=120,
                priority=5,
                course=exam.group(1).strip(),
            )
        )
    count_match = re.search(r"\b(one|two|three|four|five|\d+)\s+assignments?\b", lowered)
    if count_match:
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        count = words.get(count_match.group(1), int(count_match.group(1)) if count_match.group(1).isdigit() else 1)
        deadline = core.now_utc().replace(hour=23, minute=59, second=0, microsecond=0) + timedelta(days=2)
        for index in range(count):
            created.append(
                call(
                    "create_task",
                    title=f"Assignment {index + 1}",
                    deadline=deadline.isoformat(),
                    estimated_minutes=60,
                    priority=3,
                )
            )
    available = _duration_minutes(text)
    if created and available:
        plan = call("create_study_plan", start_at=core.now_utc().isoformat(), available_minutes=available)
        return {
            "message": f"I saved {len(created)} task(s) and created plan #{plan['plan_id']} with {len(plan['sessions'])} focused session(s). I assumed each unnamed assignment needs 60 minutes and is due in two days; tell me the real details and I’ll update them.",
            "steps": steps,
            "provider": "local-rules",
        }
    if created:
        return {
            "message": f"I saved {len(created)} task(s). How much study time is available?",
            "steps": steps,
            "provider": "local-rules",
        }
    if "plan" in lowered and available:
        plan = call("create_study_plan", start_at=core.now_utc().isoformat(), available_minutes=available)
        return {
            "message": f"Created plan #{plan['plan_id']} with {len(plan['sessions'])} session(s).",
            "steps": steps,
            "provider": "local-rules",
        }
    return {
        "message": "I need a task with a deadline, a plan duration, or an action such as “complete task #2”.",
        "steps": steps,
        "provider": "local-rules",
    }


def respond(user_id: str, text: str, tool_executor: ToolExecutor = execute_tool) -> dict[str, Any]:
    if not text.strip() or len(text) > 4000:
        raise ValueError("Message must be between 1 and 4000 characters")
    request_id = str(uuid.uuid4())
    provider = os.getenv("LUNA_AGENT_PROVIDER", "local").lower()
    if provider == "bedrock":
        result = _run_bedrock(user_id, text, request_id, tool_executor)
    elif provider in {"openai", "openai-compatible"}:
        result = _run_openai(user_id, text, request_id, tool_executor)
    elif provider == "local":
        result = _run_local(user_id, text, request_id, tool_executor)
    else:
        raise RuntimeError(f"Unsupported LUNA_AGENT_PROVIDER: {provider}")
    result["request_id"] = request_id
    return result
