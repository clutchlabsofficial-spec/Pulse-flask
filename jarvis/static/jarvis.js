/* J.A.R.V.I.S. console.
 *
 * Wispr Flow is a system-wide dictation tool: it types transcribed speech
 * straight into whatever field has focus. So the text box below IS the
 * microphone — we just watch for text arriving in bursts rather than
 * keystroke by keystroke, and send it once the dictation goes quiet.
 */
(() => {
  "use strict";

  const log = document.getElementById("log");
  const form = document.getElementById("composer");
  const input = document.getElementById("input");
  const send = document.getElementById("send");
  const player = document.getElementById("player");
  const reactor = document.getElementById("reactor");
  const mic = document.getElementById("mic");
  const autosend = document.getElementById("autosend");
  const speechToggle = document.getElementById("speech");
  const indicators = document.getElementById("indicators");

  const DICTATION_BURST = 6;      // chars arriving at once that mean "not typing"
  const DICTATION_SETTLE_MS = 1400; // silence after dictation before we send

  let busy = false;
  let lastLength = 0;
  let settleTimer = null;

  // ---------- rendering ----------
  function addTurn(who, text, cssClass) {
    const turn = document.createElement("div");
    turn.className = `turn ${cssClass}`;
    const label = document.createElement("div");
    label.className = "who";
    label.textContent = who;
    const body = document.createElement("div");
    body.className = "body";
    body.textContent = text;
    turn.append(label, body);
    log.append(turn);
    log.scrollTop = log.scrollHeight;
    return turn;
  }

  function addThinking() {
    const turn = addTurn(window.JARVIS.name, "", "jarvis");
    const dots = document.createElement("span");
    dots.className = "typing";
    dots.innerHTML = "<span></span><span></span><span></span>";
    turn.querySelector(".body").append(dots);
    return turn;
  }

  const TOOL_LABELS = {
    search_memory: (i) => `consulted vault · "${i.query || ""}"`,
    read_note: (i) => `read · ${i.path || ""}`,
    remember: (i) => `remembered · ${i.subject || ""}`,
    write_note: (i) => `wrote · ${i.path || ""}`,
    forget: (i) => `revised · ${i.path || ""}`,
    add_daily_note: () => "daily note updated",
    list_recent_notes: () => "reviewed recent notes",
  };

  function addTools(turn, calls) {
    if (!calls || !calls.length) return;
    const wrap = document.createElement("div");
    wrap.className = "tools";
    for (const call of calls) {
      const chip = document.createElement("span");
      chip.className = "tool" + (call.ok ? "" : " failed");
      const label = TOOL_LABELS[call.tool] || (() => call.tool);
      chip.textContent = call.ok ? label(call.input || {}) : `${call.tool} failed`;
      wrap.append(chip);
    }
    turn.append(wrap);
  }

  // ---------- speech ----------
  async function speak(text) {
    if (!speechToggle.checked || !text) return;
    try {
      const res = await fetch("/api/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        console.warn("voice unavailable:", err.error || res.status);
        return;
      }
      const url = URL.createObjectURL(await res.blob());
      player.src = url;
      reactor.classList.add("speaking");
      player.onended = player.onerror = () => {
        reactor.classList.remove("speaking");
        URL.revokeObjectURL(url);
      };
      await player.play().catch(() => reactor.classList.remove("speaking"));
    } catch (err) {
      console.warn("speech failed:", err);
      reactor.classList.remove("speaking");
    }
  }

  // ---------- the turn ----------
  async function submit(text, source) {
    if (busy || !text.trim()) return;
    busy = true;
    send.disabled = true;
    clearTimeout(settleTimer);
    mic.classList.remove("live");

    addTurn(window.JARVIS.user, text, "you");
    input.value = "";
    lastLength = 0;
    autoGrow();

    const pending = addThinking();
    reactor.classList.add("thinking");

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source: source || "text" }),
      });
      const data = await res.json();
      pending.remove();
      if (!res.ok) {
        addTurn("system", data.error || `Request failed (${res.status}).`, "error");
        return;
      }
      const turn = addTurn(window.JARVIS.name, data.text, "jarvis");
      addTools(turn, data.tool_calls);
      log.scrollTop = log.scrollHeight;
      speak(data.speakable || data.text);
    } catch (err) {
      pending.remove();
      addTurn("system", `Connection lost: ${err.message}`, "error");
    } finally {
      reactor.classList.remove("thinking");
      busy = false;
      send.disabled = false;
      input.focus();
    }
  }

  // ---------- input handling ----------
  function autoGrow() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 180) + "px";
  }

  input.addEventListener("input", (event) => {
    autoGrow();
    const value = input.value;
    const delta = value.length - lastLength;
    lastLength = value.length;

    const inserted = event.inputType === "insertFromPaste" || delta >= DICTATION_BURST;
    if (!inserted || !autosend.checked || busy) {
      if (!inserted) clearTimeout(settleTimer);
      return;
    }
    // Text arrived in a burst: Wispr Flow is dictating. Wait for it to settle.
    mic.classList.add("live");
    clearTimeout(settleTimer);
    settleTimer = setTimeout(() => {
      mic.classList.remove("live");
      const text = input.value.trim();
      if (text) submit(text, "wispr-flow");
    }, DICTATION_SETTLE_MS);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      clearTimeout(settleTimer);
      submit(input.value.trim(), "text");
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submit(input.value.trim(), "text");
  });

  document.getElementById("reset").addEventListener("click", async () => {
    await fetch("/api/reset", { method: "POST" });
    log.innerHTML = "";
    addTurn("system", "Working context cleared. The vault remembers everything that matters.", "jarvis");
    input.focus();
  });

  // Keep focus on the input so the Wispr Flow hotkey always lands here.
  document.addEventListener("click", (event) => {
    if (!event.target.closest("button, input, a, .log")) input.focus();
  });

  // ---------- status ----------
  async function refreshStatus() {
    try {
      const status = await (await fetch("/api/status")).json();
      const state = {
        brain: status.brain.ready,
        memory: status.memory.available,
        voice: status.voice.ready,
      };
      const detail = {
        brain: status.brain.model,
        memory: status.memory.available ? `${status.memory.notes} notes` : "no vault",
        voice: status.voice.ready ? status.voice.model : "no key",
      };
      for (const chip of indicators.querySelectorAll(".chip")) {
        const key = chip.dataset.key;
        chip.classList.toggle("up", !!state[key]);
        chip.classList.toggle("down", !state[key]);
        chip.title = detail[key] || "";
      }
    } catch (err) {
      console.warn("status unavailable", err);
    }
  }

  refreshStatus();
  setInterval(refreshStatus, 30000);
  autoGrow();
})();
