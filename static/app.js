const text = document.querySelector("#offer-text");
const form = document.querySelector("#checker");
const count = document.querySelector("#count");
const formError = document.querySelector("#form-error");
const examples = document.querySelector("#examples");
const waiting = document.querySelector("#waiting");
const result = document.querySelector("#result");
const chat = document.querySelector("#chat");
const thread = document.querySelector("#thread");
const context = document.querySelector("#chat-context");
const ask = document.querySelector("#ask");
const question = document.querySelector("#question");

let sessionId = "";

const labels = {
  risky: "Risky",
  unclear: "Unclear",
  credible: "Credible",
};

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[character]));
}

function showError(message) {
  formError.hidden = !message;
  formError.textContent = message || "";
}

text.addEventListener("input", () => {
  count.textContent = `${text.value.length} characters`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await analyse(text.value);
});

text.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    form.requestSubmit();
  }
});

ask.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = question.value.trim();
  if (!value) return;
  question.value = "";
  await send(value);
});

document.querySelector("#prompts").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-ask]");
  if (button) send(button.dataset.ask);
});

async function loadExamples() {
  const response = await fetch("/api/examples");
  const payload = await response.json();
  examples.innerHTML = payload.examples.map((item) => `
    <button type="button" data-example="${escapeHtml(item.id)}">${escapeHtml(item.title)}</button>
  `).join("");
  examples.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-example]");
    if (!button) return;
    const item = payload.examples.find((example) => example.id === button.dataset.example);
    text.value = item.text;
    count.textContent = `${text.value.length} characters`;
    for (const node of examples.querySelectorAll("button")) {
      node.setAttribute("aria-pressed", node === button ? "true" : "false");
    }
    analyse(item.text);
  });
}

async function analyse(raw) {
  const body = raw.trim();
  if (!body) {
    showError("Paste the offer message first.");
    return;
  }
  showError("");
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Reading…";
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: body }),
    });
    const payload = await response.json();
    if (!response.ok) {
      showError(payload.detail || "The check failed.");
      return;
    }
    sessionId = payload.session_id;
    render(payload, body);
  } catch (_error) {
    showError("Offer Lens could not be reached.");
  } finally {
    button.disabled = false;
    button.textContent = "Check this offer";
  }
}

function render(payload, body) {
  waiting.hidden = true;
  result.hidden = false;
  const percent = Math.round((payload.score ?? payload.confidence) * 100);
  const shares = payload.shares || payload.probabilities;
  const order = ["risky", "unclear", "credible"];
  result.innerHTML = `
    <div class="score-row">
      <div>
        <p class="stamp ${escapeHtml(payload.label)}">${labels[payload.label]}</p>
        <p class="confidence">${percent}<span> / 100 offer score</span></p>
      </div>
    </div>
    <p class="summary">${escapeHtml(payload.summary)}</p>
    ${payload.override_note ? `<p class="note">${escapeHtml(payload.override_note)}</p>` : ""}
    <div class="bars">
      ${order.map((label) => `
        <div class="bar">
          <span>${labels[label]}</span>
          <div class="track ${label}"><span style="width:${Math.round((shares[label] || 0) * 100)}%"></span></div>
          <span>${Math.round((shares[label] || 0) * 100)}%</span>
        </div>
      `).join("")}
    </div>
    ${signalBlock("Quoted from the message", payload.risk_signals, "")}
    ${signalBlock("What looks official", payload.support_signals, "support")}
    ${payload.cues.length ? `<div class="group"><h3>Phrases the model used</h3><ul class="chips">${payload.cues.map((cue) => `<li>${escapeHtml(cue)}</li>`).join("")}</ul></div>` : ""}
    <div class="group">
      <h3>Before you reply</h3>
      ${payload.checklist.map((item) => `
        <div class="check">
          <span aria-hidden="true">${item.emphasis ? "●" : "○"}</span>
          <p>${item.emphasis ? `<strong>${escapeHtml(item.text)}</strong>` : escapeHtml(item.text)}</p>
        </div>
      `).join("")}
    </div>
  `;
  thread.innerHTML = "";
  context.textContent = body.slice(0, 180) + (body.length > 180 ? "…" : "");
  chat.hidden = false;
  result.scrollIntoView({ block: "nearest" });
}

function signalBlock(title, items, className) {
  if (!items.length) return "";
  return `
    <div class="group ${className}">
      <h3>${title}</h3>
      ${items.map((item) => `
        <article class="signal ${escapeHtml(item.severity || "")}">
          <h3>${escapeHtml(item.title)}</h3>
          <blockquote>${escapeHtml(item.excerpt)}</blockquote>
          <p>${escapeHtml(item.detail)}</p>
        </article>
      `).join("")}
    </div>
  `;
}

async function send(value) {
  if (!sessionId) return;
  addBubble("user", value);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      addBubble("assistant", payload.detail || "I lost this offer. Check it again.");
      return;
    }
    addBubble("assistant", payload.reply);
  } catch (_error) {
    addBubble("assistant", "Offer Lens could not be reached.");
  }
}

function addBubble(role, value) {
  const node = document.createElement("p");
  node.className = `bubble ${role}`;
  node.textContent = value;
  thread.appendChild(node);
  node.scrollIntoView({ block: "nearest" });
}

loadExamples().catch(() => {
  showError("Example messages could not be loaded.");
});
