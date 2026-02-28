from flask import Flask, render_template, request, redirect, session, flash
import subprocess
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this")

USERNAME = os.environ.get("GUI_USERNAME", "admin")
PASSWORD = os.environ.get("GUI_PASSWORD", "changeme")

VIRTUAL_FILE = "/var/lib/postfix-gui/virtual"
WRAPPER_SCRIPT = "/usr/local/bin/update-postfix-virtual.sh"


# ---------- Utilities ----------

def load_aliases():
    aliases = []

    if not os.path.exists(VIRTUAL_FILE):
        return aliases

    with open(VIRTUAL_FILE, "r") as f:
        for line in f:
            line = line.strip()

            # Skip blanks and comments
            if not line or line.startswith("#"):
                continue

            parts = line.split(None, 1)
            if len(parts) == 2:
                alias = parts[0].strip()
                recipients = parts[1].strip()
                aliases.append((alias, recipients))

    return aliases


def save_virtual_file(lines):
    temp_file = "/tmp/postfix_virtual.tmp"

    with open(temp_file, "w") as f:
        f.writelines(lines)

    subprocess.run(["sudo", WRAPPER_SCRIPT], check=True)


# ---------- Routes ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form.get("username") == USERNAME and
            request.form.get("password") == PASSWORD
        ):
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
        alias = request.form.get("alias", "").strip()
        recipients = request.form.get("recipients", "").strip()

        if not alias or not recipients:
            flash("Alias and recipients are required.")
            return redirect("/")

        lines = []
        if os.path.exists(VIRTUAL_FILE):
            with open(VIRTUAL_FILE, "r") as f:
                lines = f.readlines()

        updated = False
        new_lines = []

        for line in lines:
            existing = line.strip()

            if not existing or existing.startswith("#"):
                new_lines.append(line)
                continue

            parts = existing.split(None, 1)
            if len(parts) == 2 and parts[0] == alias:
                new_lines.append(f"{alias}    {recipients}\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.append(f"{alias}    {recipients}\n")

        try:
            save_virtual_file(new_lines)
            flash("Alias saved successfully.")
        except subprocess.CalledProcessError:
            flash("Error updating postfix. Check server logs.")

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

    new_lines = []

    for line in lines:
        existing = line.strip()

        if not existing or existing.startswith("#"):
            new_lines.append(line)
            continue

        parts = existing.split(None, 1)
        if len(parts) == 2 and parts[0] == alias:
            continue  # skip this alias (delete)
        else:
            new_lines.append(line)

    try:
        save_virtual_file(new_lines)
        flash("Alias deleted.")
    except subprocess.CalledProcessError:
        flash("Error deleting alias. Check logs.")

    return redirect("/")


if __name__ == "__main__":
    app.run()