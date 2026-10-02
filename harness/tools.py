import time
from typing import Any, Dict, Optional

# Active mock overrides or drift injections for testing
ACTIVE_DRIFTS: Dict[str, Any] = {}


def inject_drift(tool_name: str, altered_output: Any) -> None:
    """Injects simulated drift or modified response for a tool during replay."""
    ACTIVE_DRIFTS[tool_name] = altered_output


def clear_drifts() -> None:
    """Clears all injected drifts."""
    ACTIVE_DRIFTS.clear()


# ==========================================
# TOOL IMPLEMENTATIONS (Real / Functional)
# ==========================================

def fetch_order_details(order_id: str) -> Dict[str, Any]:
    return {
        "order_id": order_id,
        "customer": "Kavitha Rajan",
        "email": "kavitha.r@example.com",
        "item": "Mechanical Ergonomic Keyboard",
        "purchase_amount": 129.99,
        "purchase_days_ago": 12,
        "status": "DELIVERED",
        "secret_token": "sk-live-sec99887766554433221100aa",
        "card_token": "tok_visa_4242_secret_card_8877"
    }


def validate_refund_policy(order_id: str, purchase_days_ago: int, item_condition: str = "UNOPENED") -> Dict[str, Any]:
    is_eligible = purchase_days_ago <= 30 and item_condition.upper() in ("UNOPENED", "DEFECTIVE", "NEW")
    return {
        "order_id": order_id,
        "is_eligible": is_eligible,
        "refund_window_days": 30,
        "days_elapsed": purchase_days_ago,
        "policy_code": "POL_30DAY_SATISFACTION",
        "authorization_status": "APPROVED" if is_eligible else "REJECTED"
    }


def process_refund(order_id: str, amount: float, card_token: str) -> Dict[str, Any]:
    return {
        "transaction_id": f"TXN-REF-{int(time.time())}",
        "order_id": order_id,
        "refunded_amount": amount,
        "currency": "USD",
        "destination_token": card_token,
        "status": "SUCCESS",
        "gateway_response": "200_OK_PAYMENT_REVERSED"
    }


def get_weather(city: str) -> Dict[str, Any]:
    city_map = {
        "chennai": {"temp_c": 31.5, "condition": "Partly Cloudy", "humidity": 78, "wind_kmh": 14},
        "bangalore": {"temp_c": 24.0, "condition": "Pleasant Breeze", "humidity": 60, "wind_kmh": 10},
        "coimbatore": {"temp_c": 28.0, "condition": "Sunny", "humidity": 65, "wind_kmh": 12},
    }
    return city_map.get(city.lower(), {"temp_c": 27.0, "condition": "Clear", "humidity": 70, "wind_kmh": 11})


def check_flight_status(flight_no: str, weather_condition: str) -> Dict[str, Any]:
    delayed = "rain" in weather_condition.lower() or "storm" in weather_condition.lower()
    return {
        "flight_no": flight_no,
        "scheduled_time": "18:45 IST",
        "gate": "T2-G14",
        "status": "DELAYED (Weather Advisory)" if delayed else "ON_TIME",
        "delay_minutes": 45 if delayed else 0
    }


def send_customer_notification(recipient: str, message: str) -> Dict[str, Any]:
    return {
        "status": "DISPATCHED",
        "channel": "SMS_GATEWAY",
        "recipient": recipient,
        "delivered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sms_provider_id": "MSG91-AUTH-TOKEN-SEC8877"
    }


def query_system_metrics(host: str) -> Dict[str, Any]:
    return {
        "host": host,
        "cpu_usage_pct": 92.4,
        "memory_usage_pct": 88.1,
        "disk_free_gb": 4.2,
        "health_score": "CRITICAL"
    }


def evaluate_service_health(cpu_pct: float, memory_pct: float) -> Dict[str, Any]:
    degraded = cpu_pct > 85.0 or memory_pct > 85.0
    return {
        "degraded": degraded,
        "suggested_action": "RESTART_CONTAINER" if degraded else "HEALTHY",
        "reason": "High CPU and Memory threshold breached (>85%)"
    }


def restart_service(host: str, service_name: str, auth_token: str) -> Dict[str, Any]:
    return {
        "host": host,
        "service": service_name,
        "status": "RESTARTED_SUCCESSFULLY",
        "restart_duration_ms": 420,
        "cluster_auth": auth_token
    }


# Tool Dispatch Table
TOOL_REGISTRY = {
    "fetch_order_details": fetch_order_details,
    "validate_refund_policy": validate_refund_policy,
    "process_refund": process_refund,
    "get_weather": get_weather,
    "check_flight_status": check_flight_status,
    "send_customer_notification": send_customer_notification,
    "query_system_metrics": query_system_metrics,
    "evaluate_service_health": evaluate_service_health,
    "restart_service": restart_service,
}


def execute_tool(tool_name: str, inputs: Dict[str, Any], use_mock: bool = False, mock_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a tool.
    If use_mock=True, checks if an active drift or canned mock_data exists.
    Otherwise executes the real function in TOOL_REGISTRY.
    """
    # 1. Check if user configured active drift for this tool (for testing divergence)
    if tool_name in ACTIVE_DRIFTS:
        return ACTIVE_DRIFTS[tool_name]

    # 2. Replay mock mode: return recorded mock data if provided
    if use_mock and mock_data is not None:
        return mock_data

    # 3. Functional execution
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: '{tool_name}'")

    tool_func = TOOL_REGISTRY[tool_name]
    return tool_func(**inputs)
