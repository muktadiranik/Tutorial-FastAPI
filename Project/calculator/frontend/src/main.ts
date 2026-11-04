import "./style.css";

interface Calculation {
  expression: string;
  result: string;
  timestamp: number;
}

const icons = {
  brand: '<path d="M5 7h6M8 4v6m7-3h5M5 17h6m4-2h5m-5 4h5"/>',
  history: '<path d="M3 11a9 9 0 1 1 2.7 7.4M3 4v7h7m2-4v5l3 2"/>',
  delete: '<path d="m9 5-7 7 7 7h12V5Zm4 4 6 6m0-6-6 6"/>',
  arrow: '<path d="M7 17 17 7M7 7h10v10"/>',
  keyboard: '<rect x="2" y="5" width="20" height="14" rx="3"/><path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 15h10"/>',
};

function icon(name: keyof typeof icons, className = ""): string {
  return `<svg class="icon ${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]}</svg>`;
}

document.querySelector<HTMLDivElement>("#app")!.innerHTML = `
  <div class="page-shell">
    <header class="site-header">
      <a class="brand" href="/" aria-label="calcula home"><span class="brand-mark">${icon("brand")}</span>calcula<span class="brand-dot">.</span></a>
      <div class="built-with"><span class="technology-dot"></span> Python <span class="plus">+</span> TypeScript</div>
    </header>

    <main>
      <section class="intro" aria-labelledby="page-title">
        <p class="eyebrow"><span></span> A LITTLE CLARITY, EVERY DAY</p>
        <h1 id="page-title">Good things <span>add up.</span></h1>
        <p class="intro-description">For quick answers and bigger ideas. A little space to do the math.</p>
      </section>

      <div class="workspace">
        <section class="calculator" aria-label="Calculator">
          <div class="calculator-heading"><span><span class="small-square">∑</span> Standard calculator</span><span class="precision-badge">28-digit precision</span></div>
          <div class="display">
            <p id="calculation-label" class="calculation-label">Let's work it out.</p>
            <label class="sr-only" for="expression">Expression</label>
            <input id="expression" type="text" inputmode="decimal" autocomplete="off" spellcheck="false" maxlength="256" placeholder="0" aria-describedby="feedback" />
            <p id="feedback" class="feedback" role="status" aria-live="polite">Ready when you are</p>
          </div>
          <div id="utility-keys" class="utility-keys" aria-label="Additional operations">
            <button type="button" data-token="(" aria-label="Open parenthesis">(</button>
            <button type="button" data-token=")" aria-label="Close parenthesis">)</button>
            <button type="button" data-token="%" aria-label="Percent, divide by one hundred">%</button>
            <button type="button" data-token="^2" aria-label="Square">x<sup>2</sup></button>
          </div>
          <div id="keypad" class="keypad">
            <button type="button" class="key key-clear" data-action="clear" aria-label="Clear all">AC</button>
            <button type="button" class="key key-function" data-action="sign" aria-label="Change sign">±</button>
            <button type="button" class="key key-function" data-action="delete" aria-label="Delete last character">${icon("delete")}</button>
            <button type="button" class="key key-operator" data-token="÷" aria-label="Divide">÷</button>
            <button type="button" class="key" data-token="7">7</button>
            <button type="button" class="key" data-token="8">8</button>
            <button type="button" class="key" data-token="9">9</button>
            <button type="button" class="key key-operator" data-token="×" aria-label="Multiply">×</button>
            <button type="button" class="key" data-token="4">4</button>
            <button type="button" class="key" data-token="5">5</button>
            <button type="button" class="key" data-token="6">6</button>
            <button type="button" class="key key-operator" data-token="−" aria-label="Subtract">−</button>
            <button type="button" class="key" data-token="1">1</button>
            <button type="button" class="key" data-token="2">2</button>
            <button type="button" class="key" data-token="3">3</button>
            <button type="button" class="key key-operator" data-token="+" aria-label="Add">+</button>
            <button type="button" class="key key-zero" data-token="0">0</button>
            <button type="button" class="key" data-token="." aria-label="Decimal point">.</button>
            <button id="equals" type="button" class="key key-equals" data-action="calculate" aria-label="Calculate">=</button>
          </div>
          <div class="keyboard-tip">${icon("keyboard")} Your keyboard works here, too <kbd>enter ↵</kbd></div>
        </section>

        <aside class="history-panel" aria-labelledby="history-title">
          <div class="history-heading"><h2 id="history-title">${icon("history")} Your calculations <span id="history-count">0</span></h2><button id="clear-history" type="button" class="text-button" hidden>Clear</button></div>
          <div id="history-list" class="history-list"></div>
          <div class="history-note"><span class="note-symbol">↗</span><p>A good idea to remember?<br /><span>Click any result to use it again.</span></p></div>
        </aside>
      </div>

      <div class="shortcuts" aria-label="Keyboard shortcuts"><span><kbd>enter</kbd> calculate</span><span><kbd>esc</kbd> clear all</span><span><kbd>⌫</kbd> delete</span></div>
    </main>

    <footer><span>Less friction. More figuring things out.</span><span class="footer-note"><span></span> Calculations powered by Python</span></footer>
  </div>
`;

const expression = document.querySelector<HTMLInputElement>("#expression")!;
const calculationLabel = document.querySelector<HTMLParagraphElement>("#calculation-label")!;
const feedback = document.querySelector<HTMLParagraphElement>("#feedback")!;
const historyList = document.querySelector<HTMLDivElement>("#history-list")!;
const historyCount = document.querySelector<HTMLSpanElement>("#history-count")!;
const clearHistoryButton = document.querySelector<HTMLButtonElement>("#clear-history")!;
const equalsButton = document.querySelector<HTMLButtonElement>("#equals")!;
const storageKey = "calcula.history.v1";
let history = loadHistory();
let justCalculated = false;
let busy = false;

function loadHistory(): Calculation[] {
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(storageKey) ?? "[]");
    if (!Array.isArray(stored)) return [];
    return stored.filter((item: unknown): item is Calculation => {
      if (typeof item !== "object" || item === null) return false;
      const value = item as Partial<Calculation>;
      return typeof value.expression === "string" && value.expression.length <= 256
        && typeof value.result === "string" && value.result.length <= 256
        && typeof value.timestamp === "number" && Number.isFinite(value.timestamp)
        && !Number.isNaN(new Date(value.timestamp).getTime());
    }).slice(0, 30);
  } catch {
    return [];
  }
}

function saveHistory(): void {
  try {
    localStorage.setItem(storageKey, JSON.stringify(history));
  } catch {
    // The calculator also works when browser storage is unavailable.
  }
}

function renderHistory(): void {
  historyList.replaceChildren();
  historyCount.textContent = String(history.length);
  clearHistoryButton.hidden = history.length === 0;
  if (history.length === 0) {
    historyList.innerHTML = `<div class="empty-history"><div class="empty-history-icon">${icon("history")}</div><h3>A fresh start.</h3><p>Your calculations will show up here.<br />Go on, make the first one.</p><span class="empty-example">24 × 7 = a little progress</span></div>`;
    return;
  }
  for (const item of history) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "history-item";
    button.setAttribute("aria-label", `Reuse result ${item.result} from ${item.expression}`);
    const top = document.createElement("span");
    top.className = "history-item-top";
    const formula = document.createElement("span");
    formula.className = "history-expression";
    formula.textContent = `${item.expression} =`;
    const time = document.createElement("time");
    time.dateTime = new Date(item.timestamp).toISOString();
    time.textContent = new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    top.append(formula, time);
    const result = document.createElement("span");
    result.className = "history-result";
    result.textContent = item.result;
    const arrow = document.createElement("span");
    arrow.className = "reuse-arrow";
    arrow.innerHTML = icon("arrow");
    result.append(arrow);
    button.append(top, result);
    button.addEventListener("click", () => {
      if (busy) return;
      expression.value = item.result;
      calculationLabel.textContent = `${item.expression} =`;
      justCalculated = true;
      setFeedback("Result restored. Keep the ideas coming.");
      focusExpression();
    });
    historyList.append(button);
  }
}

function setFeedback(message: string, error = false): void {
  feedback.textContent = message;
  feedback.classList.toggle("is-error", error);
  expression.setAttribute("aria-invalid", String(error));
}

function focusExpression(): void {
  expression.focus({ preventScroll: true });
  expression.setSelectionRange(expression.value.length, expression.value.length);
  expression.scrollLeft = expression.scrollWidth;
}

function edited(): void {
  justCalculated = false;
  calculationLabel.textContent = "Let's work it out.";
  setFeedback("Ready when you are");
}

function insertToken(token: string): void {
  if (busy) return;
  if (justCalculated && !/^[+\-−*×/÷^%]/.test(token)) expression.value = "";
  const start = expression.selectionStart ?? expression.value.length;
  const end = expression.selectionEnd ?? start;
  const next = expression.value.slice(0, start) + token + expression.value.slice(end);
  if (next.length > 256) {
    setFeedback("Keep expressions to 256 characters or fewer.", true);
    return;
  }
  expression.value = next;
  edited();
  expression.focus({ preventScroll: true });
  expression.setSelectionRange(start + token.length, start + token.length);
  expression.scrollLeft = expression.scrollWidth;
}

function clear(): void {
  expression.value = "";
  edited();
  focusExpression();
}

function backspace(): void {
  const start = expression.selectionStart ?? expression.value.length;
  const end = expression.selectionEnd ?? start;
  const from = start === end ? Math.max(0, start - 1) : start;
  expression.value = expression.value.slice(0, from) + expression.value.slice(end);
  edited();
  expression.focus({ preventScroll: true });
  expression.setSelectionRange(from, from);
}

function changeSign(): void {
  const value = expression.value.trim();
  const numeric = /^-?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value);
  const next = !value ? "-" : numeric ? (value.startsWith("-") ? value.slice(1) : `-${value}`) : `-(${value})`;
  if (next.length > 256) {
    setFeedback("Keep expressions to 256 characters or fewer.", true);
    return;
  }
  expression.value = next;
  edited();
  focusExpression();
}

function setBusy(value: boolean): void {
  busy = value;
  expression.disabled = value;
  document.querySelectorAll<HTMLButtonElement>("#keypad button, #utility-keys button").forEach(button => {
    button.disabled = value;
  });
  equalsButton.textContent = value ? "…" : "=";
  equalsButton.setAttribute("aria-busy", String(value));
}

async function calculate(): Promise<void> {
  if (busy) return;
  const formula = expression.value.trim();
  if (!formula) {
    setFeedback("Add a few numbers to get started.");
    focusExpression();
    return;
  }
  setBusy(true);
  setFeedback("Working it out…");
  try {
    const response = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expression: formula }),
      signal: AbortSignal.timeout(10000),
    });
    const data: unknown = await response.json();
    if (!response.ok) {
      const detail = typeof data === "object" && data !== null && "detail" in data ? data.detail : null;
      throw new Error(typeof detail === "string" ? detail : "Check your expression and try again.");
    }
    if (typeof data !== "object" || data === null || !("result" in data) || typeof data.result !== "string") {
      throw new Error("The server returned an unexpected response. Please try again.");
    }
    expression.value = data.result;
    calculationLabel.textContent = `${formula} =`;
    justCalculated = true;
    history.unshift({ expression: formula, result: data.result, timestamp: Date.now() });
    history = history.slice(0, 30);
    saveHistory();
    renderHistory();
    setFeedback("There you have it. Calculated with Python.");
  } catch (error) {
    const message = error instanceof TypeError || (error instanceof DOMException && error.name === "TimeoutError")
      ? "Couldn't reach Python. Start the API server and try again."
      : error instanceof Error ? error.message : "Something didn't add up. Please try again.";
    setFeedback(message, true);
  } finally {
    setBusy(false);
    focusExpression();
  }
}

document.querySelectorAll<HTMLButtonElement>("[data-token]").forEach(button => {
  button.addEventListener("click", () => insertToken(button.dataset.token!));
});

document.querySelectorAll<HTMLButtonElement>("[data-action]").forEach(button => {
  button.addEventListener("click", () => {
    if (busy) return;
    switch (button.dataset.action) {
      case "clear": clear(); break;
      case "delete": backspace(); break;
      case "sign": changeSign(); break;
      case "calculate": void calculate(); break;
    }
  });
});

clearHistoryButton.addEventListener("click", () => {
  history = [];
  saveHistory();
  renderHistory();
});

expression.addEventListener("beforeinput", event => {
  if (justCalculated && event.inputType === "insertText" && event.data && !/^[+\-−*×/÷^%]/.test(event.data)) {
    expression.value = "";
  }
});
expression.addEventListener("input", edited);

document.addEventListener("keydown", event => {
  if (busy || event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.key === "Enter" || event.key === "=") {
    // Allow Enter to activate focused buttons using the browser's native behavior.
    if (event.key === "Enter" && document.activeElement instanceof HTMLButtonElement) return;
    event.preventDefault();
    void calculate();
  } else if (event.key === "Escape") {
    event.preventDefault();
    clear();
  } else if (document.activeElement !== expression) {
    if (/^[0-9.+\-*/()%^]$/.test(event.key)) {
      event.preventDefault();
      insertToken(event.key === "*" ? "×" : event.key === "/" ? "÷" : event.key);
    } else if (event.key === "Backspace") {
      event.preventDefault();
      backspace();
    }
  }
});

renderHistory();
