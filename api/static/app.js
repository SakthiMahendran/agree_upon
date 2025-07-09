let token = "";
let convId = null;

// ── Auth UI Logic ──────────────────────────────────────────────────────
const overlay = document.getElementById("authOverlay");
const signupForm = document.getElementById("signupForm");
const loginForm  = document.getElementById("loginForm");
document.getElementById("showLogin").onclick = () => {
  signupForm.classList.add("hidden");
  loginForm.classList.remove("hidden");
};
document.getElementById("showSignup").onclick = () => {
  loginForm.classList.add("hidden");
  signupForm.classList.remove("hidden");
};

async function api(path, method="GET", body=null) {
  const opts = { method, headers:{} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (token) opts.headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`Error ${res.status}: ${await res.text()}`);
  return res.json();
}

signupForm.onsubmit = async e => {
  e.preventDefault();
  const u = document.getElementById("signupUsername").value;
  const em= document.getElementById("signupEmail").value;
  const p = document.getElementById("signupPassword").value;
  await api("/auth/register","POST",{ username:u, email:em, password:p });
  alert("Signup successful—please log in.");
  showLogin.click();
};

loginForm.onsubmit = async e => {
  e.preventDefault();
  const u = document.getElementById("loginUsername").value;
  const p = document.getElementById("loginPassword").value;
  const form = new URLSearchParams();
  form.append("username", u);
  form.append("password", p);
  const res = await fetch("/auth/token", { method:"POST", body: form });
  const data = await res.json();
  token = data.access_token;
  overlay.classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  await loadConvs();
};

// ── Conversations & Chat Logic ─────────────────────────────────────────
const convList = document.getElementById("convList");
const btnNew   = document.getElementById("btnNew");
const messages = document.getElementById("messages");
const input    = document.getElementById("input");
const btnSend  = document.getElementById("btnSend");
const docPane  = document.getElementById("documentContent");

btnNew.onclick = async () => {
  const conv = await api("/conversations","POST",{});
  convId = conv.id;
  highlightConv();
  clearChat();
  await loadConvs();
};

async function loadConvs() {
  const list = await api("/conversations");
  convList.innerHTML = "";
  list.forEach(c => {
    const li = document.createElement("li");
    li.textContent = `#${c.id} — ${c.title || "Untitled"}`;
    li.onclick = () => {
      convId = c.id;
      highlightConv();
      clearChat();
    };
    if (c.id === convId) li.classList.add("active");
    convList.appendChild(li);
  });
}

function highlightConv() {
  [...convList.children].forEach(li => li.classList.toggle("active", li.textContent.startsWith(`#${convId}`)));
}

function clearChat() {
  messages.innerHTML = "";
  docPane.textContent = "No document generated yet.";
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || !convId) return;
  // show user
  const uDiv = document.createElement("div");
  uDiv.className = "message user";
  uDiv.textContent = text;
  messages.appendChild(uDiv);
  input.value = "";

  // send
  const reply = await api(`/agent/${convId}/message`,"POST",{ content:text });
  const aDiv = document.createElement("div");
  aDiv.className = "message assistant";
  aDiv.textContent = reply.content;
  messages.appendChild(aDiv);

  // update doc pane
  docPane.textContent = reply.content;
}

btnSend.onclick = sendMessage;
input.addEventListener("keypress", e => {
  if (e.key === "Enter") sendMessage();
});
