import re
import json
import hmac
import hashlib
from typing import Any, Dict, List, Tuple

DEFAULT_SECRET_KEY = "anti-gravity-agent-audit-key-2026"
GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

# Sensitive information patterns
SENSITIVE_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|token|password|auth|jwt|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", r"\1: [REDACTED_SECRET]"),
    (r"(?i)\b(bearer\s+)([a-zA-Z0-9_\-\.]{10,})\b", r"\1[REDACTED_TOKEN]"),
    (r"\b(sk-[a-zA-Z0-9]{20,})\b", "[REDACTED_API_KEY]"),
    (r"\b(tok_[a-zA-Z0-9_]{10,})\b", "[REDACTED_PAYMENT_TOKEN]"),
    (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CARD_NUMBER]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"(?i)\"password\"\s*:\s*\"[^\"]+\"", "\"password\": \"[REDACTED_PASSWORD]\""),
]


def redact_string(val: str) -> Tuple[str, int]:
    """Redacts known sensitive patterns from a string. Returns (redacted_str, count)."""
    count = 0
    result = val
    for pattern, replacement in SENSITIVE_PATTERNS:
        matches = len(re.findall(pattern, result))
        if matches > 0:
            count += matches
            result = re.sub(pattern, replacement, result)
    return result, count


def redact_data(obj: Any) -> Tuple[Any, int]:
    """Recursively walks through dict/list/string structures and redacts sensitive data."""
    total_redactions = 0

    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            # Check key name itself for high-sensitivity keywords
            if any(secret_term in k.lower() for secret_term in ["password", "secret", "card_token", "auth_token", "api_key"]):
                new_dict[k] = "[REDACTED_SECRET]"
                total_redactions += 1
            else:
                redacted_v, count = redact_data(v)
                new_dict[k] = redacted_v
                total_redactions += count
        return new_dict, total_redactions

    elif isinstance(obj, list):
        new_list = []
        for item in obj:
            redacted_item, count = redact_data(item)
            new_list.append(redacted_item)
            total_redactions += count
        return new_list, total_redactions

    elif isinstance(obj, str):
        return redact_string(obj)

    return obj, 0


def canonical_json(data: Any) -> str:
    """Produces deterministic, formatted canonical JSON for hashing."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def calculate_step_hash(prev_hash: str, step_data: Dict[str, Any]) -> str:
    """
    Computes cryptographic SHA-256 for a single step chained to prev_hash.
    Excludes any stored step_hash to prevent circular reference.
    """
    cleaned_step = {k: v for k, v in step_data.items() if k not in ("step_hash", "prev_hash")}
    payload = f"{prev_hash}::{canonical_json(cleaned_step)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_trace_hmac(final_hash: str, secret_key: str = DEFAULT_SECRET_KEY) -> str:
    """Computes HMAC-SHA256 signature over the final block hash."""
    return hmac.new(
        secret_key.encode("utf-8"),
        final_hash.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def verify_trace_integrity(trace_data: Dict[str, Any], secret_key: str = DEFAULT_SECRET_KEY) -> Dict[str, Any]:
    """
    Validates the step-by-step cryptographic hash chain and the trace signature.
    Pinpoints the exact step if tampered.
    """
    steps = trace_data.get("steps", [])
    stored_signature = trace_data.get("signature")

    if not steps:
        return {
            "valid": False,
            "status": "TAMPERED",
            "tampered_step": None,
            "message": "Trace contains no steps."
        }

    current_prev_hash = GENESIS_HASH

    for idx, step in enumerate(steps, start=1):
        stored_step_hash = step.get("step_hash")
        stored_step_prev = step.get("prev_hash")

        # Check prev_hash linkage
        if stored_step_prev != current_prev_hash:
            return {
                "valid": False,
                "status": "TAMPERED",
                "tampered_step": idx,
                "step_name": step.get("tool_name", f"Step {idx}"),
                "message": f"Hash chain broken at Step {idx}! Expected prev_hash '{current_prev_hash[:10]}...' but got '{stored_step_prev[:10] if stored_step_prev else 'None'}...'"
            }

        # Recompute hash for step data
        computed_hash = calculate_step_hash(current_prev_hash, step)
        if computed_hash != stored_step_hash:
            return {
                "valid": False,
                "status": "TAMPERED",
                "tampered_step": idx,
                "step_name": step.get("tool_name", f"Step {idx}"),
                "message": f"Data tampering detected at Step {idx} ({step.get('tool_name')})! Recomputed hash '{computed_hash[:10]}...' does not match stored hash '{stored_step_hash[:10] if stored_step_hash else 'None'}...'"
            }

        current_prev_hash = computed_hash

    # Verify final HMAC
    expected_hmac = compute_trace_hmac(current_prev_hash, secret_key)
    if expected_hmac != stored_signature:
        return {
            "valid": False,
            "status": "TAMPERED",
            "tampered_step": None,
            "message": "Trace cryptographic HMAC signature mismatch! Root document was altered or signed with a different key."
        }

    return {
        "valid": True,
        "status": "VERIFIED_AUTHENTIC",
        "tampered_step": None,
        "step_count": len(steps),
        "final_hash": current_prev_hash,
        "signature": stored_signature,
        "message": f"Cryptographic integrity verified! All {len(steps)} steps and HMAC signature are valid."
    }
