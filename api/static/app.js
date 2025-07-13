const baseURL = "http://localhost:8000"; // Adjust as needed
let currentConvId = null;
let lastSendTime = 0;

const $ = sel => document.querySelector(sel);

//
// ─── Initial Load ────────────────────────────────────────────────
//
window.onload = () => {
  $("#app").classList.remove("hidden");
  loadConversations();
};

//
// ─── Conversations ────────────────────────────────────────────────
//
async function loadConversations() {
  const res = await fetch(`${baseURL}/conversations`);
  const conversations = await res.json();
  const list = $("#convList");
  list.innerHTML = "";
  conversations.forEach(conv => {
    const li = document.createElement("li");
    li.textContent = conv.title || `Conversation #${conv.id}`;
    li.onclick = () => openConv(conv.id, li);
    list.appendChild(li);
  });
}

$("#btnNew").onclick = async () => {
  const res = await fetch(`${baseURL}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}"
  });
  const conv = await res.json();
  await loadConversations();
  openConv(conv.id);
};

async function openConv(id, liNode) {
  currentConvId = id;
  $("#messages").innerHTML = "";
  $("#documentContent").textContent = "No document generated yet.";
  document.querySelectorAll("#convList li").forEach(li => li.classList.remove("active"));
  if (liNode) liNode.classList.add("active");

  const res = await fetch(`${baseURL}/conversations/${id}/messages`);
  const history = await res.json();
  history.forEach(m => addMessageToUI(m.sender, m.content));

  // Load associated document
  loadDocument(id);
}

//
// ─── Messaging ───────────────────────────────────────────────────
//
$("#btnSend").onclick = sendMessage;
$("#input").addEventListener("keydown", e => {
  if (e.key === "Enter") sendMessage();
});

async function sendMessage() {
  const text = $("#input").value.trim();
  if (!text || !currentConvId) return;

  $("#input").value = "";
  addMessageToUI("user", text);

  lastSendTime = performance.now();

  const res = await fetch(`${baseURL}/agent/${currentConvId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: text })
  });
  const data = await res.json();
  const deltaMs = Math.round(performance.now() - lastSendTime);

  addMessageToUI("assistant", data.assistant_reply, deltaMs);

  if (data.document) {
    $("#documentContent").textContent = data.document;
  } else {
    loadDocument(currentConvId);
  }
}

//
// ─── Document Loading ─────────────────────────────────────────────
//
async function loadDocument(conversationId) {
  const res = await fetch(`${baseURL}/documents/${conversationId}`);
  if (res.ok) {
    const doc = await res.json();
    $("#documentContent").textContent = doc.content;
  } else {
    $("#documentContent").textContent = "No document generated yet.";
  }
}

//
// ─── UI Helpers ───────────────────────────────────────────────────
//
function addMessageToUI(sender, text, deltaMs) {
  if (text === "") text = "(no reply)";

  const div = document.createElement("div");
  div.className = `message ${sender}`;
  div.textContent = text;

  if (sender === "assistant" && typeof deltaMs === "number") {
    const span = document.createElement("span");
    span.className = "response-time";
    span.textContent = ` (${deltaMs} ms)`;
    div.appendChild(span);
  }

  $("#messages").appendChild(div);
  $("#messages").scrollTop = $("#messages").scrollHeight;
}
