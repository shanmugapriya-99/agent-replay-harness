// AI Agent Replay & Verification Harness - Frontend Controller

let activeTrace = null;
let activeReplay = null;

// DOM Elements
const scenarioSelect = document.getElementById("scenarioSelect");
const btnRunAgent = document.getElementById("btnRunAgent");
const btnReplay = document.getElementById("btnReplay");
const btnVerify = document.getElementById("btnVerify");
const btnSimulateDrift = document.getElementById("btnSimulateDrift");
const btnSimulateTamper = document.getElementById("btnSimulateTamper");
const btnReset = document.getElementById("btnReset");

const verdictBanner = document.getElementById("verdictBanner");
const verdictIcon = document.getElementById("verdictIcon");
const verdictTitle = document.getElementById("verdictTitle");
const verdictMessage = document.getElementById("verdictMessage");
const verdictTimestamp = document.getElementById("verdictTimestamp");

const metaTraceId = document.getElementById("metaTraceId");
const metaStepsCount = document.getElementById("metaStepsCount");
const metaRedactionsCount = document.getElementById("metaRedactionsCount");
const metaSignature = document.getElementById("metaSignature");

const recordedStepsContainer = document.getElementById("recordedStepsContainer");
const replayStepsContainer = document.getElementById("replayStepsContainer");
const replayBadge = document.getElementById("replayBadge");
const replayIndicator = document.getElementById("replayIndicator");

const hashChainContainer = document.getElementById("hashChainContainer");
const cryptoStatusBadge = document.getElementById("cryptoStatusBadge");

// Helper: Show Toast
function showToast(icon, message) {
  const toast = document.getElementById("toast");
  const toastIcon = document.getElementById("toastIcon");
  const toastMsg = document.getElementById("toastMsg");
  toastIcon.textContent = icon;
  toastMsg.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3500);
}

// Helper: Update Verdict Banner
function showVerdict(type, title, message) {
  verdictBanner.classList.remove("hidden", "bg-emerald-950/50", "border-emerald-500/40", "text-emerald-300", 
                                "bg-rose-950/50", "border-rose-500/40", "text-rose-300", 
                                "bg-cyan-950/50", "border-cyan-500/40", "text-cyan-300",
                                "bg-amber-950/50", "border-amber-500/40", "text-amber-300");

  verdictTimestamp.textContent = new Date().toLocaleTimeString();
  verdictTitle.textContent = title;
  verdictMessage.textContent = message;

  if (type === "PASS") {
    verdictBanner.classList.add("bg-emerald-950/50", "border-emerald-500/40", "text-emerald-300", "glow-emerald");
    verdictIcon.textContent = "✅";
  } else if (type === "DIVERGENCE") {
    verdictBanner.classList.add("bg-rose-950/50", "border-rose-500/40", "text-rose-300", "glow-rose");
    verdictIcon.textContent = "❌";
  } else if (type === "TAMPER") {
    verdictBanner.classList.add("bg-rose-950/50", "border-rose-500/40", "text-rose-300", "glow-rose");
    verdictIcon.textContent = "🚨";
  } else if (type === "VERIFIED") {
    verdictBanner.classList.add("bg-cyan-950/50", "border-cyan-500/40", "text-cyan-300", "glow-cyan");
    verdictIcon.textContent = "🛡️";
  } else {
    verdictBanner.classList.add("bg-amber-950/50", "border-amber-500/40", "text-amber-300");
    verdictIcon.textContent = "ℹ️";
  }
}

// Helper: Format JSON with highlight for [REDACTED_...]
function formatJsonWithRedactions(data) {
  let str = JSON.stringify(data, null, 2);
  // Replace [REDACTED_...] with custom styled pill
  str = str.replace(/(\[REDACTED_[A-Z0-9_]+\])/g, '<span class="redacted-pill">🔒 $1</span>');
  return str;
}

// Render Recorded Baseline Steps
function renderRecordedSteps(trace) {
  if (!trace || !trace.steps || trace.steps.length === 0) {
    recordedStepsContainer.innerHTML = `
      <div class="text-center py-16 text-slate-500 text-xs">
        No trace recorded yet.<br>Click <strong class="text-indigo-400">"1. Run Agent"</strong> above!
      </div>
    `;
    return;
  }

  metaTraceId.textContent = trace.trace_id || "latest";
  metaStepsCount.textContent = `${trace.total_steps || trace.steps.length} Steps`;
  metaRedactionsCount.textContent = `${trace.total_redactions || 0} Protected`;
  metaSignature.textContent = trace.signature ? `${trace.signature.substring(0, 16)}...` : "None";

  recordedStepsContainer.innerHTML = trace.steps.map(step => `
    <div class="bg-slate-950/80 border border-slate-800/90 rounded-xl p-3.5 space-y-2 hover:border-slate-700 transition-colors">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="w-6 h-6 rounded-lg bg-indigo-500/20 text-indigo-400 font-bold text-xs flex items-center justify-center border border-indigo-500/30">
            ${step.step_index}
          </span>
          <span class="font-bold text-xs text-slate-200">${step.tool_name}</span>
        </div>
        <div class="flex items-center space-x-2 text-[11px] text-slate-400 font-mono">
          <span>⏱️ ${step.duration_ms}ms</span>
          ${step.redactions_count > 0 ? `<span class="text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">🔒 ${step.redactions_count} redacted</span>` : ''}
        </div>
      </div>

      <!-- Inputs -->
      <div class="text-[11px]">
        <div class="text-slate-400 font-medium mb-0.5">Input Parameters:</div>
        <div class="json-container">${formatJsonWithRedactions(step.inputs)}</div>
      </div>

      <!-- Outputs -->
      <div class="text-[11px]">
        <div class="text-slate-400 font-medium mb-0.5">Output Data:</div>
        <div class="json-container">${formatJsonWithRedactions(step.output)}</div>
      </div>

      <!-- Hash Badge -->
      <div class="pt-1 flex items-center justify-between text-[10px] text-slate-500 font-mono border-t border-slate-900">
        <span>Prev: ${step.prev_hash ? step.prev_hash.substring(0, 8) : '00000000'}...</span>
        <span class="text-cyan-400/80">Hash: ${step.step_hash ? step.step_hash.substring(0, 12) : ''}...</span>
      </div>
    </div>
  `).join("");
}

// Render Replay Steps & Differences
function renderReplaySteps(replay) {
  if (!replay || !replay.steps || replay.steps.length === 0) {
    replayStepsContainer.innerHTML = `
      <div class="text-center py-16 text-slate-500 text-xs">
        No replay executed yet.<br>Click <strong class="text-emerald-400">"2. Replay Trace"</strong> to verify!
      </div>
    `;
    replayBadge.textContent = "Awaiting Replay";
    replayBadge.className = "text-xs px-2 py-0.5 bg-slate-800 text-slate-400 rounded border border-slate-700 font-mono";
    replayIndicator.className = "w-2.5 h-2.5 rounded-full bg-slate-600";
    return;
  }

  // Update header badge
  if (replay.is_pass) {
    replayBadge.textContent = "✅ 100% PASS (EXACT MATCH)";
    replayBadge.className = "text-xs px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded border border-emerald-500/30 font-mono font-semibold";
    replayIndicator.className = "w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50";
  } else {
    replayBadge.textContent = "❌ DIVERGENCE DETECTED";
    replayBadge.className = "text-xs px-2 py-0.5 bg-rose-500/20 text-rose-400 rounded border border-rose-500/30 font-mono font-semibold";
    replayIndicator.className = "w-2.5 h-2.5 rounded-full bg-rose-500 shadow-lg shadow-rose-500/50";
  }

  replayStepsContainer.innerHTML = replay.steps.map(step => {
    const isPass = step.status === "PASS";
    return `
      <div class="bg-slate-950/80 border ${isPass ? 'border-emerald-500/30' : 'border-rose-500/50 glow-rose'} rounded-xl p-3.5 space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="w-6 h-6 rounded-lg ${isPass ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'} font-bold text-xs flex items-center justify-center">
              ${step.step_index}
            </span>
            <span class="font-bold text-xs text-slate-200">${step.tool_name}</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs px-2 py-0.5 rounded font-mono font-semibold ${isPass ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}">
              ${isPass ? '✅ PASS' : '❌ DIVERGED'}
            </span>
          </div>
        </div>

        <!-- Replay Output -->
        <div class="text-[11px]">
          <div class="text-slate-400 font-medium mb-0.5">Replay Tool Output:</div>
          <div class="json-container">${formatJsonWithRedactions(step.replay_output)}</div>
        </div>

        <!-- Divergence Difference Box if any -->
        ${!isPass && step.differences && step.differences.length > 0 ? `
          <div class="bg-rose-950/40 border border-rose-500/40 rounded-lg p-2.5 space-y-1.5 text-[11px]">
            <div class="font-bold text-rose-300 flex items-center space-x-1.5">
              <span>⚠️</span>
              <span>Divergence Details:</span>
            </div>
            ${step.differences.map(d => `
              <div class="text-slate-300 font-mono space-y-0.5 border-t border-rose-500/20 pt-1">
                <div><span class="text-slate-400">Field:</span> <span class="text-amber-400 font-bold">${d.field}</span></div>
                <div class="text-emerald-400"><span class="text-slate-400">Expected:</span> ${JSON.stringify(d.expected)}</div>
                <div class="text-rose-400"><span class="text-slate-400">Received:</span> ${JSON.stringify(d.actual)}</div>
              </div>
            `).join("")}
          </div>
        ` : ''}
      </div>
    `;
  }).join("");
}

// Render Blockchain-style Hash Chaining
function renderHashChain(trace, tamperedStep = null) {
  if (!trace || !trace.steps || trace.steps.length === 0) {
    hashChainContainer.innerHTML = `<div class="text-slate-500 text-xs font-mono">Run agent to generate blockchain audit trail.</div>`;
    cryptoStatusBadge.textContent = "Chain Uninitialized";
    cryptoStatusBadge.className = "text-xs px-2.5 py-1 bg-slate-800 text-slate-400 rounded-lg border border-slate-700 font-mono";
    return;
  }

  let html = `
    <!-- Genesis Block -->
    <div class="chain-node bg-slate-950 border border-slate-800 rounded-xl p-2.5 min-w-[140px] text-center shadow">
      <div class="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Block 0</div>
      <div class="text-xs font-bold text-indigo-400 mt-0.5">GENESIS</div>
      <div class="text-[9px] font-mono text-slate-500 truncate mt-1">00000000...</div>
      <span class="inline-block mt-1 text-[9px] bg-indigo-500/10 text-indigo-400 px-1.5 rounded">Root</span>
    </div>
  `;

  trace.steps.forEach(step => {
    const isStepTampered = (tamperedStep === step.step_index);
    html += `
      <div class="text-slate-600 font-mono text-lg font-bold">→</div>
      <div class="chain-node bg-slate-950 border ${isStepTampered ? 'border-rose-500 glow-rose animate-pulse' : 'border-cyan-500/30'} rounded-xl p-2.5 min-w-[150px] text-center shadow">
        <div class="text-[10px] ${isStepTampered ? 'text-rose-400 font-bold' : 'text-slate-400'} uppercase tracking-wider font-bold">
          Step ${step.step_index} Block
        </div>
        <div class="text-xs font-bold ${isStepTampered ? 'text-rose-300' : 'text-slate-200'} truncate mt-0.5 max-w-[130px] mx-auto">
          ${step.tool_name}
        </div>
        <div class="text-[9px] font-mono ${isStepTampered ? 'text-rose-400' : 'text-cyan-400'} truncate mt-1">
          ${step.step_hash ? step.step_hash.substring(0, 12) : ''}...
        </div>
        <span class="inline-block mt-1 text-[9px] ${isStepTampered ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'bg-cyan-500/10 text-cyan-300'} px-1.5 rounded">
          ${isStepTampered ? '🚨 TAMPERED' : 'Valid Link'}
        </span>
      </div>
    `;
  });

  // Final HMAC Signature Block
  const isChainBroken = (tamperedStep !== null);
  html += `
    <div class="text-slate-600 font-mono text-lg font-bold">→</div>
    <div class="chain-node bg-slate-950 border ${isChainBroken ? 'border-rose-500 text-rose-300' : 'border-emerald-500/40 text-emerald-300'} rounded-xl p-2.5 min-w-[160px] text-center shadow">
      <div class="text-[10px] uppercase tracking-wider font-bold ${isChainBroken ? 'text-rose-400' : 'text-emerald-400'}">Root Signature</div>
      <div class="text-xs font-bold mt-0.5">HMAC-SHA256</div>
      <div class="text-[9px] font-mono truncate mt-1 ${isChainBroken ? 'text-rose-400' : 'text-emerald-400'}">
        ${trace.signature ? trace.signature.substring(0, 14) : 'Pending'}...
      </div>
      <span class="inline-block mt-1 text-[9px] ${isChainBroken ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'} px-1.5 rounded">
        ${isChainBroken ? '❌ Signature Invalid' : '🔒 Verified Secure'}
      </span>
    </div>
  `;

  hashChainContainer.innerHTML = html;

  if (isChainBroken) {
    cryptoStatusBadge.textContent = `❌ TAMPERED AT STEP ${tamperedStep}`;
    cryptoStatusBadge.className = "text-xs px-2.5 py-1 bg-rose-500/20 text-rose-400 rounded-lg border border-rose-500/40 font-mono font-bold";
  } else {
    cryptoStatusBadge.textContent = "✅ CRYPTOGRAPHIC INTEGRITY INTACT";
    cryptoStatusBadge.className = "text-xs px-2.5 py-1 bg-cyan-500/20 text-cyan-300 rounded-lg border border-cyan-500/40 font-mono font-semibold";
  }
}

// 1. RUN AGENT (RECORD)
btnRunAgent.addEventListener("click", async () => {
  btnRunAgent.disabled = true;
  btnRunAgent.innerHTML = `<span>⏳</span><span>Executing Agent...</span>`;

  try {
    const scenario = scenarioSelect.value;
    const res = await fetch("/api/run-agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario })
    });
    const data = await res.json();
    if (data.status === "SUCCESS") {
      activeTrace = data.trace;
      activeReplay = null;
      renderRecordedSteps(activeTrace);
      renderReplaySteps(null);
      renderHashChain(activeTrace, null);
      showToast("⚡", "Agent execution finished and trace saved!");
      showVerdict(
        "INFO",
        "AGENT EXECUTION RECORDED",
        `Completed ${activeTrace.total_steps} tool calls. Masked ${activeTrace.total_redactions} secrets. SHA-256 hash chain and HMAC signature sealed.`
      );
    } else {
      showToast("❌", data.message || "Failed to run agent");
    }
  } catch (err) {
    showToast("❌", `Network error: ${err.message}`);
  } finally {
    btnRunAgent.disabled = false;
    btnRunAgent.innerHTML = `<span>▶</span><span>1. Run Agent (Record)</span>`;
  }
});

// 2. REPLAY TRACE
btnReplay.addEventListener("click", async () => {
  if (!activeTrace) {
    showToast("⚠️", "Run an agent first to record a trace!");
    return;
  }

  btnReplay.disabled = true;
  btnReplay.innerHTML = `<span>🔄</span><span>Replaying Trace...</span>`;

  try {
    const res = await fetch("/api/replay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trace_id: "latest", simulate_drift: false })
    });
    const data = await res.json();
    if (data.status === "SUCCESS") {
      activeReplay = data.replay;
      renderReplaySteps(activeReplay);

      if (activeReplay.is_pass) {
        showVerdict("PASS", "REPLAY VERIFICATION: PASS", activeReplay.message);
        showToast("✅", "Replay completed with 100% fidelity!");
      } else {
        showVerdict("DIVERGENCE", "DIVERGENCE DETECTED", activeReplay.message);
        showToast("❌", "Divergence detected!");
      }
    } else {
      showToast("❌", data.message);
    }
  } catch (err) {
    showToast("❌", `Replay failed: ${err.message}`);
  } finally {
    btnReplay.disabled = false;
    btnReplay.innerHTML = `<span>🔄</span><span>2. Replay Trace</span>`;
  }
});

// 3. SIMULATE DRIFT / CHAOS
btnSimulateDrift.addEventListener("click", async () => {
  if (!activeTrace) {
    showToast("⚠️", "Run an agent first to record a baseline trace!");
    return;
  }

  btnSimulateDrift.disabled = true;
  showToast("⚡", "Simulating tool output drift...");

  try {
    const res = await fetch("/api/replay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trace_id: "latest", simulate_drift: true })
    });
    const data = await res.json();
    if (data.status === "SUCCESS") {
      activeReplay = data.replay;
      renderReplaySteps(activeReplay);
      showVerdict("DIVERGENCE", "❌ DIVERGENCE DETECTED", activeReplay.message);
      showToast("⚠️", "Divergence triggered & caught by harness!");
    }
  } catch (err) {
    showToast("❌", err.message);
  } finally {
    btnSimulateDrift.disabled = false;
  }
});

// 4. VERIFY INTEGRITY
btnVerify.addEventListener("click", async () => {
  btnVerify.disabled = true;
  btnVerify.innerHTML = `<span>🛡️</span><span>Verifying...</span>`;

  try {
    const res = await fetch("/api/verify-integrity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trace_id: "latest" })
    });
    const data = await res.json();
    if (data.status === "SUCCESS") {
      const v = data.verification;
      if (v.valid) {
        showVerdict("VERIFIED", "CRYPTOGRAPHIC INTEGRITY: VERIFIED", v.message);
        renderHashChain(activeTrace, null);
        showToast("🛡️", "Trace is authentic. No tampering detected.");
      } else {
        showVerdict("TAMPER", "🚨 TAMPERING DETECTED", v.message);
        renderHashChain(activeTrace, v.tampered_step);
        showToast("🚨", "Alert: Stored trace file has been tampered!");
      }
    } else {
      showToast("❌", data.message);
    }
  } catch (err) {
    showToast("❌", err.message);
  } finally {
    btnVerify.disabled = false;
    btnVerify.innerHTML = `<span>🛡️</span><span>3. Verify Trace</span>`;
  }
});

// 5. SIMULATE TAMPER
btnSimulateTamper.addEventListener("click", async () => {
  if (!activeTrace) {
    showToast("⚠️", "Run an agent first to record a trace!");
    return;
  }

  try {
    const res = await fetch("/api/simulate-tamper", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trace_id: "latest" })
    });
    const data = await res.json();
    if (data.status === "SUCCESS") {
      showToast("⚠️", "Trace file on disk altered without updating hash!");
      // Automatically trigger verification to illustrate detection
      setTimeout(() => {
        btnVerify.click();
      }, 400);
    } else {
      showToast("❌", data.message);
    }
  } catch (err) {
    showToast("❌", err.message);
  }
});

// 6. RESET STATE
btnReset.addEventListener("click", async () => {
  const scenario = scenarioSelect.value;
  try {
    const res = await fetch("/api/reset-state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario })
    });
    const data = await res.json();
    if (data.status === "SUCCESS") {
      activeTrace = data.trace;
      activeReplay = null;
      renderRecordedSteps(activeTrace);
      renderReplaySteps(null);
      renderHashChain(activeTrace, null);
      showVerdict("INFO", "ENVIRONMENT RESET", "Reset to pristine baseline trace. Active drifts and tampering cleared.");
      showToast("↺", "Reset to clean baseline.");
    }
  } catch (err) {
    showToast("❌", err.message);
  }
});

// Auto-run on page load to present instant working dashboard
window.addEventListener("DOMContentLoaded", () => {
  btnRunAgent.click();
});
