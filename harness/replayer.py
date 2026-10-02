import time
from typing import Any, Dict, List, Optional
from harness.tools import execute_tool
from harness.security import redact_data


def compare_values(val1: Any, val2: Any, path: str = "") -> List[Dict[str, Any]]:
    """Recursively compares two data structures and returns list of differences."""
    diffs = []
    if type(val1) != type(val2):
        diffs.append({
            "field": path or "root",
            "expected": val1,
            "actual": val2,
            "reason": f"Type mismatch: {type(val1).__name__} vs {type(val2).__name__}"
        })
        return diffs

    if isinstance(val1, dict):
        all_keys = set(val1.keys()) | set(val2.keys())
        for k in all_keys:
            subpath = f"{path}.{k}" if path else k
            if k not in val1:
                diffs.append({"field": subpath, "expected": "<missing>", "actual": val2[k], "reason": "Extra key in replay"})
            elif k not in val2:
                diffs.append({"field": subpath, "expected": val1[k], "actual": "<missing>", "reason": "Missing key in replay"})
            else:
                diffs.extend(compare_values(val1[k], val2[k], subpath))
    elif isinstance(val1, list):
        if len(val1) != len(val2):
            diffs.append({
                "field": path or "root",
                "expected": f"Array of length {len(val1)}",
                "actual": f"Array of length {len(val2)}",
                "reason": "Array length mismatch"
            })
        else:
            for idx, (item1, item2) in enumerate(zip(val1, val2)):
                diffs.extend(compare_values(item1, item2, f"{path}[{idx}]"))
    else:
        if val1 != val2:
            diffs.append({
                "field": path or "root",
                "expected": val1,
                "actual": val2,
                "reason": "Value mismatch"
            })
    return diffs


def replay_trace(trace_data: Dict[str, Any], inject_mock_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Replays all recorded steps using the mock tool harness.
    Validates step outputs against the recorded baseline to catch divergence.
    """
    recorded_steps = trace_data.get("steps", [])
    replay_steps: List[Dict[str, Any]] = []
    total_divergences = 0
    diverged_steps = []

    for step in recorded_steps:
        step_idx = step["step_index"]
        tool_name = step["tool_name"]
        recorded_inputs = step["inputs"]
        recorded_output = step["output"]

        # If override is passed for this tool, inject it
        mock_data = recorded_output
        if inject_mock_override and tool_name in inject_mock_override:
            mock_data = inject_mock_override[tool_name]

        # Execute in mock mode (will respect active drift injections if any)
        t0 = time.perf_counter()
        raw_replay_output = execute_tool(tool_name, recorded_inputs, use_mock=True, mock_data=mock_data)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        # Sanitize replay output just in case
        sanitized_replay_output, _ = redact_data(raw_replay_output)

        # Diff calculation
        differences = compare_values(recorded_output, sanitized_replay_output)
        is_match = (len(differences) == 0)

        if not is_match:
            total_divergences += 1
            diverged_steps.append(step_idx)

        replay_steps.append({
            "step_index": step_idx,
            "tool_name": tool_name,
            "inputs": recorded_inputs,
            "expected_output": recorded_output,
            "replay_output": sanitized_replay_output,
            "status": "PASS" if is_match else "DIVERGED",
            "duration_ms": round(duration_ms, 2),
            "differences": differences
        })

    is_overall_pass = (total_divergences == 0)
    verdict = "PASS" if is_overall_pass else "DIVERGENCE_DETECTED"

    return {
        "verdict": verdict,
        "is_pass": is_overall_pass,
        "trace_id": trace_data.get("trace_id"),
        "task_name": trace_data.get("task_name"),
        "total_steps": len(recorded_steps),
        "diverged_steps_count": total_divergences,
        "diverged_steps": diverged_steps,
        "replayed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "steps": replay_steps,
        "message": (
            "✅ Replay matched original trace with 100% fidelity!"
            if is_overall_pass
            else f"❌ DIVERGENCE DETECTED at Step(s): {', '.join(map(str, diverged_steps))}! Tool output deviated from recorded trace."
        )
    }
