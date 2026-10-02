# ⚡ AI Agent Replay & Verification Harness

A full-stack web application designed for **AI Agent Observability, Deterministic Replay, Divergence Detection, and Cryptographic Tamper Auditing**.

---

## 🎯 Architecture Flow

```
User Task / Trigger
       ↓
    AI Agent
       ↓
  Tool Calls (Functional / Live)
       ↓
    Harness
  ├─ Secret Redactor: Masks API keys, tokens, cards -> [REDACTED]
  ├─ Cryptographic Hash Chain: SHA-256(prev_hash + step_data)
  └─ HMAC Signature: Seals the trace document
       ↓
 Record & Save (JSON Trace)
       ↓
 Replay Engine (Mocked Tools)
       ↓
 Side-by-Side Verification Diff
       ↓
 Verdict: ✅ PASS or ❌ DIVERGENCE DETECTED
       ↓
 Cryptographic Integrity Check
       ↓
 Tamper Status: 🛡️ VERIFIED AUTHENTIC or 🚨 TAMPERING DETECTED
```

---

## 🚀 How to Run the Web Application

The application is located at:
`C:\Users\suree\.gemini\antigravity\scratch\agent-replay-harness`

### Quick Start (Zero Setup Needed):

Open PowerShell or Command Prompt, navigate to the folder, and run:

```powershell
cd C:\Users\suree\.gemini\antigravity\scratch\agent-replay-harness
python app.py
```

Open your browser and visit:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

> **Note:** `app.py` is equipped with a dual backend. If `fastapi` and `uvicorn` are installed, it automatically boots with high-performance FastAPI. If not, it seamlessly falls back to Python's built-in standard library HTTP server with **zero external dependencies** required!

Optional: To install FastAPI and Uvicorn for production mode:
```powershell
pip install -r requirements.txt
```

---

## 🌟 Key Features & Verification Capabilities

### 1. 🤖 Multi-Scenario Agents
Switch between 3 pre-built realistic agent workflows from the scenario dropdown:
* **📦 E-Commerce Refund Agent**: Fetches order data, validates 30-day return policy, and dispatches payment gateway refund.
* **✈️ Weather & Travel Advisor**: Fetches live regional forecasts, evaluates flight delay conditions, and sends customer alerts.
* **🖥️ Cloud SRE Auto-Healer**: Gathers server CPU/memory metrics, checks SLA thresholds, and restarts degraded microservices.

### 2. 🔒 Automatic PII & Secret Redaction
All inputs and outputs are sanitized in real time before being written to disk:
* API keys (`sk-...`)
* Auth Bearer tokens (`bearer_...`)
* Credit card & payment tokens (`tok_visa_...`)
* Customer emails & phone numbers
Protected fields appear in the UI highlighted with amber `[REDACTED_...]` badges.

### 3. 🔄 Deterministic Replay Harness
Replays the recorded trace using mock tool responses:
* Verifies if each tool call, parameter, and output matches the recorded golden baseline.
* If 100% matched: Displays **✅ PASS (100% Exact Match)**.

### 4. ⚡ Live Drift / Divergence Demo (Chaos Engineering)
Click the **"⚡ Simulate Drift"** button in the UI:
* Temporarily forces a mock tool to return an altered response (e.g., return window expired, or severe storm alert).
* The harness immediately catches the deviation and highlights the exact mismatched field in red: **❌ DIVERGENCE DETECTED**.

### 5. 🔗 Cryptographic Hash Chaining & Tamper Detection
* Every step calculates:
  $$\text{Hash}_n = \text{SHA256}(\text{Hash}_{n-1} + \text{CanonicalStepJSON})$$
* Root document is signed with an **HMAC-SHA256** cryptographic signature.
* Click the **"⚠️ Tamper Trace File"** button:
  * The harness deliberately mutates a byte in the saved JSON file on disk (e.g. changing refund status or amount) without updating the hash chain.
  * The verification engine immediately triggers:
    **🚨 TAMPERING DETECTED at Step X!** and highlights the broken block in the visual blockchain explorer.
* Click **"🛡️ Verify Trace"** anytime to perform a full cryptographic audit.

---

## 📁 Project Structure

```
agent-replay-harness/
├── app.py                 # Backend server (FastAPI + Standalone Fallback)
├── requirements.txt       # Dependencies (fastapi, uvicorn, pydantic)
├── README.md              # Project documentation
├── harness/
│   ├── __init__.py
│   ├── agent.py           # Multi-step agents (Refund, Travel, DevOps)
│   ├── recorder.py        # Trace recording, JSON store & hash linking
│   ├── replayer.py        # Mock tool replayer & deep diff engine
│   ├── security.py        # SHA-256 hash chaining, HMAC signing & redactor
│   └── tools.py           # Functional tools, mock dispatch & chaos injection
├── static/
│   ├── index.html         # Modern dark dashboard UI
│   ├── app.js             # Interactive frontend controller
│   └── styles.css         # Styling, glows & diff layout
└── traces/                # Stored JSON execution traces
```
