import os
import sys
import json
from typing import Any, Dict, Optional

# Ensure project root is in python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from harness.agent import execute_agent_task, AGENT_DISPATCH
from harness.recorder import TraceRecorder
from harness.replayer import replay_trace
from harness.security import verify_trace_integrity
from harness.tools import inject_drift, clear_drifts

STATIC_DIR = os.path.join(BASE_DIR, "static")

# Shared backend controller logic
def handle_run_agent(scenario: str) -> Dict[str, Any]:
    clear_drifts()
    trace = execute_agent_task(scenario)
    return {"status": "SUCCESS", "trace": trace}


def handle_replay_trace(trace_id: str = "latest", simulate_drift: bool = False) -> Dict[str, Any]:
    trace = TraceRecorder.load_trace(trace_id)
    if not trace:
        return {"status": "ERROR", "message": f"Trace '{trace_id}' not found."}

    if simulate_drift:
        # Inject realistic drift for the first tool in this trace
        if trace.get("steps"):
            first_tool = trace["steps"][0]["tool_name"]
            if first_tool == "fetch_order_details":
                inject_drift("validate_refund_policy", {
                    "order_id": "ORD-9842",
                    "is_eligible": False,
                    "refund_window_days": 30,
                    "days_elapsed": 45,
                    "policy_code": "POL_EXPIRED",
                    "authorization_status": "REJECTED_OUT_OF_WINDOW"
                })
            elif first_tool == "get_weather":
                inject_drift("get_weather", {
                    "temp_c": 18.2,
                    "condition": "Severe Tropical Storm",
                    "humidity": 98,
                    "wind_kmh": 68
                })
            else:
                inject_drift("evaluate_service_health", {
                    "degraded": False,
                    "suggested_action": "NO_ACTION_REQUIRED",
                    "reason": "Metrics stabilized within threshold"
                })

    result = replay_trace(trace)
    return {"status": "SUCCESS", "replay": result}


def handle_verify_integrity(trace_id: str = "latest") -> Dict[str, Any]:
    trace = TraceRecorder.load_trace(trace_id)
    if not trace:
        return {"status": "ERROR", "message": f"Trace '{trace_id}' not found."}
    verification = verify_trace_integrity(trace)
    return {"status": "SUCCESS", "verification": verification, "trace_id": trace.get("trace_id")}


def handle_simulate_tamper(trace_id: str = "latest") -> Dict[str, Any]:
    trace = TraceRecorder.load_trace(trace_id)
    if not trace or not trace.get("steps"):
        return {"status": "ERROR", "message": "No trace available to tamper with. Run an agent first!"}

    # Alter Step 2 or Step 1 without recalculating hash chain
    target_step = trace["steps"][1] if len(trace["steps"]) > 1 else trace["steps"][0]
    original_val = json.dumps(target_step["output"])
    
    # Deliberately tamper with output payload
    if isinstance(target_step["output"], dict):
        target_step["output"]["_unauthorized_tampered_field"] = "HACKED_BYPASS_VERIFICATION_999"
        if "authorization_status" in target_step["output"]:
            target_step["output"]["authorization_status"] = "FORCED_OVERRIDE_APPROVED"
        elif "condition" in target_step["output"]:
            target_step["output"]["condition"] = "FORCED_SUNNY"
    else:
        target_step["output"] = "TAMPERED_PAYLOAD_VALUE"

    # Save tampered file directly to disk without updating hashes
    filepath = TraceRecorder.save_trace(trace)
    return {
        "status": "SUCCESS",
        "message": f"Tampered Step {target_step['step_index']} in trace '{trace.get('trace_id')}'. Stored hash remains unchanged, causing cryptographic verification failure!",
        "tampered_step": target_step["step_index"],
        "filepath": filepath
    }


def handle_reset_state(scenario: str = "refund") -> Dict[str, Any]:
    clear_drifts()
    trace = execute_agent_task(scenario)
    return {"status": "SUCCESS", "message": "Cleared all drifts and generated clean baseline trace.", "trace": trace}


def handle_list_traces() -> Dict[str, Any]:
    return {"status": "SUCCESS", "traces": TraceRecorder.list_traces()}


# ========================================================
# TRY FASTAPI FIRST, FALLBACK TO STANDARD LIBRARY HTTP
# ========================================================
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
    import uvicorn

    app = FastAPI(title="AI Agent Replay & Verification Harness", version="1.0.0")

    class AgentRunReq(BaseModel):
        scenario: str = "refund"

    class ReplayReq(BaseModel):
        trace_id: str = "latest"
        simulate_drift: bool = False

    class VerifyReq(BaseModel):
        trace_id: str = "latest"

    # Mount static assets
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.post("/api/run-agent")
    def api_run_agent(req: AgentRunReq):
        return handle_run_agent(req.scenario)

    @app.post("/api/replay")
    def api_replay(req: ReplayReq):
        return handle_replay_trace(req.trace_id, req.simulate_drift)

    @app.post("/api/verify-integrity")
    def api_verify(req: VerifyReq):
        return handle_verify_integrity(req.trace_id)

    @app.post("/api/simulate-tamper")
    def api_tamper(req: VerifyReq):
        return handle_simulate_tamper(req.trace_id)

    @app.post("/api/reset-state")
    def api_reset(req: AgentRunReq):
        return handle_reset_state(req.scenario)

    @app.get("/api/traces")
    def api_traces():
        return handle_list_traces()

    @app.get("/api/trace/{trace_id}")
    def api_get_trace(trace_id: str):
        t = TraceRecorder.load_trace(trace_id)
        if not t:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {"status": "SUCCESS", "trace": t}

    RUN_MODE = "FASTAPI"

except ImportError:
    # Standard Library HTTP fallback so it runs anywhere without pip install
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import urllib.parse

    RUN_MODE = "STDLIB"

    class HarnessHttpHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                self.serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
            elif parsed.path.startswith("/static/"):
                file_rel = parsed.path.replace("/static/", "")
                file_path = os.path.join(STATIC_DIR, file_rel)
                content_type = "text/css" if file_rel.endswith(".css") else ("application/javascript" if file_rel.endswith(".js") else "text/plain")
                self.serve_file(file_path, content_type)
            elif parsed.path == "/api/traces":
                self.send_json(handle_list_traces())
            elif parsed.path.startswith("/api/trace/"):
                tid = parsed.path.replace("/api/trace/", "")
                t = TraceRecorder.load_trace(tid)
                if t:
                    self.send_json({"status": "SUCCESS", "trace": t})
                else:
                    self.send_json({"status": "ERROR", "message": "Not found"}, 404)
            else:
                self.send_error(404)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except Exception:
                payload = {}

            if parsed.path == "/api/run-agent":
                self.send_json(handle_run_agent(payload.get("scenario", "refund")))
            elif parsed.path == "/api/replay":
                self.send_json(handle_replay_trace(payload.get("trace_id", "latest"), payload.get("simulate_drift", False)))
            elif parsed.path == "/api/verify-integrity":
                self.send_json(handle_verify_integrity(payload.get("trace_id", "latest")))
            elif parsed.path == "/api/simulate-tamper":
                self.send_json(handle_simulate_tamper(payload.get("trace_id", "latest")))
            elif parsed.path == "/api/reset-state":
                self.send_json(handle_reset_state(payload.get("scenario", "refund")))
            else:
                self.send_error(404)

        def serve_file(self, filepath: str, mime: str):
            if not os.path.exists(filepath):
                self.send_error(404, f"File {filepath} not found")
                return
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def send_json(self, data: Any, code: int = 200):
            content = json.dumps(data).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000))
    HOST = "0.0.0.0"
    print(f"=======================================================")
    print(f"🚀 AI AGENT REPLAY & VERIFICATION HARNESS")
    print(f"🌐 Running on: http://{HOST}:{PORT}")
    print(f"⚙️  Backend Engine: {RUN_MODE}")
    print(f"=======================================================")

    if RUN_MODE == "FASTAPI":
        uvicorn.run("app:app", host=HOST, port=PORT, reload=False)
    else:
        httpd = HTTPServer((HOST, PORT), HarnessHttpHandler)
        print("Serving via Python standard library HTTP server...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
