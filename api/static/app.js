// app.js

const baseURL = "http://localhost:8000";   // ← adjust if needed
let jwtToken    = null;
let currentConvId = null;
let lastSendTime  = 0;  // timestamp just before sending

const $ = sel => document.querySelector(sel);

//
// ─── Auth handlers ───────────────────────────────────────────────
//
$("#showLogin").onclick  = e => {
  e.preventDefault();
  $("#signupForm").classList.add("hidden");
  $("#loginForm").classList.remove("hidden");
};
$("#showSignup").onclick = e => {
  e.preventDefault();
  $("#loginForm").classList.add("hidden");
  $("#signupForm").classList.remove("hidden");
};

$("#signupForm").onsubmit = async e => {
  e.preventDefault();
  const body = {
    username: $("#signupUsername").value,
    email:    $("#signupEmail").value,
    password: $("#signupPassword").value
  };
  await fetch(`${baseURL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  alert("Signup success! Now log in.");
};

$("#loginForm").onsubmit = async e => {
  e.preventDefault();
  const body = {
    username: $("#loginUsername").value,
    password: $("#loginPassword").value
  };
  const res = await fetch(`${baseURL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  jwtToken = data.access_token;
  $("#authOverlay").classList.add("hidden");
  $("#app").classList.remove("hidden");
  loadConversations();
};

//
// ─── Conversations ────────────────────────────────────────────────
//
async function loadConversations(){
  const res  = await apiGET("/conversations");
  const list = $("#convList");
  list.innerHTML = "";
  res.forEach(conv => {
    const li = document.createElement("li");
    li.textContent = conv.title || `Conversation #${conv.id}`;
    li.onclick = () => openConv(conv.id, li);
    list.appendChild(li);
  });
}

$("#btnNew").onclick = async () => {
  const conv = await apiPOST("/conversations", {});
  loadConversations();
  openConv(conv.id);
};

async function openConv(id, liNode){
  currentConvId = id;
  $("#messages").innerHTML = "";
  $("#documentContent").textContent = "No document generated yet.";
  document.querySelectorAll("#convList li").forEach(li=>li.classList.remove("active"));
  if(liNode) liNode.classList.add("active");
  const history = await apiGET(`/conversations/${id}/messages`);
  history.forEach(m => addMessageToUI(m.sender, m.content));
}

//
// ─── Messaging ───────────────────────────────────────────────────
//
$("#btnSend").onclick = sendMessage;
$("#input").addEventListener("keydown", e => {
  if(e.key === "Enter") sendMessage();
});

async function sendMessage(){
  const text = $("#input").value.trim();
  if(!text || !currentConvId) return;
  $("#input").value = "";
  addMessageToUI("user", text);

  // record send time
  lastSendTime = performance.now();

  // fire the POST
  const res = await apiPOST(`/agent/${currentConvId}/message`, { content: text });

  // compute round-trip
  const deltaMs = Math.round(performance.now() - lastSendTime);

  addMessageToUI("assistant", res.assistant_reply, deltaMs);

  if(res.document){
    $("#documentContent").textContent = res.document;
  }
}

//
// ─── Helpers & API ────────────────────────────────────────────────
//
function addMessageToUI(sender, text, deltaMs) {
  // for blank replies
  if(text === "") text = "(no reply)";

  const div = document.createElement("div");
  div.className = `message ${sender}`;
  div.textContent = text;

  // if this is assistant, append the time taken
  if(sender === "assistant" && typeof deltaMs === "number") {
    const span = document.createElement("span");
    span.className = "response-time";
    span.textContent = `(${deltaMs} ms)`;
    div.appendChild(span);
  }

  $("#messages").appendChild(div);
  $("#messages").scrollTop = $("#messages").scrollHeight;
}

async function apiGET(path) {
  const res = await fetch(baseURL + path, {
    headers: { Authorization: `Bearer ${jwtToken}` }
  });
  return res.json();
}

async function apiPOST(path, body) {
  const res = await fetch(baseURL + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${jwtToken}`
    },
    body: JSON.stringify(body)
  });
  return res.json();
}
