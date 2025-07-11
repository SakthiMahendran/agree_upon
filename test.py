import requests
import time

BASE_URL = "http://127.0.0.1:8000"

# GLOBAL STATE
headers = {}
convo_id = None

def test_register_and_login():
    print("\n🔐 Testing Registration and Login")
    reg_data = {
        "username": "testuser",
        "password": "testpass"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    if res.status_code == 400:
        print("✅ Already registered, skipping register.")
    elif res.ok:
        print("✅ Registered new user.")
    else:
        print("❌ Register failed:", res.text)

    res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    assert res.ok, "❌ Login failed"
    token = res.json()["access_token"]
    global headers
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Logged in and got token")

def test_create_conversation():
    print("\n💬 Testing Conversation Creation")
    res = requests.post(f"{BASE_URL}/conversations/", json={}, headers=headers)
    assert res.ok, "❌ Failed to create conversation"
    global convo_id
    convo_id = res.json()["id"]
    print(f"✅ Created conversation with ID {convo_id}")

def test_get_conversation():
    print("\n📋 Testing Fetch Conversation")
    res = requests.get(f"{BASE_URL}/conversations/{convo_id}", headers=headers)
    assert res.ok, "❌ Failed to get conversation"
    print("✅ Retrieved conversation with messages")

def test_agent_flow():
    print("\n🤖 Testing Agent Interaction")

    # Step 1 - Send a name
    res = requests.post(f"{BASE_URL}/agent/{convo_id}/message", json={"content": "Kiran Parthiban"}, headers=headers)
    assert res.ok, "❌ Agent message failed (1)"
    print("✅ Sent user message (1):", res.json()["content"])

    time.sleep(1)

    # Step 2 - Send an address
    res = requests.post(f"{BASE_URL}/agent/{convo_id}/message", json={"content": "123 Main Street, Toronto"}, headers=headers)
    assert res.ok, "❌ Agent message failed (2)"
    print("✅ Sent user message (2):", res.json()["content"])

    # Step 3 - Continue sending dummy fields to complete generation
    fields = ["test@example.com", "1234567890", "2025-07-09"]
    for i, field in enumerate(fields, start=3):
        res = requests.post(f"{BASE_URL}/agent/{convo_id}/message", json={"content": field}, headers=headers)
        assert res.ok, f"❌ Agent message failed ({i})"
        print(f"✅ Sent user message ({i}):", res.json()["content"])

def test_document_view_and_edit():
    print("\n📄 Testing Document View and Edit")
    res = requests.get(f"{BASE_URL}/documents/{convo_id}", headers=headers)
    assert res.ok, "❌ Failed to get document"
    print("✅ Document content retrieved")

    res = requests.post(f"{BASE_URL}/documents/{convo_id}/edit", json={"instruction": "Add confidentiality clause"}, headers=headers)
    assert res.ok, "❌ Document refinement failed"
    print("✅ Document refined")

def test_list_conversations():
    print("\n📚 Testing List Conversations")
    res = requests.get(f"{BASE_URL}/conversations/", headers=headers)
    assert res.ok, "❌ Failed to list conversations"
    print("✅ Listed conversations:", [c['id'] for c in res.json()])

def test_delete_conversation():
    print("\n🗑️ Testing Delete Conversation")
    res = requests.delete(f"{BASE_URL}/conversations/{convo_id}", headers=headers)
    assert res.ok, "❌ Failed to delete conversation"
    print("✅ Conversation deleted")

if __name__ == "__main__":
    test_register_and_login()
    test_create_conversation()
    test_get_conversation()
    test_agent_flow()
    test_document_view_and_edit()
    test_list_conversations()
    test_delete_conversation()
