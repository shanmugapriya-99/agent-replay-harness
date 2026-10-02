import time
from typing import Any, Dict, Optional
from harness.recorder import TraceRecorder
from harness.tools import execute_tool


def run_refund_agent(recorder: TraceRecorder) -> Dict[str, Any]:
    """
    Scenario: E-Commerce Refund Agent
    Steps:
      1. Fetch order details (contains customer info, sensitive tokens)
      2. Validate refund policy compliance
      3. Process payment gateway refund (contains card tokens)
    """
    order_id = "ORD-9842"

    # Step 1: Fetch Order
    t0 = time.perf_counter()
    inputs_1 = {"order_id": order_id}
    out_1 = execute_tool("fetch_order_details", inputs_1)
    duration_1 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("fetch_order_details", inputs_1, out_1, duration_1)

    # Step 2: Validate Policy
    t0 = time.perf_counter()
    inputs_2 = {
        "order_id": order_id,
        "purchase_days_ago": out_1.get("purchase_days_ago", 12),
        "item_condition": "UNOPENED"
    }
    out_2 = execute_tool("validate_refund_policy", inputs_2)
    duration_2 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("validate_refund_policy", inputs_2, out_2, duration_2)

    # Step 3: Process Refund
    t0 = time.perf_counter()
    inputs_3 = {
        "order_id": order_id,
        "amount": out_1.get("purchase_amount", 129.99),
        "card_token": out_1.get("card_token", "tok_visa_4242_secret_card_8877")
    }
    out_3 = execute_tool("process_refund", inputs_3)
    duration_3 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("process_refund", inputs_3, out_3, duration_3)

    return {
        "status": "COMPLETED",
        "final_outcome": f"Refund of ${inputs_3['amount']} issued for Order {order_id}. Reference: {out_3.get('transaction_id')}"
    }


def run_travel_agent(recorder: TraceRecorder) -> Dict[str, Any]:
    """
    Scenario: Weather & Travel Advisor Agent
    Steps:
      1. Fetch weather forecast
      2. Check flight departure status based on weather
      3. Dispatch customer SMS alert
    """
    city = "chennai"
    flight_no = "AI-542"

    # Step 1: Weather
    t0 = time.perf_counter()
    inputs_1 = {"city": city}
    out_1 = execute_tool("get_weather", inputs_1)
    duration_1 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("get_weather", inputs_1, out_1, duration_1)

    # Step 2: Flight Status
    t0 = time.perf_counter()
    inputs_2 = {
        "flight_no": flight_no,
        "weather_condition": out_1.get("condition", "Clear")
    }
    out_2 = execute_tool("check_flight_status", inputs_2)
    duration_2 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("check_flight_status", inputs_2, out_2, duration_2)

    # Step 3: Dispatch SMS
    t0 = time.perf_counter()
    inputs_3 = {
        "recipient": "+91-9876543210",
        "message": f"Flight {flight_no} is currently {out_2.get('status')} at {out_2.get('scheduled_time')}."
    }
    out_3 = execute_tool("send_customer_notification", inputs_3)
    duration_3 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("send_customer_notification", inputs_3, out_3, duration_3)

    return {
        "status": "COMPLETED",
        "final_outcome": f"Flight {flight_no} status checked ({out_2.get('status')}) and SMS dispatched."
    }


def run_devops_agent(recorder: TraceRecorder) -> Dict[str, Any]:
    """
    Scenario: DevOps SRE Auto-Healing Agent
    Steps:
      1. Query host system metrics
      2. Evaluate health threshold
      3. Restart overloaded service with cluster token
    """
    host = "prod-api-01"

    # Step 1: System Metrics
    t0 = time.perf_counter()
    inputs_1 = {"host": host}
    out_1 = execute_tool("query_system_metrics", inputs_1)
    duration_1 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("query_system_metrics", inputs_1, out_1, duration_1)

    # Step 2: Evaluate Health
    t0 = time.perf_counter()
    inputs_2 = {
        "cpu_pct": out_1.get("cpu_usage_pct", 92.4),
        "memory_pct": out_1.get("memory_usage_pct", 88.1)
    }
    out_2 = execute_tool("evaluate_service_health", inputs_2)
    duration_2 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("evaluate_service_health", inputs_2, out_2, duration_2)

    # Step 3: Restart Service
    t0 = time.perf_counter()
    inputs_3 = {
        "host": host,
        "service_name": "payment-worker",
        "auth_token": "bearer_cluster_super_admin_sec9988"
    }
    out_3 = execute_tool("restart_service", inputs_3)
    duration_3 = (time.perf_counter() - t0) * 1000.0
    recorder.record_step("restart_service", inputs_3, out_3, duration_3)

    return {
        "status": "COMPLETED",
        "final_outcome": f"Health check failed on {host}; restarted service {inputs_3['service_name']} successfully."
    }


AGENT_DISPATCH = {
    "refund": ("Process Order Refund (E-Commerce)", run_refund_agent),
    "weather": ("Check Weather & Flight (Travel)", run_travel_agent),
    "devops": ("Auto-Heal High Load Server (DevOps)", run_devops_agent),
}


def execute_agent_task(scenario_key: str = "refund") -> Dict[str, Any]:
    """
    Entry point to run an agent scenario with trace recording.
    """
    if scenario_key not in AGENT_DISPATCH:
        scenario_key = "refund"

    task_title, agent_fn = AGENT_DISPATCH[scenario_key]
    recorder = TraceRecorder(task_name=task_title)

    result = agent_fn(recorder)
    trace = recorder.finalize()
    trace["agent_result"] = result
    return trace
