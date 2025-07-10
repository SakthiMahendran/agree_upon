let token = "";
let convId = null;

// ── Auth UI Logic ──────────────────────────────────────────────────────
const overlay = document.getElementById("authOverlay");
const signupForm = document.getElementById("signupForm");
const loginForm = document.getElementById("loginForm");

document.getElementById("showLogin").onclick = () => {
  signupForm.classList.add("hidden");
  loginForm.classList.remove("hidden");
};

document.getElementById("showSignup").onclick = () => {
  loginForm.classList.add("hidden");
  signupForm.classList.remove("hidden");
};

async function api(path, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (token) {
    opts.headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    throw new Error(`Error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

signupForm.onsubmit = async (e) => {
  e.preventDefault();
  const u = document.getElementById("signupUsername").value;
  const em = document.getElementById("signupEmail").value;
  const p = document.getElementById("signupPassword").value;
  try {
    await api("/auth/register/", "POST", { username: u, email: em, password: p });
    alert("Signup successful—please log in.");
    document.getElementById("showLogin").click();
  } catch (err) {
    alert(`Signup error: ${err.message}`);
  }
};

loginForm.onsubmit = async (e) => {
  e.preventDefault();
  const em = document.getElementById("loginUsername").value;
  const p = document.getElementById("loginPassword").value;
  try {
    const res = await api("/auth/login/", "POST", { email: em, password: p });
    token = res.access_token;
    overlay.classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    await loadConvs();
  } catch (err) {
    alert(`Login failed: ${err.message}`);
  }
};

// ── Conversations & Chat Logic ─────────────────────────────────────────
const convList = document.getElementById("convList");
const btnNew = document.getElementById("btnNew");
const messages = document.getElementById("messages");
const input = document.getElementById("input");
const btnSend = document.getElementById("btnSend");
const docPane = document.getElementById("documentContent");

btnNew.onclick = async () => {
  try {
    const conv = await api("/conversations/", "POST", {});
    convId = conv.id;
    highlightConv();
    clearChat();
    await loadConvs();
  } catch (err) {
    alert(`Create conversation error: ${err.message}`);
  }
};

async function loadConvs() {
  try {
    const list = await api("/conversations/", "GET");
    convList.innerHTML = "";
    list.forEach((c) => {
      const li = document.createElement("li");
      li.textContent = `#${c.id} — ${c.title || "Untitled"}`;
      li.onclick = async () => {
        convId = c.id;
        highlightConv();
        clearChat();
        const res = await api(`/conversations/${convId}/`, "GET");
        res.messages.forEach((msg) => {
          const d = document.createElement("div");
          d.className = `message ${msg.sender}`;
          d.textContent = msg.content;
          messages.appendChild(d);
        });
      };
      if (c.id === convId) li.classList.add("active");
      convList.appendChild(li);
    });
  } catch (err) {
    alert(`Load conversations error: ${err.message}`);
  }
}

function highlightConv() {
  [...convList.children].forEach((li) =>
    li.classList.toggle("active", li.textContent.startsWith(`#${convId}`))
  );
}

function clearChat() {
  messages.innerHTML = "";
  docPane.textContent = "No document generated yet.";
}

async function sendMessage() {
  const text = input.value.trim();
  if (!text || !convId) return;

  // Append user message
  const uDiv = document.createElement("div");
  uDiv.className = "message user";
  uDiv.textContent = text;
  messages.appendChild(uDiv);
  input.value = "";

  // Placeholder for assistant message
  const aDiv = document.createElement("div");
  aDiv.className = "message assistant";
  aDiv.textContent = "";
  messages.appendChild(aDiv);

  try {
    // Send the message to trigger agent step (non-streaming call triggers server state)
    await api(`/agent/${convId}/message`, "POST", { content: text });

    // Open stream to get token-wise output
    const eventSource = new EventSource(`/agent/${convId}/stream`);

    let fullReply = "";

    eventSource.onmessage = (event) => {
      fullReply += event.data;
      aDiv.textContent = fullReply;
      docPane.textContent = fullReply;
      messages.scrollTop = messages.scrollHeight;
    };

    eventSource.addEventListener("done", () => {
      eventSource.close();
    });

    eventSource.onerror = (err) => {
      console.error("Streaming error:", err);
      eventSource.close();
    };
  } catch (err) {
    alert(`Send error: ${err.message}`);
  }
}

btnSend.onclick = sendMessage;
input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendMessage();
});
