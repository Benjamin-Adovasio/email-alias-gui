from flask import Flask, render_template, request, redirect, session, flash
import subprocess
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this")

USERNAME = os.environ.get("GUI_USERNAME", "admin")
PASSWORD = os.environ.get("GUI_PASSWORD", "changeme")

VIRTUAL_FILE = "/etc/postfix/virtual"

def reload_postfix():
    subprocess.run(["/usr/sbin/postmap", VIRTUAL_FILE])
    subprocess.run(["/bin/systemctl", "reload", "postfix"])

def load_aliases():
    aliases = []
    if os.path.exists(VIRTUAL_FILE):
        with open(VIRTUAL_FILE, "r") as f:
            for line in f:
                if line.strip():
                    alias, recipients = line.split(None, 1)
                    aliases.append((alias.strip(), recipients.strip()))
    return aliases

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect("/")
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/", methods=["GET", "POST"])
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")

    if request.method == "POST":
        alias = request.form["alias"].strip()
        recipients = request.form["recipients"].strip()

        lines = []
        if os.path.exists(VIRTUAL_FILE):
            with open(VIRTUAL_FILE, "r") as f:
                lines = f.readlines()

        updated = False
        new_lines = []

        for line in lines:
            if line.startswith(alias):
                new_lines.append(f"{alias}    {recipients}\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"{alias}    {recipients}\n")

        with open(VIRTUAL_FILE, "w") as f:
            f.writelines(new_lines)

        reload_postfix()
        flash("Alias saved successfully")
        return redirect("/")

    aliases = load_aliases()
    return render_template("dashboard.html", aliases=aliases)

@app.route("/delete/<alias>")
def delete(alias):
    if not session.get("logged_in"):
        return redirect("/login")

    lines = []
    if os.path.exists(VIRTUAL_FILE):
        with open(VIRTUAL_FILE, "r") as f:
            lines = f.readlines()

    new_lines = [line for line in lines if not line.startswith(alias)]

    with open(VIRTUAL_FILE, "w") as f:
        f.writelines(new_lines)

    reload_postfix()
    flash("Alias deleted")
    return redirect("/")

if __name__ == "__main__":
    app.run()