#!/usr/bin/env python3
"""
ZWANSKI Bug Bounty Platform Server
Serves the local dashboard UI and proxies OpenRouter AI.
"""
import json
import os
import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
import requests

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
CONFIG_FILE = ROOT / "config.json"
DEFAULT_API_URL = "https://api.openrouter.ai/api/v1/chat/completions"

ALLOWED_TOOLS = [
    "subfinder", "amass", "assetfinder", "dnsx", "puredns", "alterx", "chaos",
    "httpx", "katana", "hakrawler", "waybackurls", "gau", "gospider",
    "naabu", "nmap", "rustscan", "nuclei", "nikto", "ffuf", "feroxbuster",
    "gobuster", "dirsearch", "trufflehog", "gitleaks", "dalfox", "sqlmap",
    "arjun", "paramspider", "interactsh-client", "tlsx", "uncover", "zwanski-recon",
    "zwanski-oauth", "rchq", "shodan", "apktool", "jadx", "apkleaks", "frida",
    "objection", "s3scanner", "aws"
]

app = Flask(__name__, static_folder=str(UI_DIR))
CORS(app)


def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    config = {
        "openrouter_key": "",
        "api_url": DEFAULT_API_URL,
        "model": "anthropic/claude-3-haiku",
        "theme": "dark"
    }
    save_config(config)
    return config


def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def tool_installed(name):
    return shutil.which(name) is not None


def get_tools_status():
    tools = []
    for name in ALLOWED_TOOLS:
        tools.append({
            "name": name,
            "installed": tool_installed(name),
            "category": "misc",
            "description": ""
        })
    return tools


@app.route("/")
def index():
    if not (UI_DIR / "index.html").exists():
        return "Dashboard UI not found. Please run install.sh or git pull the repository.", 404
    return send_from_directory(str(UI_DIR), "index.html")


@app.route("/ui/<path:path>")
def ui_files(path):
    return send_from_directory(str(UI_DIR), path)


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def api_set_config():
    config = load_config()
    config.update(request.json or {})
    save_config(config)
    return jsonify({"ok": True, "config": config})


@app.route("/api/tools", methods=["GET"])
def api_tools():
    return jsonify(get_tools_status())


@app.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400

    body = request.get_json(silent=True) or {}
    messages = body.get("messages", [])
    model = body.get("model", config.get("model", "google/gemini-flash-1.5"))
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 600
    }

    try:
        r = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=45
        )
        r.raise_for_status()
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "message": content})
    except Exception as exc:
        return jsonify({"error": str(exc)})


@app.route("/api/ai/grade", methods=["POST"])
def api_ai_grade():
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400

    body = request.get_json(silent=True) or {}
    finding = body.get("finding", "").strip()
    if not finding:
        return jsonify({"error": "Provide a finding description to grade."}), 400

    prompt = (
        "You are a bug bounty grading assistant. Evaluate the following finding and return: "
        "1) severity (low/medium/high/critical), 2) impact summary, 3) suggested CVSS-like score, "
        "4) concise report headline. Output as a JSON object.\n\n"
        f"Finding:\n{finding}"
    )
    messages = [
        {"role": "system", "content": "You are a bug bounty assessment assistant."},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": config.get("model", "google/gemini-flash-1.5"),
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 300
    }
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL

    try:
        r = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=45
        )
        r.raise_for_status()
        data = r.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "grade": content})
    except Exception as exc:
        return jsonify({"error": str(exc)})


@app.route("/api/run", methods=["POST"])
def api_run():
    body = request.get_json(silent=True) or {}
    cmd = body.get("cmd", "").strip()
    if not cmd:
        return jsonify({"error": "No command provided."}), 400

    first = cmd.split()[0]
    if first not in ALLOWED_TOOLS:
        return jsonify({"error": f"Tool '{first}' is not allowed."}), 403

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return jsonify({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Command timed out."}), 408
    except Exception as exc:
        return jsonify({"error": str(exc)})


def open_browser(port):
    url = f"http://localhost:{port}"
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 1337))
    threading.Timer(1.2, lambda: open_browser(port)).start()
    print(f"Starting ZWANSKI dashboard on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
