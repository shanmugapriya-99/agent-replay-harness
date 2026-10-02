import os
import json
import time
from typing import Any, Dict, List, Optional
from harness.security import (
    calculate_step_hash,
    compute_trace_hmac,
    redact_data,
    GENESIS_HASH,
    DEFAULT_SECRET_KEY,
)

TRACES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "traces")
os.makedirs(TRACES_DIR, exist_ok=True)


class TraceRecorder:
    def __init__(self, task_name: str, trace_id: Optional[str] = None):
        self.task_name = task_name
        self.trace_id = trace_id or f"trace_{int(time.time())}_{task_name.lower().replace(' ', '_')}"
        self.created_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.steps: List[Dict[str, Any]] = []
        self.current_prev_hash: str = GENESIS_HASH
        self.total_redactions: int = 0

    def record_step(self, tool_name: str, raw_inputs: Dict[str, Any], raw_output: Any, duration_ms: float) -> Dict[str, Any]:
        """
        Redacts sensitive fields, computes cryptographic step hash chained to previous step,
        and appends the step record to the trace.
        """
        step_index = len(self.steps) + 1

        # Redact inputs & outputs
        redacted_inputs, count_in = redact_data(raw_inputs)
        redacted_output, count_out = redact_data(raw_output)
        step_redactions = count_in + count_out
        self.total_redactions += step_redactions

        # Step record without hash first
        step_record: Dict[str, Any] = {
            "step_index": step_index,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool_name": tool_name,
            "inputs": redacted_inputs,
            "output": redacted_output,
            "duration_ms": round(duration_ms, 2),
            "redactions_count": step_redactions,
            "prev_hash": self.current_prev_hash
        }

        # Calculate cryptographic hash chained to current_prev_hash
        step_hash = calculate_step_hash(self.current_prev_hash, step_record)
        step_record["step_hash"] = step_hash
        self.current_prev_hash = step_hash

        self.steps.append(step_record)
        return step_record

    def finalize(self, secret_key: str = DEFAULT_SECRET_KEY) -> Dict[str, Any]:
        """Calculates final HMAC signature and saves the trace to disk."""
        final_hash = self.current_prev_hash
        signature = compute_trace_hmac(final_hash, secret_key)

        trace_data = {
            "trace_id": self.trace_id,
            "task_name": self.task_name,
            "created_at": self.created_at,
            "total_steps": len(self.steps),
            "total_redactions": self.total_redactions,
            "final_hash": final_hash,
            "signature": signature,
            "steps": self.steps
        }

        # Save to disk
        self.save_trace(trace_data)
        return trace_data

    @staticmethod
    def save_trace(trace_data: Dict[str, Any]) -> str:
        trace_id = trace_data.get("trace_id", "trace_unnamed")
        filepath = os.path.join(TRACES_DIR, f"{trace_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)

        # Also write as latest.json for convenient auto-loading
        latest_path = os.path.join(TRACES_DIR, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)

        return filepath

    @staticmethod
    def load_trace(trace_id: str = "latest") -> Optional[Dict[str, Any]]:
        filename = f"{trace_id}.json" if not trace_id.endswith(".json") else trace_id
        filepath = os.path.join(TRACES_DIR, filename)
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def list_traces() -> List[Dict[str, Any]]:
        traces = []
        if not os.path.exists(TRACES_DIR):
            return []
        for file in os.listdir(TRACES_DIR):
            if file.endswith(".json") and file != "latest.json":
                path = os.path.join(TRACES_DIR, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        traces.append({
                            "trace_id": data.get("trace_id", file),
                            "task_name": data.get("task_name", "Unknown"),
                            "created_at": data.get("created_at", "Unknown"),
                            "steps_count": len(data.get("steps", [])),
                            "total_redactions": data.get("total_redactions", 0),
                        })
                except Exception:
                    continue
        return sorted(traces, key=lambda x: x.get("created_at", ""), reverse=True)
