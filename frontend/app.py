from flask import Flask, render_template, request, redirect, url_for
from utils import *

app = Flask(__name__)

@app.route("/")
def index():
    projects = get_projects()
    return render_template("index.html", projects=projects)

@app.route("/new-project", methods=["GET", "POST"])
def new_project():
    if request.method == "POST":
        name = request.form["name"]
        desc = request.form.get("description", "")
        create_project(name, desc)
        return redirect(url_for("index"))
    return render_template("new_project.html")

@app.route("/project/<project_id>", methods=["GET", "POST"])
def view_project(project_id):
    if request.method == "POST":
        docs = request.files.getlist("documents")
        files = [("files", (d.filename, d.stream, d.mimetype)) for d in docs]
        upload_documents(project_id, files)
    chats = get_project_chats(project_id)
    return render_template("project.html", project_id=project_id, chats=chats)

@app.route("/new-chat/<project_id>", methods=["GET", "POST"])
def new_chat(project_id):
    if request.method == "POST":
        title = request.form["title"]
        draft = request.files.get("draft")
        create_chat(project_id, title, draft)
        return redirect(url_for("view_project", project_id=project_id))
    return render_template("new_chat.html", project_id=project_id)

@app.route("/project/<project_id>/chat/<chat_id>")
def view_chat(project_id, chat_id):
    messages = get_conversation(chat_id)
    checkpoints = get_checkpoints(chat_id)
    return render_template("chat.html", project_id=project_id, chat_id=chat_id, messages=messages, checkpoints=checkpoints)

@app.route("/checkpoint/<checkpoint_id>/respond", methods=["POST"])
def respond_cp(checkpoint_id):
    approved = request.form["approved"] == "yes"
    feedback = request.form.get("response", "")
    respond_checkpoint(checkpoint_id, approved, feedback)
    return redirect(request.referrer)


@app.route("/project/<project_id>/chat/<chat_id>/download")
def download_markdown(project_id, chat_id):
    import requests
    from flask import Response
    url = f"http://127.0.0.1:8000/chats/{chat_id}/output"
    resp = requests.get(url)
    if resp.status_code == 200:
        return Response(
            resp.text,
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment;filename={chat_id}.md"}
        )
    return f"No output yet for chat {chat_id}", 404

if __name__ == "__main__":
    app.run(debug=True)