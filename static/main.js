// main.js
let token = null;
let conversationId = null;

async function register(username, password) {
    const res = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
}

async function login(username, password) {
    const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    token = data.access_token;
    return data;
}

async function startConversation() {
    const res = await fetch('/conversations/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: '{}' // empty body
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    conversationId = data.id;
    return data;
}

async function sendMessage(content) {
    const res = await fetch(`/agent/${conversationId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({ content })
    });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
}

// --- UI State ---
let conversations = [];
let selectedConvo = null;

// --- DOM Elements ---
const authSection = document.getElementById('auth-section');
const mainApp = document.getElementById('main-app');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const toRegisterBtn = document.getElementById('to-register');
const toLoginBtn = document.getElementById('to-login');
const convoList = document.getElementById('convo-list');
const newConvoBtn = document.getElementById('new-convo-btn');
const deleteConvoBtn = document.getElementById('delete-convo-btn');
const chatSection = document.getElementById('chat-section');
const chat = document.getElementById('chat');
const inputRow = document.getElementById('input-row');
const userInput = document.getElementById('user-input');
const documentContent = document.getElementById('document-content');

// --- Auth Switching ---
toRegisterBtn.onclick = () => {
  loginForm.style.display = 'none';
  registerForm.style.display = 'flex';
  document.getElementById('auth-title').textContent = 'Register';
};
toLoginBtn.onclick = () => {
  loginForm.style.display = 'flex';
  registerForm.style.display = 'none';
  document.getElementById('auth-title').textContent = 'Login';
};

// --- Auth Flows ---
loginForm.onsubmit = async e => {
  e.preventDefault();
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  try {
    await login(username, password);
    await loadConversations();
    authSection.style.display = 'none';
    mainApp.style.display = 'flex';
    if (conversations.length) {
      selectConversation(conversations[0].id);
    } else {
      await createConversation();
    }
  } catch (err) {
    alert('Login failed: ' + err.message);
  }
};
registerForm.onsubmit = async e => {
  e.preventDefault();
  const username = document.getElementById('register-username').value;
  const password = document.getElementById('register-password').value;
  try {
    await register(username, password);
    alert('Registration successful. Please log in.');
    toLoginBtn.click();
  } catch (err) {
    alert('Registration failed: ' + err.message);
  }
};

// --- Conversation Management ---
async function loadConversations() {
  const res = await fetch('/conversations/', {
    headers: { 'Authorization': 'Bearer ' + token }
  });
  if (!res.ok) throw new Error(await res.text());
  conversations = await res.json();
  renderConvoList();
}

function renderConvoList() {
  convoList.innerHTML = '';
  if (!conversations.length) {
    const div = document.createElement('div');
    div.textContent = 'No conversations.';
    div.style.padding = '16px';
    convoList.appendChild(div);
    deleteConvoBtn.disabled = true;
    return;
  }
  conversations.forEach(convo => {
    const btn = document.createElement('button');
    btn.className = 'convo-item' + (selectedConvo && convo.id === selectedConvo.id ? ' selected' : '');
    btn.textContent = `#${convo.id} (${new Date(convo.created_at).toLocaleString()})`;
    btn.onclick = () => selectConversation(convo.id);
    convoList.appendChild(btn);
  });
  deleteConvoBtn.disabled = !selectedConvo;
}

async function createConversation() {
  const res = await fetch('/conversations/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
    body: '{}'
  });
  if (!res.ok) throw new Error(await res.text());
  const convo = await res.json();
  conversations.unshift(convo);
  renderConvoList();
  selectConversation(convo.id);
}

async function deleteConversation() {
  if (!selectedConvo) return;
  const res = await fetch(`/conversations/${selectedConvo.id}`, {
    method: 'DELETE',
    headers: { 'Authorization': 'Bearer ' + token }
  });
  if (!res.ok) { alert('Delete failed'); return; }
  conversations = conversations.filter(c => c.id !== selectedConvo.id);
  selectedConvo = null;
  renderConvoList();
  chat.innerHTML = '';
  documentContent.textContent = 'No document yet.';
  deleteConvoBtn.disabled = true;
  if (conversations.length) selectConversation(conversations[0].id);
}

newConvoBtn.onclick = createConversation;
deleteConvoBtn.onclick = deleteConversation;

async function selectConversation(id) {
  selectedConvo = conversations.find(c => c.id === id);
  renderConvoList();
  chat.innerHTML = '';
  documentContent.textContent = 'Loading...';
  // Load messages
  const res = await fetch(`/conversations/${id}`, {
    headers: { 'Authorization': 'Bearer ' + token }
  });
  if (!res.ok) { chat.innerHTML = '<div>Error loading conversation.</div>'; return; }
  const convo = await res.json();
  if (convo.messages && convo.messages.length) {
    convo.messages.forEach(m => {
      addMsg(m.sender, m.content);
    });
  } else {
    addMsg('agent', "Hi, I’m your Legal Assistant. I can help you draft documents like: NDA Agreement, Lease or Rental Agreement, Partnership Agreement, Shareholder Agreement. Or feel free to describe your legal needs.");
  }
  // Load document
  const docRes = await fetch(`/documents/${id}`, {
    headers: { 'Authorization': 'Bearer ' + token }
  });
  if (docRes.ok) {
    const doc = await docRes.json();
    documentContent.textContent = doc.content;
  } else {
    documentContent.textContent = 'No document yet.';
  }
}

// --- Chat ---
function addMsg(role, content) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = content;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

inputRow.onsubmit = async e => {
  e.preventDefault();
  if (!selectedConvo) return;
  const msg = userInput.value;
  addMsg('user', msg);
  userInput.value = '';
  addMsg('agent', '...');
  try {
    const res = await fetch(`/agent/${selectedConvo.id}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ content: msg })
    });
    if (!res.ok) {
      chat.lastChild.textContent = 'Error: ' + (await res.text());
      return;
    }
    const data = await res.json();
    console.log("Backend response:", data);
    console.log("Setting agent bubble to:", data.assistant_reply);
    chat.lastChild.textContent = data.assistant_reply;
    // reload document after each agent reply
    const docRes = await fetch(`/documents/${selectedConvo.id}`, {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (docRes.ok) {
      const doc = await docRes.json();
      documentContent.textContent = doc.content;
    }
  } catch (err) {
    chat.lastChild.textContent = 'Error: ' + err.message;
  }
};
