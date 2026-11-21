const $ = (selector) => document.querySelector(selector);

const els = {
  dropZone: $("#drop-zone"), fileInput: $("#file-input"), uploadProgress: $("#upload-progress"),
  progressBar: $("#progress-bar"), progressLabel: $("#progress-label"), documentCard: $("#document-card"),
  documentStatus: $("#document-status"), fileType: $("#file-type"), fileName: $("#file-name"),
  fileMeta: $("#file-meta"), deleteButton: $("#delete-button"), deleteModal: $("#delete-modal"),
  cancelDelete: $("#cancel-delete"), confirmDelete: $("#confirm-delete"), serviceStatus: $("#service-status"),
  welcome: $("#welcome"), messages: $("#messages"), chat: $("#chat"), form: $("#chat-form"),
  input: $("#question-input"), send: $("#send-button"), toast: $("#toast"),
};

let documentInfo = null;
let history = [];
let busy = false;
let toastTimer;

function showToast(message, isError = false) {
  clearTimeout(toastTimer);
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
  els.toast.hidden = false;
  toastTimer = setTimeout(() => { els.toast.hidden = true; }, 4200);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = units[0];
  for (let i = 1; value >= 1024 && i < units.length; i += 1) { value /= 1024; unit = units[i]; }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${unit}`;
}

function renderDocument() {
  const ready = Boolean(documentInfo);
  els.dropZone.classList.toggle("hidden", ready);
  els.documentCard.hidden = !ready;
  els.documentStatus.textContent = ready ? "Ready" : "Empty";
  els.documentStatus.classList.toggle("ready", ready);
  els.input.disabled = !ready || busy;
  els.send.disabled = !ready || busy;
  els.input.placeholder = ready ? "Ask a question about your document…" : "Upload a document to start asking questions";

  if (ready) {
    const extension = documentInfo.name.split(".").pop().toUpperCase();
    els.fileType.textContent = extension;
    els.fileName.textContent = documentInfo.name;
    els.fileMeta.textContent = `${formatBytes(documentInfo.size)} · ${documentInfo.chunk_count} searchable sections`;
  }
}

function setProgress(percent) {
  els.progressBar.style.width = `${percent}%`;
  els.progressLabel.textContent = `${percent}%`;
}

async function upload(file) {
  if (!file) return;
  const allowed = ["pdf", "docx", "txt"];
  const extension = file.name.split(".").pop().toLowerCase();
  if (!allowed.includes(extension)) { showToast("Choose a PDF, DOCX, or TXT file.", true); return; }
  if (file.size > 20 * 1024 * 1024) { showToast("The file is larger than 20 MB.", true); return; }

  els.dropZone.classList.add("hidden");
  els.documentCard.hidden = true;
  els.uploadProgress.hidden = false;
  setProgress(12);
  const form = new FormData();
  form.append("file", file);
  const timer = setInterval(() => {
    const current = Number.parseInt(els.progressLabel.textContent, 10);
    setProgress(Math.min(current + Math.ceil(Math.random() * 8), 88));
  }, 400);

  try {
    const response = await fetch("/api/document", { method: "POST", body: form });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Upload failed.");
    setProgress(100);
    documentInfo = payload;
    history = [];
    els.messages.replaceChildren();
    els.welcome.hidden = false;
    setTimeout(() => { els.uploadProgress.hidden = true; renderDocument(); }, 300);
    showToast("Document indexed and ready.");
  } catch (error) {
    els.uploadProgress.hidden = true;
    els.dropZone.classList.remove("hidden");
    showToast(error.message, true);
  } finally {
    clearInterval(timer);
    els.fileInput.value = "";
  }
}

function addMessage(role, content, loading = false) {
  const row = document.createElement("div");
  row.className = `message ${role}`;
  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "assistant-avatar";
    avatar.textContent = "L";
    row.append(avatar);
  }
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  if (loading) {
    bubble.innerHTML = '<div class="typing"><i></i><i></i><i></i></div>';
  } else {
    bubble.textContent = content;
  }
  row.append(bubble);
  els.messages.append(row);
  els.chat.scrollTo({ top: els.chat.scrollHeight, behavior: "smooth" });
  return row;
}

async function ask(question) {
  question = question.trim();
  if (!question || busy || !documentInfo) return;
  busy = true;
  renderDocument();
  els.welcome.hidden = true;
  addMessage("user", question);
  const pending = addMessage("assistant", "", true);
  els.input.value = "";
  autoResize();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Could not generate an answer.");
    pending.querySelector(".message-bubble").textContent = payload.answer;
    history.push({ role: "user", content: question }, { role: "assistant", content: payload.answer });
    history = history.slice(-12);
  } catch (error) {
    pending.remove();
    addMessage("assistant", `Sorry, I couldn't answer that. ${error.message}`);
  } finally {
    busy = false;
    renderDocument();
    els.input.focus();
  }
}

function autoResize() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 140)}px`;
}

async function deleteDocument() {
  els.confirmDelete.disabled = true;
  try {
    const response = await fetch("/api/document", { method: "DELETE" });
    if (!response.ok) throw new Error("Delete failed.");
    documentInfo = null;
    history = [];
    els.messages.replaceChildren();
    els.welcome.hidden = false;
    els.deleteModal.hidden = true;
    renderDocument();
    showToast("Document and local index deleted.");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    els.confirmDelete.disabled = false;
  }
}

els.dropZone.addEventListener("dragover", (event) => { event.preventDefault(); els.dropZone.classList.add("dragging"); });
els.dropZone.addEventListener("dragleave", () => els.dropZone.classList.remove("dragging"));
els.dropZone.addEventListener("drop", (event) => { event.preventDefault(); els.dropZone.classList.remove("dragging"); upload(event.dataTransfer.files[0]); });
els.fileInput.addEventListener("change", () => upload(els.fileInput.files[0]));
els.form.addEventListener("submit", (event) => { event.preventDefault(); ask(els.input.value); });
els.input.addEventListener("input", autoResize);
els.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); els.form.requestSubmit(); }
});
els.deleteButton.addEventListener("click", () => { els.deleteModal.hidden = false; els.cancelDelete.focus(); });
els.cancelDelete.addEventListener("click", () => { els.deleteModal.hidden = true; });
els.confirmDelete.addEventListener("click", deleteDocument);
els.deleteModal.addEventListener("click", (event) => { if (event.target === els.deleteModal) els.deleteModal.hidden = true; });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") els.deleteModal.hidden = true; });

async function initialize() {
  renderDocument();
  try {
    const [healthResponse, documentResponse] = await Promise.all([fetch("/api/health"), fetch("/api/document")]);
    const health = await healthResponse.json();
    if (!healthResponse.ok) throw new Error();
    els.serviceStatus.classList.add(health.openai_configured ? "online" : "error");
    els.serviceStatus.querySelector("span").textContent = health.openai_configured ? "OpenAI connected" : "API key required";
    if (documentResponse.ok) documentInfo = await documentResponse.json();
    renderDocument();
  } catch {
    els.serviceStatus.classList.add("error");
    els.serviceStatus.querySelector("span").textContent = "Service unavailable";
  }
}

initialize();

