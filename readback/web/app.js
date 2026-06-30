const el = (id) => document.getElementById(id);

const state = { paperId: null, words: [], wordEnds: [], raf: null, selection: "" };

// ---- Chat panel toggle -----------------------------------------------------
el("chat-toggle").addEventListener("click", toggleChat);

function toggleChat() {
  const panel = el("chat-panel");
  const toggle = el("chat-toggle");
  const layout = document.querySelector(".layout");
  const hidden = panel.classList.toggle("hidden-chat");
  layout.classList.toggle("no-chat", hidden);
  toggle.textContent = hidden ? "\u2190" : "\u2192";
  toggle.classList.toggle("shifted", !hidden);
}

// ---- Chat panel toggle -----------------------------------------------------

// ---- Error helpers ---------------------------------------------------------
el("error-close").addEventListener("click", () => el("error-banner").classList.add("hidden"));

function showError(message) {
  el("error-text").textContent = message;
  el("error-banner").classList.remove("hidden");
  setStatus("Error", true);
}

function clearError() {
  el("error-banner").classList.add("hidden");
}

function showSpinner(label = "Working…") {
  el("spinner-label").textContent = label;
  el("spinner").classList.remove("hidden");
}

function hideSpinner() {
  el("spinner").classList.add("hidden");
}

/**
 * Central fetch wrapper. Returns parsed JSON on success.
 * Throws a friendly Error on network failure or non-2xx responses.
 */
async function apiCall(path, body) {
  let res;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (networkErr) {
    throw new Error(
      "Can't reach the Readback server. Is `readback-web` still running on this port?"
    );
  }

  let data = {};
  try { data = await res.json(); } catch (_) { /* non-JSON body */ }

  if (res.ok) return data;

  // Map common statuses to human explanations, falling back to server detail.
  const detail = data.detail || "";
  if (res.status === 0 || res.status >= 500) {
    throw new Error(detail || `Server error (${res.status}). Check the readback-web terminal for a traceback.`);
  }
  if (res.status === 404) {
    throw new Error(detail || "Not found. The server may have restarted — try loading the paper again.");
  }
  if (res.status === 400) {
    throw new Error(detail || "Bad request — the URL or input wasn't accepted.");
  }
  if (res.status === 422) {
    throw new Error("Malformed request to the server.");
  }
  throw new Error(detail || `Request failed (${res.status}).`);
}

// ---- Load ------------------------------------------------------------------
el("load-btn").addEventListener("click", load);
el("url").addEventListener("keydown", (e) => { if (e.key === "Enter") load(); });

async function load() {
  const url = el("url").value.trim();
  if (!url) return;
  clearError();
  setStatus("Fetching + cleaning paper (this takes a moment)…");
  showSpinner("Fetching + cleaning paper…");
  try {
    const data = await apiCall("/api/load", { url });
    state.paperId = data.paper_id;
    el("paper-title").textContent = data.title;
    el("paper-meta").classList.remove("hidden");
    el("generate-btn").disabled = false;
    el("player-row").classList.add("hidden");
    renderScript(data.text);
    el("pdf-download").href = "/api/pdf/" + data.paper_id;
    el("pdf-download").classList.remove("hidden");
    setStatus("Loaded");
  } catch (err) {
    showError(err.message);
  } finally {
    hideSpinner();
  }
}

// ---- Generate audio --------------------------------------------------------
el("generate-btn").addEventListener("click", generate);

async function generate() {
  if (!state.paperId) { showError("Load a paper first."); return; }
  clearError();
  const btn = el("generate-btn");
  btn.disabled = true;
  showSpinner("Generating audio…");
  try {
    setStatus("Generating audio…");
    const data = await apiCall("/api/audio", { paper_id: state.paperId });
    const audio = el("audio");
    audio.src = data.audio_url;
    el("player-row").classList.remove("hidden");
    setStatus("Ready");
  } catch (err) {
    showError(err.message);
  } finally {
    hideSpinner();
    btn.disabled = false;
  }
}

function renderScript(script) {
  const container = el("script");
  container.innerHTML = "";
  state.words = script.trim().split(/\s+/);
  state.wordEnds = [];
  const totalWeight = state.words.reduce((s, w) => s + Math.max(w.length, 1), 0) || 1;
  let cumulative = 0;
  state.words.forEach((word, i) => {
    cumulative += Math.max(word.length, 1);
    state.wordEnds.push(cumulative / totalWeight); // fraction of duration, resolved on metadata
    const span = document.createElement("span");
    span.className = "word";
    span.dataset.i = i;
    span.textContent = word;
    container.appendChild(span);
    container.appendChild(document.createTextNode(" "));
  });
}

// ---- Karaoke highlight -----------------------------------------------------
const audio = el("audio");
audio.addEventListener("loadedmetadata", () => {
  const dur = audio.duration && isFinite(audio.duration) ? audio.duration : 0;
  state.wordEnds = state.wordEnds.map((f) => f * dur);
  if (state.raf) cancelAnimationFrame(state.raf);
  tick();
});

function tick() {
  const t = audio.currentTime;
  const idx = state.wordEnds.findIndex((end) => t < end);
  const active = idx === -1 ? state.words.length - 1 : idx;
  const spans = el("script").querySelectorAll(".word");
  spans.forEach((s, i) => s.classList.toggle("active", i === active));
  const activeSpan = spans[active];
  if (activeSpan && audio.paused === false) {
    activeSpan.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  state.raf = requestAnimationFrame(tick);
}

// ---- Selection + Chat ------------------------------------------------------
document.addEventListener("selectionchange", () => {
  const sel = window.getSelection();
  const node = sel.anchorNode;
  const inScript = node && el("script").contains(node) && sel.toString().trim().length > 0;
  state.selection = inScript ? sel.toString().trim() : "";
  el("sel-badge").classList.toggle("hidden", !state.selection);
});

el("send-btn").addEventListener("click", send);
el("question").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });

async function send() {
  if (!state.paperId) { showError("Load a paper first."); return; }
  const question = el("question").value.trim();
  if (!question) return;
  clearError();
  addMsg("user", question);
  el("question").value = "";
  const meta = addMsg("meta", "Thinking…");

  try {
    const data = await apiCall("/api/chat", {
      paper_id: state.paperId,
      question,
      selection: state.selection,
    });
    meta.remove();
    addMsg("bot", data.answer);
    if (state.selection) {
      state.selection = "";
      el("sel-badge").classList.add("hidden");
    }
  } catch (err) {
    meta.remove();
    addMsg("bot", "Error: " + err.message);
    showError(err.message);
  }
}

// ---- Library ---------------------------------------------------------------
el("library-btn").addEventListener("click", openLibrary);
el("library-close").addEventListener("click", () => el("library-panel").classList.add("hidden"));

async function openLibrary() {
  el("library-panel").classList.toggle("hidden");
  if (!el("library-panel").classList.contains("hidden")) {
    await refreshLibrary();
  }
}

async function refreshLibrary() {
  const list = el("library-list");
  list.innerHTML = '<div class="library-empty">Loading…</div>';
  try {
    const res = await fetch("/api/papers");
    const data = await res.json();
    if (!data.papers || data.papers.length === 0) {
      list.innerHTML = '<div class="library-empty">No papers loaded yet.</div>';
      return;
    }
    list.innerHTML = "";
    data.papers.forEach((p) => {
      const item = document.createElement("div");
      item.className = "library-item";
      const audio = p.has_audio ? '<span class="li-audio">has audio</span>' : "";
      item.innerHTML =
        '<div class="li-title">' + escapeHtml(p.title) + '</div>' +
        '<div class="li-meta">' + (p.saved_at || "") + " &middot; " +
        p.char_count.toLocaleString() + " chars " + audio + '</div>';
      item.addEventListener("click", () => reopen(p.paper_id));
      list.appendChild(item);
    });
  } catch {
    list.innerHTML = '<div class="library-empty">Could not load library.</div>';
  }
}

async function reopen(paperId) {
  el("library-panel").classList.add("hidden");
  clearError();
  setStatus("Opening from library…");
  showSpinner("Opening from library…");
  try {
    const res = await fetch("/api/papers/" + paperId);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "could not reopen");
    state.paperId = data.paper_id;
    el("paper-title").textContent = data.title;
    el("paper-meta").classList.remove("hidden");
    el("generate-btn").disabled = false;
    renderScript(data.text);
    el("pdf-download").href = "/api/pdf/" + data.paper_id;
    el("pdf-download").classList.remove("hidden");
    setStatus("Loaded from library");
  } catch (err) {
    showError(err.message);
  } finally {
    hideSpinner();
  }
}

// ---- helpers ---------------------------------------------------------------
function addMsg(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  if (role === "bot") {
    const body = document.createElement("div");
    body.innerHTML = renderMarkdown(text);
    div.appendChild(body);
  } else {
    div.textContent = text;
  }
  el("messages").appendChild(div);
  el("messages").scrollTop = el("messages").scrollHeight;
  return div;
}

/**
 * Minimal, safe markdown renderer for chat replies.
 * Supports: headings, bold, italic, inline code, code blocks,
 * bullet/numbered lists, and paragraphs. HTML-escapes everything first.
 */
function renderMarkdown(text) {
  const esc = escapeHtml(text);
  const lines = esc.split("\n");
  let html = "";
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Code block (```...```)
    if (line.startsWith("```")) {
      const buf = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        buf.push(lines[i]);
        i++;
      }
      if (inList) { html += "</ul>"; inList = false; }
      html += '<pre class="code-block">' + escapeHtml(buf.join("\n")) + "</pre>";
      continue;
    }

    // Headings
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      if (inList) { html += "</ul>"; inList = false; }
      const level = heading[1].length;
      html += `<h${level}>${inline(heading[2])}</h${level}>`;
      continue;
    }

    // Bullet list
    if (/^\s*[-*]\s+/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += "<li>" + inline(line.replace(/^\s*[-*]\s+/, "")) + "</li>";
      continue;
    }

    // Numbered list
    if (/^\s*\d+\.\s+/.test(line)) {
      if (!inList) { html += "<ol>"; inList = true; }
      html += "<li>" + inline(line.replace(/^\s*\d+\.\s+/, "")) + "</li>";
      continue;
    }

    // Close any open list
    if (inList && line.trim() === "") {
      html += inList ? "</ul>" : "";
      inList = false;
    }

    // Paragraph (skip empty lines between blocks)
    if (line.trim() === "") continue;
    html += "<p>" + inline(line) + "</p>";
  }
  if (inList) html += "</ul>";
  return html;
}

/** Inline formatting: bold, italic, inline code. */
function inline(text) {
  return text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/(?<!\w)_([^_]+)_(?!\w)/g, '<em>$1</em>');
}

function setStatus(text, isError = false) {
  const s = el("status");
  s.textContent = text;
  s.style.color = isError ? "#f87171" : "#9aa3b2";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}
