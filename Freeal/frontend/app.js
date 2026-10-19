/**
 * Freeal Chatbot - Frontend Logic
 * Conecta con el backend FastAPI (http://localhost:8000), gestiona historial en localStorage,
 * renderiza markdown enriquecido y permite revisar consultas anteriores.
 */

const API_BASE_URL = "http://localhost:8000";
const STORAGE_KEY = "freeal_chat_history_v1";

// DOM Elements
const chatContainer = document.getElementById("chatContainer");
const chatViewport = document.querySelector(".chat-viewport");
const messageList = document.getElementById("messageList");
const welcomeScreen = document.getElementById("welcomeScreen");
const typingIndicator = document.getElementById("typingIndicator");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const clearChatBtn = document.getElementById("clearChatBtn");
const statusIndicator = document.getElementById("statusIndicator");
const statusText = statusIndicator.querySelector(".status-text");

// State: Array of { role: "user" | "assistant", content: string, timestamp: string }
let history = [];
let isGenerating = false;

// Initialize Marked configuration
if (window.marked) {
  marked.setOptions({
    breaks: true,
    gfm: true,
  });
}

/**
 * Load history from localStorage
 */
function loadHistory() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      history = JSON.parse(saved);
      if (Array.isArray(history) && history.length > 0) {
        welcomeScreen.classList.add("hidden");
        history.forEach((msg) => renderMessage(msg.role, msg.content, msg.timestamp, false));
        scrollToBottom();
      }
    }
  } catch (e) {
    console.error("Error al cargar historial local:", e);
    history = [];
  }
}

/**
 * Save history to localStorage
 */
function saveHistory() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch (e) {
    console.error("Error al guardar historial local:", e);
  }
}

/**
 * Formats ISO or Date timestamp to HH:mm
 */
function formatTime(isoString) {
  const date = isoString ? new Date(isoString) : new Date();
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Render a single message into the chat UI
 */
function renderMessage(role, content, timestamp = null, animate = true) {
  welcomeScreen.classList.add("hidden");

  const row = document.createElement("div");
  row.className = `message-row ${role}`;
  if (!animate) {
    row.style.animation = "none";
  }

  const timeStr = formatTime(timestamp);

  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    // Format content with marked + DOMPurify
    let formattedHtml = content;
    if (window.marked && window.DOMPurify) {
      formattedHtml = DOMPurify.sanitize(marked.parse(content));
    } else {
      formattedHtml = `<p>${escapeHtml(content).replace(/\n/g, "<br>")}</p>`;
    }

    bubble.innerHTML = `
      <div class="message-content">${formattedHtml}</div>
      <div class="message-meta">${timeStr}</div>
    `;

    row.appendChild(avatar);
    row.appendChild(bubble);
  } else {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = `
      <div class="message-content">${escapeHtml(content).replace(/\n/g, "<br>")}</div>
      <div class="message-meta">${timeStr}</div>
    `;
    row.appendChild(bubble);
  }

  messageList.appendChild(row);
  scrollToBottom();
}

/**
 * Scroll viewport to bottom
 */
function scrollToBottom() {
  setTimeout(() => {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }, 30);
}

/**
 * Escape HTML to prevent XSS in raw user inputs
 */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Adjust textarea height dynamically
 */
function adjustTextareaHeight() {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 160) + "px";
}

/**
 * Check backend connection status
 */
async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
    if (response.ok) {
      statusIndicator.className = "status-badge online";
      statusText.textContent = "Conectado";
    } else {
      statusIndicator.className = "status-badge offline";
      statusText.textContent = "Servicio inactivo";
    }
  } catch (err) {
    statusIndicator.className = "status-badge offline";
    statusText.textContent = "Sin conexión";
  }
}

/**
 * Send query to FastAPI backend
 */
async function handleSendMessage() {
  const query = userInput.value.trim();
  if (!query || isGenerating) return;

  const nowIso = new Date().toISOString();

  // Add user message to UI and history
  history.push({ role: "user", content: query, timestamp: nowIso });
  renderMessage("user", query, nowIso);
  saveHistory();

  // Reset input
  userInput.value = "";
  adjustTextareaHeight();
  sendBtn.disabled = true;
  userInput.focus();

  // Show typing indicator
  isGenerating = true;
  typingIndicator.classList.remove("hidden");
  scrollToBottom();

  // Prepare payload with last 10 conversation history items as requested by FastAPI
  const historyForBackend = history
    .slice(0, -1) // Exclude current question, since it's sent in 'question'
    .slice(-10)
    .map((item) => ({
      role: item.role,
      content: item.content,
    }));

  const payload = {
    question: query,
    mode: "hybrid",
    top_k: 50,
    only_need_context: false,
    conversation_history: historyForBackend,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let answerText = "";
    if (response.ok) {
      const data = await response.json();
      answerText = data.answer || "No se obtuvo respuesta del sistema.";
    } else {
      const errorData = await response.json().catch(() => ({}));
      answerText =
        errorData.detail ||
        `Error al procesar la consulta (${response.status}). Por favor, reintenta en unos instantes.`;
    }

    const botIso = new Date().toISOString();
    history.push({ role: "assistant", content: answerText, timestamp: botIso });
    renderMessage("assistant", answerText, botIso);
    saveHistory();
  } catch (error) {
    console.error("Error al conectar con el backend:", error);
    const errorMsg =
      "No se pudo conectar con el servidor local de Freeal en `http://localhost:8000`. Asegúrate de que el backend esté en ejecución (`uvicorn main:app`).";
    const botIso = new Date().toISOString();
    history.push({ role: "assistant", content: errorMsg, timestamp: botIso });
    renderMessage("assistant", errorMsg, botIso);
    saveHistory();
  } finally {
    isGenerating = false;
    typingIndicator.classList.add("hidden");
    userInput.disabled = false;
    userInput.focus();
    checkBackendHealth();
  }
}

/**
 * Clear chat history
 */
function handleClearChat() {
  if (history.length === 0) return;

  const confirmed = confirm(
    "¿Deseas reiniciar la conversación y borrar el historial de chats anteriores?"
  );
  if (!confirmed) return;

  history = [];
  localStorage.removeItem(STORAGE_KEY);
  messageList.innerHTML = "";
  welcomeScreen.classList.remove("hidden");
  userInput.value = "";
  adjustTextareaHeight();
  sendBtn.disabled = true;
  userInput.focus();
}

// Event Listeners
userInput.addEventListener("input", () => {
  adjustTextareaHeight();
  sendBtn.disabled = userInput.value.trim().length === 0 || isGenerating;
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled) {
      handleSendMessage();
    }
  }
});

sendBtn.addEventListener("click", handleSendMessage);
clearChatBtn.addEventListener("click", handleClearChat);

// Suggestion chips handler
document.querySelectorAll(".suggestion-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const promptText = chip.getAttribute("data-prompt");
    if (promptText) {
      userInput.value = promptText;
      adjustTextareaHeight();
      sendBtn.disabled = false;
      handleSendMessage();
    }
  });
});

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  loadHistory();
  checkBackendHealth();
  setInterval(checkBackendHealth, 15000); // Check status every 15s
  userInput.focus();
});
