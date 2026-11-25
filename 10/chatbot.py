# /// script
# requires-python = ">=3.12"
# dependencies = ["fastapi>=0.111,<1", "httpx>=0.27,<1", "uvicorn>=0.29,<1"]
# ///
"""Single-file FastAPI chatbot powered by a local Ollama server.

Quick start (from the repository root):
    ollama pull llama3.2:1b
    uv run 10/ChatBot.py

Open http://127.0.0.1:8000 in your browser. Start the Ollama desktop app
or run `ollama serve` in another terminal if Ollama is not already running.

Optional environment variables:
    OLLAMA_MODEL: downloaded model name (default: llama3.2:1b).
    OLLAMA_BASE_URL: server URL (default: http://127.0.0.1:11434).

This is a local development example, not an authenticated public service.
History stays in the browser tab's memory; refreshing the page clears it.
"""

import os
from html import escape
from typing import Annotated, Literal

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, StringConstraints

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_TIMEOUT = httpx.Timeout(120.0, connect=5.0)
SYSTEM_PROMPT = "You are a helpful, friendly assistant. Give clear and accurate answers."

app = FastAPI(title="Ollama Chatbot")

MessageText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class ChatMessage(BaseModel):
    """One previous user or assistant message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=16000)


class ChatRequest(BaseModel):
    """The latest message and at most ten previous conversation turns."""

    message: MessageText
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    """The assistant's reply and the model that generated it."""

    reply: str
    model: str


PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ollama Chatbot</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; background: #f3f5fa; color: #172033; font-family: system-ui, sans-serif; }
    main { max-width: 860px; height: 100dvh; margin: auto; padding: 24px;
           display: flex; flex-direction: column; gap: 16px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    h1 { margin: 0; font-size: 24px; }
    p { margin: 6px 0 0; color: #526078; font-size: 14px; }
    button { border: 0; border-radius: 10px; padding: 12px 18px; font: inherit; cursor: pointer;
             background: #3159db; color: white; }
    button.secondary { background: #e2e7f3; color: #172033; }
    button:disabled { cursor: wait; opacity: .55; }
    #messages { flex: 1; min-height: 0; overflow-y: auto; display: flex;
                flex-direction: column; gap: 14px; padding: 20px; background: white;
                border: 1px solid #dce2ee; border-radius: 16px; }
    .message { max-width: 90%; padding: 12px 16px; border-radius: 12px; white-space: pre-wrap;
               overflow-wrap: anywhere; line-height: 1.6; background: #eef1f7; align-self: flex-start; }
    .user { background: #3159db; color: white; align-self: flex-end; }
    .label { display: block; font-size: 12px; font-weight: 700; margin-bottom: 4px; opacity: .8; }
    #status { min-height: 22px; margin: 0; }
    #status.error { color: #b42318; }
    form { display: flex; align-items: flex-end; gap: 10px; }
    textarea { flex: 1; min-width: 0; resize: vertical; max-height: 180px; border: 1px solid #c4cddd;
               border-radius: 12px; padding: 14px; font: inherit; }
    textarea:focus { outline: 2px solid #3159db; outline-offset: 2px; }
    footer { color: #526078; text-align: center; font-size: 12px; }
    @media (max-width: 540px) { main { padding: 12px; } #messages { padding: 12px; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div><h1>Ollama Chatbot</h1><p>Model: __MODEL__</p></div>
      <button id="clear" class="secondary" type="button">New chat</button>
    </header>
    <section id="messages" role="log" aria-label="Conversation" aria-live="polite"></section>
    <p id="status" role="status" aria-live="polite"></p>
    <form id="chat-form">
      <textarea id="message" rows="2" maxlength="4000" placeholder="Ask anything..."
                aria-label="Your message" required></textarea>
      <button id="send" type="submit">Send</button>
    </form>
    <footer>Enter to send · Shift+Enter for a new line · Refresh to clear history</footer>
  </main>
  <script>
    const form = document.querySelector("#chat-form");
    const input = document.querySelector("#message");
    const messages = document.querySelector("#messages");
    const status = document.querySelector("#status");
    const send = document.querySelector("#send");
    const clear = document.querySelector("#clear");
    let history = [];
    let busy = false;

    function addMessage(role, content) {
      const bubble = document.createElement("div");
      bubble.className = `message ${role}`;
      const label = document.createElement("span");
      label.className = "label";
      label.textContent = role === "user" ? "You" : "Assistant";
      bubble.append(label, document.createTextNode(content));
      messages.append(bubble);
      messages.scrollTop = messages.scrollHeight;
      return bubble;
    }

    function resetChat() {
      history = [];
      messages.replaceChildren();
      addMessage("assistant", "Hi! What would you like to talk about?");
      status.textContent = "";
      status.className = "";
      input.value = "";
      input.focus();
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message || busy) return;
      busy = true;
      send.disabled = clear.disabled = input.disabled = true;
      input.value = "";
      status.className = "";
      status.textContent = "Thinking... The first reply may take a little longer.";
      const bubble = addMessage("user", message);
      try {
        const response = await fetch("/chat", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({message, history}),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(typeof data.detail === "string" ? data.detail : "Invalid chat request.");
        }
        addMessage("assistant", data.reply);
        history.push({role: "user", content: message}, {role: "assistant", content: data.reply});
        history = history.slice(-20);
        status.textContent = "";
      } catch (error) {
        bubble.remove();
        input.value = message;
        status.className = "error";
        status.textContent = error.message || "Could not reach the chatbot. Please try again.";
      } finally {
        busy = false;
        send.disabled = clear.disabled = input.disabled = false;
        input.focus();
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
    clear.addEventListener("click", resetChat);
    resetChat();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    """Serve the self-contained chat interface."""
    return HTMLResponse(PAGE.replace("__MODEL__", escape(OLLAMA_MODEL)))


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Send browser-provided history to Ollama without shared server-side memory."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[message.model_dump() for message in request.history],
        {"role": "user", "content": request.message},
    ]
    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT, trust_env=False) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": 512},
                },
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Ollama took too long to reply. Try a shorter message or smaller model.") from exc
    except httpx.RequestError as exc:
        raise HTTPException(503, "Cannot reach Ollama. Start the Ollama app or run 'ollama serve'.") from exc

    if response.status_code == 404:
        raise HTTPException(503, f"Model unavailable. Download it with: ollama pull {OLLAMA_MODEL}")
    if response.is_error:
        raise HTTPException(502, f"Ollama returned an error (HTTP {response.status_code}). Check its server logs.")

    try:
        reply = response.json()["message"]["content"]
        if not isinstance(reply, str) or not reply.strip() or len(reply) > 16000:
            raise ValueError("Expected a non-empty text reply of at most 16000 characters.")
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(502, "Ollama returned an invalid or empty reply. Try another chat model.") from exc

    return ChatResponse(reply=reply, model=OLLAMA_MODEL)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
