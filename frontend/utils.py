import requests
from config import BACKEND_URL

def get_projects():
    resp = requests.get(f"{BACKEND_URL}/projects")
    try:
        resp.raise_for_status()
        return resp.json()
    except Exception:
        print("❌ Failed to load projects:", resp.text)
        return []

def create_project(name, description):
    return requests.post(f"{BACKEND_URL}/projects", data={"name": name, "description": description}).json()

def upload_documents(project_id, files):
    return requests.post(f"{BACKEND_URL}/projects/{project_id}/documents", files=files).json()

def get_project_chats(project_id):
    return requests.get(f"{BACKEND_URL}/projects/{project_id}/chats").json()

def create_chat(project_id, title, draft):
    files = {"draft": draft} if draft else None
    data = {"title": title}
    return requests.post(f"{BACKEND_URL}/projects/{project_id}/chats", data=data, files=files).json()

def run_chat(chat_id):
    return requests.post(f"{BACKEND_URL}/projects/{chat_id}/run").json()

def get_conversation(chat_id):
    return requests.get(f"{BACKEND_URL}/chats/{chat_id}/conversation").json()

def get_checkpoints(chat_id):
    return requests.get(f"{BACKEND_URL}/checkpoints/{chat_id}/checkpoints").json()

def respond_checkpoint(checkpoint_id, approved, response):
    data = {"approved": approved, "response": response}
    return requests.post(f"{BACKEND_URL}/checkpoints/{checkpoint_id}/respond", json=data).json()