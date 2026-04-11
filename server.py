#!/usr/bin/env python3
"""
ZWANSKI Bug Bounty Platform Server
Serves the local dashboard UI and proxies OpenRouter AI.
"""
import json
import os
import queue
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
import psutil

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
UI_DIR = ROOT / "ui"

from zwanski_kb import TargetKnowledgeBase
from shadow_client import shadow_request

WARMAP_STATE = {"hosts": [], "ports": [], "edges": [], "updated_at": None}
_NET_LAST = {"sent": None, "recv": None}

_URL_HOST_RE = re.compile(r"(?:https?://)([a-zA-Z0-9][-a-zA-Z0-9.]*[a-zA-Z0-9])", re.I)
_PORT_RE = re.compile(r":(\d{2,5})\b|port[:\s]+(\d{2,5})", re.I)
CONFIG_FILE = ROOT / "config.json"
DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.0-flash-001"
HTTP_REFERER = "https://zwanski.org"
OPENROUTER_HEADERS = {
    "Content-Type": "application/json",
    "Referer": HTTP_REFERER,
    "X-Title": "zwanski"
}

PROMPT_TEMPLATES = {
    "subdomain_analysis": {
        "title": "Subdomain Analysis",
        "description": "Identify high-value targets and exposed services from reconnaissance output.",
        "prompt": (
            "You are a bug bounty reconnaissance analyst. Review the following reconnaissance output and identify the most valuable subdomains, services, and likely attack surfaces. "
            "Highlight any high-risk hosts, exposed admin panels, cloud storage, or outdated technology. "
            "Provide concise recommendations for follow-up tests.\n\n" 
            "Recon output:\n{context}"
        )
    },
    "code_review": {
        "title": "Code Review",
        "description": "Scan JavaScript and source outputs for hidden endpoints and credentials.",
        "prompt": (
            "You are a security researcher analyzing front-end code. Review the following JavaScript and related outputs to find hidden endpoints, hardcoded keys, unusual API patterns, or logic that can be abused. "
            "Identify potential attack vectors, sensitive parameters, and payload ideas.\n\n"
            "Code context:\n{context}"
        )
    },
    "vulnerability_explanation": {
        "title": "Vulnerability Explanation",
        "description": "Explain complex attack chains and summarize impact for reporting.",
        "prompt": (
            "You are a bug bounty reporter. Read the following finding details and explain the vulnerability chain in a way that is easily understood by developers and security reviewers. "
            "Describe the root cause, exploitation path, and impact.\n\n"
            "Finding details:\n{context}"
        )
    },
    "xss_sqli_payload": {
        "title": "XSS/SQLi Payload Suggestion",
        "description": "Suggest next-step payloads and exploitation paths based on scan results.",
        "prompt": (
            "You are a penetration tester. Based on the following scan output, propose concrete XSS or SQL injection payloads and the best next steps for validation. "
            "Include one or two precise payload examples and a brief rationale.\n\n"
            "Scan output:\n{context}"
        )
    },
    "report_generation": {
        "title": "Automated Report Generation",
        "description": "Create a professional vulnerability report for HackerOne/Bugcrowd.",
        "prompt": (
            "You are a professional vulnerability report writer. Convert the following findings and scan output into a polished HackerOne/Bugcrowd report. "
            "Use markdown sections: Summary, Impact, Reproduction, Remediation, and Notes. Keep it concise but professional.\n\n"
            "Finding context:\n{context}"
        )
    }
}

ALLOWED_TOOLS = [
    "subfinder", "subdominator", "amass", "assetfinder", "dnsx", "puredns", "alterx", "chaos",
    "httpx", "katana", "hakrawler", "waybackurls", "gau", "gospider",
    "naabu", "nmap", "rustscan", "nuclei", "nikto", "ffuf", "feroxbuster",
    "gobuster", "dirsearch", "trufflehog", "gitleaks", "dalfox", "sqlmap",
    "arjun", "paramspider", "interactsh-client", "tlsx", "uncover", "zwanski-recon",
    "zwanski-oauth", "rchq", "shodan", "apktool", "jadx", "apkleaks", "frida",
    "objection", "s3scanner", "aws"
]

app = Flask(__name__, static_folder=str(UI_DIR))
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*")


def load_config():
    if CONFIG_FILE.exists():
        config_dict = json.loads(CONFIG_FILE.read_text())
    else:
        config_dict = {
            "openrouter_key": "",
            "api_url": DEFAULT_API_URL,
            "model": DEFAULT_MODEL,
            "theme": "dark",
            "ai_recon_enabled": True,
        }

    config_dict["openrouter_key"] = os.getenv(
        "OPENROUTER_API_KEY", config_dict.get("openrouter_key", "")
    )
    config_dict["api_url"] = os.getenv(
        "OPENROUTER_API_URL", config_dict.get("api_url", DEFAULT_API_URL)
    )
    config_dict["model"] = os.getenv(
        "OPENROUTER_MODEL", config_dict.get("model", DEFAULT_MODEL)
    )
    return config_dict



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


class Task:
    def __init__(self, cmd):
        self.id = uuid.uuid4().hex
        self.cmd = cmd
        self.status = "pending"
        self.stdout = ""
        self.stderr = ""
        self.returncode = None
        self.created_at = datetime.utcnow().isoformat() + "Z"
        self.updated_at = self.created_at
        self.logs = []
        self.proc = None

    def append_output(self, text, stream="stdout"):
        self.logs.append({"stream": stream, "text": text, "timestamp": datetime.utcnow().isoformat() + "Z"})
        if stream == "stdout":
            self.stdout += text
        else:
            self.stderr += text
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self, include_logs=False):
        data = {
            "id": self.id,
            "cmd": self.cmd,
            "status": self.status,
            "returncode": self.returncode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "summary": self.logs[-1]["text"] if self.logs else ""
        }
        if include_logs:
            data["logs"] = self.logs
        return data


class TaskManager:
    def __init__(self, persistence_file=None):
        self.tasks = {}
        self.queue = queue.Queue()
        self.persistence_file = persistence_file or (ROOT / "tasks.json")
        self._load_tasks()
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _load_tasks(self):
        if not self.persistence_file.exists():
            return
        try:
            raw = json.loads(self.persistence_file.read_text())
            for item in raw:
                task = Task(item["cmd"])
                task.id = item["id"]
                task.status = item["status"]
                if task.status == "running":
                    task.status = "stopped"
                task.stdout = item.get("stdout", "")
                task.stderr = item.get("stderr", "")
                task.returncode = item.get("returncode")
                task.created_at = item.get("created_at", task.created_at)
                task.updated_at = item.get("updated_at", task.updated_at)
                task.logs = item.get("logs", [])
                self.tasks[task.id] = task
        except Exception:
            pass

    def _save_tasks(self):
        try:
            self.persistence_file.write_text(json.dumps([task.to_dict(include_logs=True) for task in self.tasks.values()], indent=2))
        except Exception:
            pass

    def _worker_loop(self):
        while True:
            task = self.queue.get()
            self._execute_task(task)
            self.queue.task_done()

    def submit(self, cmd):
        task = Task(cmd)
        self.tasks[task.id] = task
        self._save_tasks()
        self._emit_task_update(task)
        self.queue.put(task)
        return task

    def _execute_task(self, task):
        task.status = "running"
        task.updated_at = datetime.utcnow().isoformat() + "Z"
        self._save_tasks()
        self._emit_task_update(task)
        try:
            proc = subprocess.Popen(
                task.cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(ROOT)
            )
            task.proc = proc

            def read_stream(stream, stream_name):
                for line in iter(stream.readline, ""):
                    if not line:
                        break
                    task.append_output(line, stream=stream_name)
                    self._emit_task_output(task, line, stream_name)
                    print(f"[task:{task.id}][{stream_name}] {line.rstrip()}", flush=True)
                stream.close()

            stdout_thread = threading.Thread(target=read_stream, args=(proc.stdout, "stdout"), daemon=True)
            stderr_thread = threading.Thread(target=read_stream, args=(proc.stderr, "stderr"), daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            proc.wait()
            stdout_thread.join()
            stderr_thread.join()
            task.returncode = proc.returncode
            task.status = "completed" if proc.returncode == 0 else "failed"
        except Exception as exc:
            task.append_output(str(exc) + "\n", stream="stderr")
            task.status = "failed"
            task.returncode = -1
        finally:
            task.updated_at = datetime.utcnow().isoformat() + "Z"
            self._save_tasks()
            self._emit_task_update(task)
            try:
                merge_warmap_from_text(task.stdout + "\n" + task.stderr, "")
            except Exception:
                pass

    def _emit_task_output(self, task, text, stream):
        socketio.emit(
            "terminal_output",
            {"task_id": task.id, "output": text, "stream": stream},
            broadcast=True
        )

    def _emit_task_update(self, task):
        socketio.emit("task_update", task.to_dict(include_logs=False), broadcast=True)

    def list_tasks(self):
        return [task.to_dict(include_logs=False) for task in sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)]

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def abort(self, task_id):
        task = self.get_task(task_id)
        if not task or not task.proc or task.proc.poll() is not None:
            return False
        try:
            task.proc.terminate()
            task.status = "cancelled"
            task.updated_at = datetime.utcnow().isoformat() + "Z"
            self._save_tasks()
            self._emit_task_update(task)
            return True
        except Exception:
            return False


task_manager = TaskManager()

# ======================
# WAR MAP (attack surface graph hints from recon stdout)
# ======================


def parse_recon_warmap(text: str, seed_domain: str = ""):
    hosts = set()
    if seed_domain:
        hosts.add(seed_domain.strip().lower().rstrip("."))
    for m in _URL_HOST_RE.finditer(text or ""):
        hosts.add(m.group(1).lower())
    ports = set()
    for m in _PORT_RE.finditer(text or ""):
        p = m.group(1) or m.group(2)
        if p:
            pi = int(p)
            if 1 <= pi <= 65535:
                ports.add(pi)
    hosts = {h for h in hosts if h and (("." in h) or h.replace("-", "").isalnum())}
    return {"hosts": sorted(hosts), "ports": sorted(ports)}


def hosts_to_edges(hosts):
    edges = []
    hset = set(hosts)
    for h in hosts:
        parts = h.split(".")
        if len(parts) >= 3:
            parent = ".".join(parts[1:])
            if parent in hset:
                edges.append({"from": parent, "to": h, "type": "subdomain"})
    return edges


def merge_warmap_from_text(text: str, seed_domain: str = ""):
    global WARMAP_STATE
    parsed = parse_recon_warmap(text, seed_domain)
    mh = set(WARMAP_STATE.get("hosts", [])) | set(parsed["hosts"])
    mp = set(WARMAP_STATE.get("ports", [])) | set(parsed["ports"])
    host_list = sorted(mh)
    WARMAP_STATE = {
        "hosts": host_list,
        "ports": sorted(mp),
        "edges": hosts_to_edges(host_list),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    socketio.emit("warmap_update", WARMAP_STATE, broadcast=True)


# ======================
# SYSTEM HEALTH MONITORING
# ======================

def get_system_health():
    """Get current CPU, RAM, and network stats."""
    global _NET_LAST
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    net_io = psutil.net_io_counters()
    sent_delta = recv_delta = 0
    if _NET_LAST["sent"] is not None:
        sent_delta = max(0, net_io.bytes_sent - _NET_LAST["sent"])
        recv_delta = max(0, net_io.bytes_recv - _NET_LAST["recv"])
    _NET_LAST["sent"] = net_io.bytes_sent
    _NET_LAST["recv"] = net_io.bytes_recv

    return {
        "cpu_percent": cpu_percent,
        "cpu_count": psutil.cpu_count(),
        "memory_total": memory.total,
        "memory_used": memory.used,
        "memory_percent": memory.percent,
        "network_bytes_sent": net_io.bytes_sent,
        "network_bytes_recv": net_io.bytes_recv,
        "network_sent_delta": sent_delta,
        "network_recv_delta": recv_delta,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_process_list():
    """Get list of running recon processes."""
    processes = []
    for task in task_manager.tasks.values():
        if task.status == "running" and task.proc:
            try:
                proc_info = psutil.Process(task.proc.pid)
                processes.append({
                    "pid": task.proc.pid,
                    "tool_name": task.cmd.split()[0] if task.cmd else "unknown",
                    "command": task.cmd,
                    "uptime": task.updated_at,
                    "cpu_percent": proc_info.cpu_percent(interval=0.1),
                    "memory_mb": proc_info.memory_info().rss / 1024 / 1024,
                    "status": task.status
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    return processes


# Background system monitoring thread
def system_monitor_loop():
    """Emit system health updates every 2 seconds."""
    while True:
        try:
            health = get_system_health()
            processes = get_process_list()
            socketio.emit("system_health", health)
            socketio.emit("process_update", {"processes": processes})
        except Exception as e:
            print(f"System monitor error: {e}")
        time.sleep(2)


# Start system monitor
monitor_thread = threading.Thread(target=system_monitor_loop, daemon=True)
monitor_thread.start()


# ======================
# AGENTIC RECON PIPELINE
# ======================

class AgentPipeline:
    """Multi-phase recon: CrawlAI-RAG → Subdominator/ProjectDiscovery → httpx/probe → NeuroSploit/nuclei."""

    def __init__(self, target_domain):
        self.target_domain = target_domain.strip()
        self.phase = "idle"
        self.results = {
            "intelligence": [],
            "subdomains": [],
            "endpoints": [],
            "vulnerabilities": [],
            "exploit_chains": [],
            "logs": [],
        }
        self.kb = TargetKnowledgeBase(ROOT, self.target_domain)
        self.subs_file = ROOT / "data" / "tmp" / f"subs_{self.target_domain.replace('.', '_')}.txt"
        self.subs_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message):
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.results["logs"].append(entry)
        print(f"[AgentPipeline] {entry}", flush=True)
        socketio.emit("agent_log", {"message": entry, "phase": self.phase}, broadcast=True)

    def _run_shell(self, cmd: str, timeout: int = 900) -> tuple[str, str, int]:
        self.log(cmd[:500])
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(ROOT),
            )
            return proc.stdout or "", proc.stderr or "", proc.returncode
        except subprocess.TimeoutExpired:
            return "", "timeout", -1
        except Exception as exc:
            return "", str(exc), -1

    def _ghost_pause(self):
        time.sleep(random.uniform(0.4, 2.2))

    def run_intelligence_phase(self):
        self.phase = "intelligence"
        self.log(f"INTELLIGENCE: target={self.target_domain}")
        self._ghost_pause()
        if shutil.which("crawlai-rag"):
            out, err, code = self._run_shell(
                f'crawlai-rag --target "{self.target_domain}" --output "{self.subs_file}.crawl.json" 2>&1',
                timeout=1200,
            )
            blob = out + err
            self.kb.append(blob[:200_000], "crawlai-rag")
            self.results["intelligence"].append(blob[:8000])
        else:
            url = f"https://{self.target_domain}"
            try:
                if os.environ.get("SHADOW_MODE", "").lower() in ("1", "true", "yes", "on"):
                    self._ghost_pause()
                    r = shadow_request("GET", url, timeout=45, allow_redirects=True)
                    probe = f"{r.status_code}\n{r.text[:8000]}"
                else:
                    r = requests.get(url, timeout=45, allow_redirects=True)
                    probe = f"{r.status_code}\n{r.text[:8000]}"
                self.kb.append(probe, "shadow_probe" if os.environ.get("SHADOW_MODE") else "httpx_fallback_probe")
                self.results["intelligence"].append(probe[:4000])
            except Exception as exc:
                self.results["intelligence"].append(f"probe_failed: {exc}")
        self.log("INTELLIGENCE: phase complete")
        return self.results["intelligence"]

    def run_recon_phase(self):
        self.phase = "recon"
        self.log("RECON: subdomain enumeration (Subdominator / subfinder → dnsx)")
        self._ghost_pause()
        out_parts = []
        if shutil.which("subdominator"):
            o, e, _ = self._run_shell(
                f'subdominator -d "{self.target_domain}" -s -o "{self.subs_file}" 2>&1',
            )
            blob = o + e
            out_parts.append(blob)
            self.kb.append(blob[:150_000], "subdominator")
        elif shutil.which("subfinder"):
            o, e, _ = self._run_shell(
                f'subfinder -d "{self.target_domain}" -silent -o "{self.subs_file}" 2>&1',
            )
            blob = o + e
            out_parts.append(blob)
            self.kb.append(blob[:150_000], "subfinder")
        else:
            self.log("RECON: no subdominator/subfinder in PATH — skipping file enum")
        if self.subs_file.exists():
            merge_warmap_from_text(self.subs_file.read_text(errors="replace"), self.target_domain)
        if shutil.which("dnsx") and self.subs_file.exists():
            o, e, _ = self._run_shell(
                f'dnsx -l "{self.subs_file}" -silent -a -resp 2>&1',
                timeout=600,
            )
            out_parts.append(o + e)
            self.kb.append((o + e)[:80_000], "dnsx")
        self.results["subdomains"] = out_parts
        self.log("RECON: phase complete")
        return self.results["subdomains"]

    def run_attack_phase(self):
        self.phase = "attack"
        self.log("ATTACK: live hosts + vuln scan (httpx → nuclei / neurosploit)")
        self._ghost_pause()
        lines = []
        if shutil.which("httpx"):
            if self.subs_file.exists():
                o, e, _ = self._run_shell(
                    f'httpx -l "{self.subs_file}" -silent -sc -title -tech-detect -timeout 30 2>&1',
                    timeout=1200,
                )
            else:
                o, e, _ = self._run_shell(
                    f'httpx -u "https://{self.target_domain}" -silent -sc -title -tech-detect 2>&1',
                    timeout=600,
                )
            blob = o + e
            lines.append(blob)
            self.kb.append(blob[:200_000], "httpx")
            merge_warmap_from_text(blob, self.target_domain)
        if shutil.which("neurosploit"):
            o, e, _ = self._run_shell(
                f'neurosploit --target "https://{self.target_domain}" 2>&1',
                timeout=900,
            )
            blob = o + e
            lines.append(blob)
            self.kb.append(blob[:120_000], "neurosploit")
        if shutil.which("nuclei"):
            o, e, _ = self._run_shell(
                f'nuclei -u "https://{self.target_domain}" -silent -nc 2>&1',
                timeout=900,
            )
            lines.append(o + e)
            self.kb.append((o + e)[:200_000], "nuclei")
        self.results["endpoints"] = lines[:3]
        self.results["vulnerabilities"] = lines
        self.log("ATTACK: phase complete")
        return self.results["vulnerabilities"]

    def run_full_pipeline(self):
        self.log(f"PIPELINE start: {self.target_domain}")
        try:
            self.run_intelligence_phase()
            self.run_recon_phase()
            self.run_attack_phase()
            self._suggest_chains_from_kb()
        finally:
            self.phase = "complete"
            self.log("PIPELINE: complete")
        return self.results

    def _suggest_chains_from_kb(self):
        ctx = self.kb.query("redirect open API admin upload oauth graphql websocket ssrf xss sqli")
        if not ctx.strip():
            return
        vuln_snip = "\n".join(self.results.get("vulnerabilities", []))[:6000]
        config = load_config()
        key = config.get("openrouter_key", "")
        if not key:
            self.results["exploit_chains"].append("Set OPENROUTER_API_KEY for exploit-chain suggestions.")
            return
        prompt = (
            "You are an offensive security advisor. Given recon text, suggest 2–4 concise exploit CHAINS "
            "(e.g. Open Redirect → SSRF via a specific path hypothesis). "
            "Focus on business-logic and chaining, not generic CVEs. Output markdown bullets.\n\n"
            f"=== Knowledge snippets ===\n{ctx[:7000]}\n\n=== Scan lines ===\n{vuln_snip}"
        )
        try:
            api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL
            payload = {
                "model": config.get("model", DEFAULT_MODEL),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.15,
                "max_tokens": 900,
            }
            data = call_openrouter_api(api_url, key, payload)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self.results["exploit_chains"].append(content)
            socketio.emit(
                "exploit_chains",
                {"target": self.target_domain, "content": content},
                broadcast=True,
            )
        except Exception as exc:
            self.results["exploit_chains"].append(f"chain_suggestion_failed: {exc}")

    def to_dict(self):
        return {
            "target": self.target_domain,
            "phase": self.phase,
            "results": self.results,
        }


# Active agent pipelines
agent_pipelines = {}

# ======================
# MOBILE NODE STATUS (OpenClaw)
# ======================

class MobileNode:
    """OpenClaw mobile node status tracker."""
    
    def __init__(self):
        self.status = "offline"  # online, offline, running
        self.last_heartbeat = None
        self.channel = None  # telegram, whatsapp, discord
        self.pending_approval = []
        self.heartbeat_enabled = False
    
    def to_dict(self):
        return {
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "channel": self.channel,
            "pending_approval": self.pending_approval,
            "heartbeat_enabled": self.heartbeat_enabled
        }


mobile_node = MobileNode()


def run_heartbeat_monitor():
    """Background heartbeat monitor for OpenClaw auto-recon."""
    while True:
        if mobile_node.heartbeat_enabled:
            # Check for new targets every heartbeat_interval
            pass  # Placeholder for autonomous recon
        time.sleep(60)


heartbeat_thread = threading.Thread(target=run_heartbeat_monitor, daemon=True)
heartbeat_thread.start()


def git_sync_safe(message: str) -> dict:
    """Optional commit + push when AUTO_GIT_SYNC is enabled (use with care on public repos)."""
    flag = (os.environ.get("AUTO_GIT_SYNC") or "").lower()
    if flag not in ("1", "true", "yes", "on"):
        return {"ok": False, "skipped": True, "reason": "AUTO_GIT_SYNC not enabled"}
    safe_msg = re.sub(r"[^\w\s\-.,:;]", "", message)[:100].strip() or "zwanski: automated sync"
    branch = os.environ.get("GIT_BRANCH", "main")
    try:
        add = subprocess.run(
            ["git", "add", "-A"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=60,
        )
        if add.returncode != 0:
            return {"ok": False, "error": add.stderr or "git add failed"}
        commit = subprocess.run(
            ["git", "commit", "-m", safe_msg],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=60,
        )
        if commit.returncode != 0 and "nothing to commit" not in (commit.stdout + commit.stderr).lower():
            return {"ok": False, "error": commit.stderr or commit.stdout or "git commit failed"}
        push = subprocess.run(
            ["git", "push", "origin", branch],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=120,
        )
        return {
            "ok": push.returncode == 0,
            "stdout": push.stdout,
            "stderr": push.stderr,
            "branch": branch,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def summarize_scan_text(raw_text, max_length=3500):
    if not raw_text:
        return ""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if len(lines) == 0:
        return ""
    if len(lines) <= 120:
        result = "\n".join(lines)
    else:
        keywords = ["http", "404", "403", "500", "nginx", "amazonaws", "s3", "php", "js", "javascript", "xss", "sql", "error", "admin", "login", "api", "token", "cookie", "cloudfront", "docker", "aws", "host"]
        selected = [line for line in lines if any(k in line.lower() for k in keywords)]
        if len(selected) < 40:
            selected = lines[:20] + selected + lines[-20:]
        result = "\n".join(dict.fromkeys(selected))
    if len(result) > max_length:
        result = result[:max_length].rsplit("\n", 1)[0]
    return result


def build_prompt(template_id, context):
    template = PROMPT_TEMPLATES.get(template_id)
    if not template:
        raise ValueError("Unknown prompt template")
    summary = summarize_scan_text(context)
    return template["prompt"].format(context=summary or context)


def call_openrouter_api(api_url, key, payload):
    headers = {"Authorization": f"Bearer {key}", **OPENROUTER_HEADERS}
    response = requests.post(api_url, headers=headers, json=payload, timeout=45)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text
        try:
            parsed = response.json()
            body = json.dumps(parsed, indent=2)
        except ValueError:
            pass
        error_message = f"OpenRouter HTTP {response.status_code}: {body}"
        app.logger.error(error_message)
        raise RuntimeError(error_message) from exc
    return response.json()


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


@app.route("/api/prompt-templates", methods=["GET"])
def api_prompt_templates():
    return jsonify([
        {"id": key, "title": value["title"], "description": value["description"]}
        for key, value in PROMPT_TEMPLATES.items()
    ])


@app.route("/api/ai/analyze", methods=["POST"])
def api_ai_analyze():
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400

    body = request.get_json(silent=True) or {}
    task_id = body.get("task_id")
    template_id = body.get("template_id")
    if not task_id or not template_id:
        return jsonify({"error": "task_id and template_id are required."}), 400

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found."}), 404

    prompt = build_prompt(template_id, task.stdout + "\n" + task.stderr)
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL
    payload = {"model": config.get("model", DEFAULT_MODEL), "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 800}

    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "analysis": content})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/ai/report", methods=["POST"])
def api_ai_report():
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400

    body = request.get_json(silent=True) or {}
    task_id = body.get("task_id")
    platform = body.get("platform", "HackerOne/Bugcrowd")
    if not task_id:
        return jsonify({"error": "task_id is required."}), 400

    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found."}), 404

    prompt = PROMPT_TEMPLATES["report_generation"]["prompt"].format(context=task.stdout + "\n" + task.stderr + f"\n\nTarget platform: {platform}")
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL
    payload = {"model": config.get("model", DEFAULT_MODEL), "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 1000}

    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "report": content})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/control/restart", methods=["POST"])
def api_control_restart():
    def delayed_exit():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=delayed_exit, daemon=True).start()
    return jsonify({"ok": True, "message": "Restarting server."})


@app.route("/api/control/stop", methods=["POST"])
def api_control_stop():
    stop_file = ROOT / ".monitor_stop"
    try:
        stop_file.write_text("stop")
    except Exception:
        pass
    def delayed_exit():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=delayed_exit, daemon=True).start()
    return jsonify({"ok": True, "message": "Stopping server."})


@app.route("/api/control/status", methods=["GET"])
def api_control_status():
    return jsonify({"ok": True, "status": "running"})


@app.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400

    body = request.get_json(silent=True) or {}
    messages = body.get("messages", [])
    model = body.get("model", config.get("model", DEFAULT_MODEL))
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 600
    }

    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "message": content})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


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
        "model": config.get("model", DEFAULT_MODEL),
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 300
    }
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL

    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "grade": content})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/run", methods=["POST"])
def api_run():
    body = request.get_json(silent=True) or {}
    cmd = body.get("cmd", "").strip()
    if not cmd:
        return jsonify({"error": "No command provided."}), 400

    first = cmd.split()[0]
    if first not in ALLOWED_TOOLS and first not in {"oauth-mapper", "subdomain-recon", "./oauth-mapper", "./subdomain-recon"}:
        return jsonify({"error": f"Tool '{first}' is not allowed."}), 403

    if body.get("sync"):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
            return jsonify({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Command timed out."}), 408
        except Exception as exc:
            return jsonify({"error": str(exc)})

    task = task_manager.submit(cmd)
    return jsonify({"ok": True, "task_id": task.id, "status": task.status})


@app.route("/api/tasks", methods=["GET"])
def api_tasks():
    return jsonify(task_manager.list_tasks())


@app.route("/api/tasks/<task_id>", methods=["GET"])
def api_task_detail(task_id):
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "Task not found."}), 404
    return jsonify(task.to_dict(include_logs=True))


@app.route("/api/tasks/<task_id>/abort", methods=["POST"])
def api_task_abort(task_id):
    if task_manager.abort(task_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Unable to abort task."}), 400


@app.route("/api/deploy", methods=["POST"])
def api_deploy():
    try:
        # Git deploy
        result = subprocess.run('git add . && git commit -m "v2.0: Integrated C2 Controls, Auto-Port Recovery, Claude-Bug-Bounty Logic" || true && git push origin HEAD', shell=True, capture_output=True, text=True, cwd=str(ROOT), timeout=60)
        if result.returncode == 0:
            return jsonify({"ok": True, "output": result.stdout})
        else:
            return jsonify({"ok": False, "error": result.stderr}), 500
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


# ======================
# SYSTEM HEALTH API
# ======================

@app.route("/api/system/health", methods=["GET"])
def api_system_health():
    """Get current system health metrics."""
    return jsonify(get_system_health())


@app.route("/api/system/processes", methods=["GET"])
def api_system_processes():
    """Get list of running processes."""
    return jsonify({"processes": get_process_list()})


# ======================
# INTEGRATED TOOLS HEALTH STATUS
# ======================

@app.route("/api/health", methods=["GET"])
def api_health():
    """Get health status of all integrated tools (Subdominator, NeuroSploit, CrawlAI-RAG, OpenClaw)."""
    tools_status = {
        "subdominator": {
            "name": "Subdominator",
            "installed": tool_installed("subdominator") or shutil.which("subdominator") is not None,
            "description": "Passive subdomain enumeration by RevoltSecurities",
            "status": "available" if tool_installed("subdominator") else "not_found"
        },
        "neurosploit": {
            "name": "NeuroSploit",
            "installed": tool_installed("neurosploit") or shutil.which("neurosploit") is not None,
            "description": "AI-driven payload generation and exploit chaining by JoasASantos",
            "status": "available" if tool_installed("neurosploit") else "not_found"
        },
        "crawlai_rag": {
            "name": "CrawlAI-RAG",
            "installed": tool_installed("crawlai-rag") or shutil.which("crawlai-rag") is not None,
            "description": "Website crawling and knowledge extraction by AnkitNayak-eth",
            "status": "available" if tool_installed("crawlai-rag") else "not_found"
        },
        "openclaw": {
            "name": "OpenClaw",
            "installed": shutil.which("openclaw") is not None or os.path.exists(str(ROOT / "OpenClaw")),
            "description": "Mobile C2 bridge for Telegram/WhatsApp/Discord",
            "channel": mobile_node.channel,
            "status": mobile_node.status,
            "heartbeat_enabled": mobile_node.heartbeat_enabled
        }
    }
    
    # Count available tools
    available_count = sum(1 for t in tools_status.values() if t.get("installed", False))
    total_count = len(tools_status)
    
    # Overall system health
    config = load_config()
    system_health = get_system_health()
    
    return jsonify({
        "status": "healthy" if available_count >= 2 else "degraded",
        "message": f"{available_count}/{total_count} integrated tools available",
        "tools": tools_status,
        "api_key_configured": bool(config.get("openrouter_key")),
        "system": {
            "cpu_percent": system_health["cpu_percent"],
            "memory_percent": system_health["memory_percent"],
            "uptime": system_health["timestamp"]
        }
    })


# ======================
# AGENT PIPELINE API
# ======================

@app.route("/api/agent/run", methods=["POST"])
def api_agent_run():
    """Start an agent pipeline for a target."""
    body = request.get_json(silent=True) or {}
    target = body.get("target", "").strip()
    if not target:
        return jsonify({"error": "Target (domain) is required."}), 400
    
    # Validate target format
    if not target.replace(".", "").replace("-", "").isalnum():
        return jsonify({"error": "Invalid target format."}), 400
    
    pipeline_id = uuid.uuid4().hex
    pipeline = AgentPipeline(target)
    agent_pipelines[pipeline_id] = pipeline
    
    # Run pipeline in background thread
    def run_pipeline(pipeline_id, pipeline):
        try:
            pipeline.run_full_pipeline()
        except Exception as e:
            print(f"Pipeline error: {e}")
    
    thread = threading.Thread(target=run_pipeline, args=(pipeline_id, pipeline), daemon=True)
    thread.start()
    
    return jsonify({
        "ok": True,
        "pipeline_id": pipeline_id,
        "target": target,
        "status": "started"
    })


@app.route("/api/agent/<pipeline_id>", methods=["GET"])
def api_agent_status(pipeline_id):
    """Get status of an agent pipeline."""
    pipeline = agent_pipelines.get(pipeline_id)
    if not pipeline:
        return jsonify({"error": "Pipeline not found."}), 404
    return jsonify(pipeline.to_dict())


@app.route("/api/agent", methods=["GET"])
def api_agent_list():
    """List all agent pipelines."""
    return jsonify({
        "pipelines": [p.to_dict() for p in agent_pipelines.values()]
    })


# ======================
# AUTO-REPORTING API
# ======================

@app.route("/api/report/finalize", methods=["POST"])
def api_report_finalize():
    """Generate a final report from agent logs and recon data."""
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400
    
    body = request.get_json(silent=True) or {}
    pipeline_id = body.get("pipeline_id")
    target = body.get("target", "")
    platform = body.get("platform", "HackerOne")
    
    # Get pipeline data
    pipeline_data = ""
    if pipeline_id:
        pipeline = agent_pipelines.get(pipeline_id)
        if pipeline:
            pipeline_data = json.dumps(pipeline.results, indent=2)
    
    # Get task data
    task_data = ""
    recent_tasks = task_manager.list_tasks()[:5]
    for task in recent_tasks:
        task_data += f"\n--- Task: {task['cmd']} ---\n"
        task_data += task.get("stdout", "")[:1000]
    
    # Build comprehensive report prompt
    prompt = f"""You are a professional bug bounty report writer. Create a comprehensive security assessment report.

Target: {target}

=== AGENT PIPELINE RESULTS ===
{pipeline_data}

=== RECENT TASK OUTPUT ===
{task_data}

Generate a professional report with these sections:
1. Executive Summary
2. Scope
3. Methodology  
4. Findings (with severity ratings: Critical, High, Medium, Low)
5. Impact Analysis
6. Proof of Concept
7. Remediation Recommendations
8. References

Make it suitable for {platform} submission. Use clear markdown formatting."""

    messages = [
        {"role": "system", "content": "You are a professional vulnerability report writer."},
        {"role": "user", "content": prompt}
    ]
    
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL
    payload = {
        "model": config.get("model", DEFAULT_MODEL),
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2000
    }
    
    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Save report to file
        report_filename = ROOT / f"report_{target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_filename.write_text(content)
        
        sync = git_sync_safe(f"Report generated for {target}")
        return jsonify({
            "ok": True,
            "report": content,
            "report_file": str(report_filename),
            "git_sync": sync,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/warmap", methods=["GET"])
def api_warmap():
    return jsonify(WARMAP_STATE)


@app.route("/api/openclaw/commands", methods=["GET"])
def api_openclaw_commands():
    bridge = ROOT / "openclaw_bridge.json"
    if not bridge.exists():
        return jsonify({"error": "openclaw_bridge.json missing"}), 404
    return jsonify(json.loads(bridge.read_text()))


@app.route("/api/kb/query", methods=["POST"])
def api_kb_query():
    body = request.get_json(silent=True) or {}
    target = (body.get("target") or "").strip()
    question = (body.get("question") or "").strip()
    if not target or not question:
        return jsonify({"error": "target and question required"}), 400
    kb = TargetKnowledgeBase(ROOT, target)
    chunks = kb.query(question)
    return jsonify({"ok": True, "chunks": chunks, "chars": len(chunks)})


@app.route("/api/ai/rag-analyze", methods=["POST"])
def api_ai_rag_analyze():
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400
    body = request.get_json(silent=True) or {}
    target = (body.get("target") or "").strip()
    if not target:
        return jsonify({"error": "target required"}), 400
    kb = TargetKnowledgeBase(ROOT, target)
    ctx = kb.query(body.get("focus") or "business logic auth workflow payment upload export admin oauth api")
    if not ctx.strip():
        return jsonify({"error": "No knowledge base yet for this target. Run the agent pipeline first."}), 400
    prompt = (
        "You are a bug bounty hunter prioritizing business-logic flaws. "
        "Using ONLY the provided recon context, list plausible high-impact logic flaws "
        "(IDOR, workflow abuse, feature flags, multi-step chains). Avoid generic CVE boilerplate.\n\n"
        f"=== Context ===\n{ctx[:9000]}"
    )
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL
    payload = {
        "model": config.get("model", DEFAULT_MODEL),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 1000,
    }
    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "analysis": content})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/ai/exploit-chain", methods=["POST"])
def api_ai_exploit_chain():
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        return jsonify({"error": "OpenRouter API key is not set."}), 400
    body = request.get_json(silent=True) or {}
    finding = (body.get("finding") or "").strip()
    target = (body.get("target") or "").strip()
    if not finding:
        return jsonify({"error": "finding text required"}), 400
    kb_ctx = ""
    if target:
        kb_ctx = TargetKnowledgeBase(ROOT, target).query(finding)[:6000]
    prompt = (
        "Given a confirmed or suspected vulnerability, propose one or two realistic exploit CHAINS "
        "(next hops, endpoints to test, escalation paths). Be specific to the stack hints in the text. "
        "Output markdown.\n\n"
        f"=== Finding ===\n{finding}\n\n=== Optional recon ===\n{kb_ctx}"
    )
    api_url = config.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL
    payload = {
        "model": config.get("model", DEFAULT_MODEL),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.15,
        "max_tokens": 800,
    }
    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return jsonify({"ok": True, "chains": content})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/findings/confirm", methods=["POST"])
def api_findings_confirm():
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "Confirmed finding").strip()
    severity = (body.get("severity") or "").strip().lower()
    trigger = severity in ("high", "critical") or body.get("force_sync") is True
    if not trigger:
        return jsonify({"ok": True, "git_sync": {"skipped": True, "reason": "severity below threshold"}})
    msg = f"Finding confirmed [{severity}]: {title}"
    sync = git_sync_safe(msg)
    return jsonify({"ok": True, "git_sync": sync})


@socketio.on('connect')
def handle_connect():
    emit("status", {"message": "Connected to ZWANSKI Dashboard"})
    emit("warmap_update", WARMAP_STATE)

@socketio.on('run_command')
def handle_run_command(data):
    command = data.get('command', '')
    if not command:
        return
    first = command.split()[0]
    if first not in ALLOWED_TOOLS and first not in {"oauth-mapper", "subdomain-recon", "./oauth-mapper", "./subdomain-recon"}:
        emit('terminal_output', {'output': f"Error: Tool '{first}' is not allowed.\n"})
        return

    task = task_manager.submit(command)
    emit('task_started', {'task_id': task.id, 'status': task.status, 'cmd': task.cmd})

@socketio.on('ai_chat')
def handle_ai_chat(data):
    config = load_config()
    key = config.get("openrouter_key", "")
    if not key:
        emit('ai_response', {'error': 'API key not set'})
        return
    messages = data.get('messages', [])
    model = data.get('model', config.get('model', DEFAULT_MODEL))
    api_url = config.get('api_url', DEFAULT_API_URL) or DEFAULT_API_URL
    payload = {"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 600}
    try:
        data = call_openrouter_api(api_url, key, payload)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        emit('ai_response', {'response': content})
    except Exception as e:
        emit('ai_response', {'error': str(e)})


def free_port(port: int) -> None:
    """Terminate listeners on TCP port using psutil, then fall back to fuser/lsof."""
    pids = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if not conn.laddr:
                continue
            if conn.laddr.port != port:
                continue
            if conn.status != psutil.CONN_LISTEN:
                continue
            if conn.pid:
                pids.add(conn.pid)
    except (psutil.AccessDenied, AttributeError):
        pass
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if pids:
        time.sleep(0.3)
    if shutil.which("fuser"):
        subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    if shutil.which("lsof"):
        result = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if line.strip().isdigit():
                try:
                    os.kill(int(line.strip()), signal.SIGKILL)
                except OSError:
                    pass
        return
    if not pids:
        print(
            "Warning: could not detect process on port; install fuser or lsof if bind fails.",
            file=sys.stderr,
        )


def open_browser(port):
    url = f"http://localhost:{port}"
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 1337))
    free_port(port)
    threading.Timer(1.2, lambda: open_browser(port)).start()
    print(f"Starting ZWANSKI dashboard on http://localhost:{port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
