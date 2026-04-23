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
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from urllib.parse import urlparse
from datetime import datetime, timezone
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
WATCHDOG_ROOT = ROOT / "zwanski-watchdog"

from zwanski_kb import TargetKnowledgeBase
from shadow_client import shadow_request
from version_manager import version_manager
from reporting_enhanced import cvss_calculator, finding_tracker, report_generator
from scope_manager import scope_manager

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
# threading: avoids deprecated eventlet; server-side emits from worker threads need app_context (see emit_to_all).
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


def utc_now_iso_z() -> str:
    """UTC timestamp with Z suffix (replaces deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit_to_all(event: str, data) -> None:
    """Broadcast to every connected client from any thread (python-socketio 5+ has no broadcast= kwarg)."""
    with app.app_context():
        socketio.emit(event, data, namespace="/")


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


def get_setup_requirements(config):
    key_set = bool((config.get("openrouter_key") or "").strip())
    requirements = [
        {
            "id": "openrouter_key",
            "label": "OpenRouter API key",
            "kind": "api",
            "required": True,
            "ready": key_set,
            "description": "Required for Intel AI analysis, report generation, and exploit-chain suggestions.",
            "configure_tab": "settings",
        },
        {
            "id": "tmux",
            "label": "tmux terminal multiplexer",
            "kind": "tool",
            "required": True,
            "ready": tool_installed("tmux"),
            "description": "Enables non-blocking parallel terminal panes in the Terminal panel.",
            "install_cmd": "sudo apt install -y tmux",
        },
        {
            "id": "docker",
            "label": "Docker engine",
            "kind": "tool",
            "required": True,
            "ready": tool_installed("docker"),
            "description": "Needed to run Watchdog infra services (Redis/Postgres/Elasticsearch/MinIO/IPFS).",
            "install_cmd": "sudo apt install -y docker.io",
        },
        {
            "id": "pnpm",
            "label": "pnpm package manager",
            "kind": "tool",
            "required": False,
            "ready": tool_installed("pnpm"),
            "description": "Used by Watchdog API/Web workspaces and JavaScript monorepo tasks.",
            "install_cmd": "sudo npm i -g pnpm",
        },
        {
            "id": "subfinder",
            "label": "Subfinder",
            "kind": "tool",
            "required": False,
            "ready": tool_installed("subfinder"),
            "description": "Recommended passive recon dependency for subdomain workflows.",
            "install_cmd": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        },
        {
            "id": "nuclei",
            "label": "Nuclei",
            "kind": "tool",
            "required": False,
            "ready": tool_installed("nuclei"),
            "description": "Recommended vulnerability scanner for Arsenal and agentic attack phases.",
            "install_cmd": "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        },
    ]
    return requirements


class Task:
    def __init__(self, cmd):
        self.id = uuid.uuid4().hex
        self.cmd = cmd
        self.status = "pending"
        self.stdout = ""
        self.stderr = ""
        self.returncode = None
        self.created_at = utc_now_iso_z()
        self.updated_at = self.created_at
        self.logs = []
        self.proc = None
        self.pid = None
        self.session_name = None
        self.pane_id = None
        self.archived = False

    def append_output(self, text, stream="stdout"):
        self.logs.append({"stream": stream, "text": text, "timestamp": utc_now_iso_z()})
        if stream == "stdout":
            self.stdout += text
        else:
            self.stderr += text
        self.updated_at = utc_now_iso_z()

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
            "summary": self.logs[-1]["text"] if self.logs else "",
            "pid": self.pid,
            "session_name": self.session_name,
            "pane_id": self.pane_id,
            "archived": self.archived,
        }
        if include_logs:
            data["logs"] = self.logs
        return data


class TaskManager:
    def __init__(self, persistence_file=None):
        self.tasks = {}
        self.lock = threading.Lock()
        self.persistence_file = persistence_file or (ROOT / "tasks.json")
        self.tmux_available = shutil.which("tmux") is not None
        self._load_tasks()

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
                task.pid = item.get("pid")
                task.session_name = item.get("session_name")
                task.pane_id = item.get("pane_id")
                task.archived = item.get("archived", False)
                self.tasks[task.id] = task
        except Exception:
            pass

    def _save_tasks(self):
        try:
            self.persistence_file.write_text(json.dumps([task.to_dict(include_logs=True) for task in self.tasks.values()], indent=2))
        except Exception:
            pass

    def submit(self, cmd):
        task = Task(cmd)
        with self.lock:
            self.tasks[task.id] = task
        self._save_tasks()
        self._emit_task_update(task)
        threading.Thread(target=self._execute_task, args=(task,), daemon=True).start()
        return task

    def _run_tmux(self, args):
        return subprocess.run(["tmux"] + args, capture_output=True, text=True)

    def _capture_tmux(self, pane_id):
        result = self._run_tmux(["capture-pane", "-pt", pane_id, "-S", "-4000", "-J"])
        return result.stdout if result.returncode == 0 else ""

    def _execute_tmux_task(self, task):
        task.session_name = f"zw_{task.id[:8]}"
        quoted_cmd = shlex.quote(f'cd "{ROOT}" && {task.cmd}')
        wrapped = f"bash -lc {quoted_cmd}; rc=$?; echo __ZW_EXIT__:$rc"
        created = self._run_tmux(["new-session", "-d", "-P", "-F", "#{pane_id}", "-s", task.session_name, wrapped])
        if created.returncode != 0:
            raise RuntimeError(created.stderr.strip() or "failed to create tmux session")
        task.pane_id = created.stdout.strip()
        marker_re = re.compile(r"__ZW_EXIT__:(\d+)")
        last = ""
        returncode = None
        idle_ticks = 0
        while True:
            captured = self._capture_tmux(task.pane_id)
            if captured and captured != last:
                if captured.startswith(last):
                    delta = captured[len(last):]
                else:
                    delta = captured
                if delta:
                    task.append_output(delta, stream="stdout")
                    self._emit_task_output(task, delta, "stdout")
                last = captured
                idle_ticks = 0
            else:
                idle_ticks += 1
            marker = marker_re.search(captured or "")
            if marker:
                returncode = int(marker.group(1))
            alive = self._run_tmux(["has-session", "-t", task.session_name]).returncode == 0
            if returncode is not None and (not alive or idle_ticks > 2):
                break
            time.sleep(0.7)
        if alive:
            self._run_tmux(["kill-session", "-t", task.session_name])
        task.returncode = 0 if returncode is None else returncode
        task.archived = True

    def _execute_task(self, task):
        task.status = "running"
        task.updated_at = utc_now_iso_z()
        self._save_tasks()
        self._emit_task_update(task)
        try:
            if self.tmux_available:
                self._execute_tmux_task(task)
            else:
                proc = subprocess.Popen(
                    task.cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(ROOT)
                )
                task.proc = proc
                task.pid = proc.pid

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
            task.status = "completed" if task.returncode == 0 else "failed"
        except Exception as exc:
            task.append_output(str(exc) + "\n", stream="stderr")
            task.status = "failed"
            task.returncode = -1
        finally:
            task.updated_at = utc_now_iso_z()
            self._save_tasks()
            self._emit_task_update(task)
            try:
                merge_warmap_from_text(task.stdout + "\n" + task.stderr, "")
            except Exception:
                pass

    def _emit_task_output(self, task, text, stream):
        emit_to_all(
            "terminal_output",
            {"task_id": task.id, "output": text, "stream": stream},
        )

    def _emit_task_update(self, task):
        emit_to_all("task_update", task.to_dict(include_logs=False))

    def list_tasks(self):
        return [task.to_dict(include_logs=False) for task in sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)]

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def abort(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return False
        try:
            if task.session_name and self.tmux_available:
                self._run_tmux(["kill-session", "-t", task.session_name])
            elif task.proc and task.proc.poll() is None:
                task.proc.terminate()
            else:
                return False
            task.status = "cancelled"
            task.archived = True
            task.updated_at = utc_now_iso_z()
            self._save_tasks()
            self._emit_task_update(task)
            return True
        except Exception:
            return False

    def list_terminals(self):
        out = []
        for task in self.list_tasks():
            if task.get("session_name") or task.get("pid"):
                out.append(
                    {
                        "task_id": task["id"],
                        "label": task["cmd"][:64],
                        "status": task["status"],
                        "pid": task.get("pid"),
                        "session_name": task.get("session_name"),
                        "pane_id": task.get("pane_id"),
                        "archived": task.get("archived", False),
                    }
                )
        return out


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
        "updated_at": utc_now_iso_z(),
    }
    emit_to_all("warmap_update", WARMAP_STATE)


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
        "timestamp": utc_now_iso_z(),
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
            emit_to_all("system_health", health)
            emit_to_all("process_update", {"processes": processes})
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
        emit_to_all("agent_log", {"message": entry, "phase": self.phase})

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
            emit_to_all(
                "exploit_chains",
                {"target": self.target_domain, "content": content},
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


@app.route("/api/setup/checklist", methods=["GET"])
def api_setup_checklist():
    config = load_config()
    onboarding = config.get("onboarding", {})
    decisions = onboarding.get("decisions", {})
    reqs = get_setup_requirements(config)
    items = []
    for item in reqs:
        entry = dict(item)
        entry["decision"] = decisions.get(item["id"])
        items.append(entry)
    return jsonify(
        {
            "ok": True,
            "first_launch": not onboarding.get("completed", False),
            "completed": onboarding.get("completed", False),
            "items": items,
        }
    )


@app.route("/api/setup/decision", methods=["POST"])
def api_setup_decision():
    body = request.get_json(silent=True) or {}
    item_id = (body.get("item_id") or "").strip()
    decision = (body.get("decision") or "").strip().lower()
    if not item_id or decision not in {"install", "skip", "configure", "done"}:
        return jsonify({"error": "item_id and valid decision are required"}), 400
    config = load_config()
    onboarding = config.setdefault("onboarding", {})
    decisions = onboarding.setdefault("decisions", {})
    decisions[item_id] = {"decision": decision, "updated_at": utc_now_iso_z()}
    save_config(config)
    return jsonify({"ok": True})


@app.route("/api/setup/complete", methods=["POST"])
def api_setup_complete():
    config = load_config()
    onboarding = config.setdefault("onboarding", {})
    onboarding["completed"] = True
    onboarding["completed_at"] = utc_now_iso_z()
    save_config(config)
    return jsonify({"ok": True, "completed_at": onboarding["completed_at"]})


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

    normalized_cmd = _normalize_dashboard_command(cmd)

    if body.get("sync"):
        try:
            result = subprocess.run(normalized_cmd, shell=True, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
            return jsonify({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            })
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Command timed out."}), 408
        except Exception as exc:
            return jsonify({"error": str(exc)})

    task = task_manager.submit(normalized_cmd)
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


@app.route("/api/term/sessions", methods=["GET"])
def api_term_sessions():
    return jsonify({"sessions": task_manager.list_terminals()})


@app.route("/api/term/<task_id>/kill", methods=["POST"])
def api_term_kill(task_id):
    if task_manager.abort(task_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Unable to kill terminal session."}), 400


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
    raw_target = body.get("target", "").strip()
    if not raw_target:
        return jsonify({"error": "Target (domain) is required."}), 400

    # Accept common forms like https://example.com or example.com/path.
    parsed = urlparse(raw_target if "://" in raw_target else f"//{raw_target}")
    target = (parsed.hostname or raw_target).strip().lower().rstrip(".")

    # Validate normalized hostname format.
    if not target.replace(".", "").replace("-", "").isalnum():
        return jsonify({"error": "Invalid target format. Use a domain like example.com."}), 400
    
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


def _watchdog_service_urls():
    """URLs for Watchdog stack (override via .env)."""
    return {
        "api": os.environ.get("WATCHDOG_API_URL", "http://127.0.0.1:4000").rstrip("/"),
        "web": os.environ.get("WATCHDOG_WEB_URL", "http://127.0.0.1:3000").rstrip("/"),
        "classifier": os.environ.get("WATCHDOG_CLASSIFIER_URL", "http://127.0.0.1:8001").rstrip("/"),
    }


def _http_probe(url: str, path: str, timeout: float = 2.0):
    """Return (reachable, status_code_or_none, error_hint)."""
    try:
        r = requests.get(f"{url}{path}", timeout=timeout, allow_redirects=True)
        return True, r.status_code, None
    except requests.RequestException as exc:
        return False, None, str(exc)[:120]


@app.route("/api/watchdog/info", methods=["GET"])
def api_watchdog_info():
    """Static paths and quick-start hints for the embedded Watchdog monorepo."""
    urls = _watchdog_service_urls()
    compose = WATCHDOG_ROOT / "infra" / "docker-compose.yml"
    return jsonify(
        {
            "ok": True,
            "installed": WATCHDOG_ROOT.is_dir() and (WATCHDOG_ROOT / "README.md").exists(),
            "root": str(WATCHDOG_ROOT),
            "docker_compose": str(compose) if compose.is_file() else None,
            "urls": urls,
            "docs_url": "https://github.com/zwanski2019/zwanski-Bug-Bounty/tree/main/zwanski-watchdog",
        }
    )


@app.route("/api/watchdog/status", methods=["GET"])
def api_watchdog_status():
    """Reachability of Watchdog API / web / classifier (when you run them locally)."""
    urls = _watchdog_service_urls()
    api_ok, api_code, api_err = _http_probe(urls["api"], "/health")
    web_ok, web_code, web_err = _http_probe(urls["web"], "/")
    clf_ok, clf_code, clf_err = _http_probe(urls["classifier"], "/health")
    return jsonify(
        {
            "ok": True,
            "installed": WATCHDOG_ROOT.is_dir(),
            "services": {
                "api": {"url": urls["api"], "up": api_ok, "status": api_code, "error": api_err},
                "web": {"url": urls["web"], "up": web_ok, "status": web_code, "error": web_err},
                "classifier": {"url": urls["classifier"], "up": clf_ok, "status": clf_code, "error": clf_err},
            },
        }
    )


def _watchdog_shell_tasks():
    """Fixed commands only — no user-controlled shell fragments."""
    r = str(WATCHDOG_ROOT.resolve())
    compose_up_cmd = (
        "sh -c 'if docker compose version >/dev/null 2>&1; "
        "then docker compose -f - up -d postgres redis elasticsearch minio ipfs; "
        "else docker-compose -f - up -d postgres redis elasticsearch minio ipfs; fi'"
    )
    compose_down_cmd = (
        "sh -c 'if docker compose version >/dev/null 2>&1; "
        "then docker compose -f - down; "
        "else docker-compose -f - down; fi'"
    )
    return {
        "compose_up": f'cd "{r}/infra" && python3 -c "from pathlib import Path; print(Path(\'{r}/infra/docker-compose.yml\').read_text())" | {compose_up_cmd}',
        "compose_down": f'cd "{r}/infra" && python3 -c "from pathlib import Path; print(Path(\'{r}/infra/docker-compose.yml\').read_text())" | {compose_down_cmd}',
        "pnpm_install": f'cd "{r}" && pnpm install',
        "api_dev": f'cd "{r}" && pnpm --filter @zwanski/api dev',
        "web_dev": f'cd "{r}" && pnpm --filter @zwanski/web dev',
        "classifier_dev": (
            f'cd "{r}/apps/classifier" && pip install -q -r requirements.txt '
            f'&& uvicorn main:app --host 127.0.0.1 --port 8001'
        ),
        "scanner_dry": f'cd "{r}/apps/scanner" && go run ./cmd/watchdog --dry-run --modules s3',
        "scanner_help": f'cd "{r}/apps/scanner" && go run ./cmd/watchdog --help',
    }


def _normalize_dashboard_command(cmd: str) -> str:
    """Normalize wrapper invocations to absolute paths under platform root."""
    parts = shlex.split(cmd, posix=True)
    if not parts:
        return cmd
    first = parts[0]
    alias_map = {
        "oauth-mapper": str(ROOT / "oauth-mapper"),
        "./oauth-mapper": str(ROOT / "oauth-mapper"),
        "subdomain-recon": str(ROOT / "subdomain-recon"),
        "./subdomain-recon": str(ROOT / "subdomain-recon"),
    }
    mapped = alias_map.get(first)
    if not mapped:
        return cmd
    parts[0] = mapped
    return " ".join(shlex.quote(p) for p in parts)


@app.route("/api/watchdog/run", methods=["POST"])
def api_watchdog_run():
    """Queue a predefined Watchdog maintenance command (streams in Terminal tab)."""
    if not WATCHDOG_ROOT.is_dir():
        return jsonify({"error": "zwanski-watchdog directory not found in platform root."}), 404
    body = request.get_json(silent=True) or {}
    task_key = (body.get("task") or "").strip()
    tasks = _watchdog_shell_tasks()
    if task_key not in tasks:
        return jsonify({"error": "unknown task", "allowed": list(tasks.keys())}), 400
    cmd = tasks[task_key]
    if task_key.startswith("compose_"):
        compose_file = WATCHDOG_ROOT / "infra" / "docker-compose.yml"
        if compose_file.exists() and not os.access(compose_file, os.R_OK):
            return jsonify(
                {
                    "error": (
                        f"Permission denied reading {compose_file}. "
                        "Fix ownership/permissions on ~/.zwanski-bb (example: "
                        f"sudo chown -R {os.getenv('USER', 'your-user')}:{os.getenv('USER', 'your-user')} ~/.zwanski-bb)."
                    )
                }
            ), 403
    t = task_manager.submit(cmd)
    return jsonify({"ok": True, "task_id": t.id, "cmd": cmd})


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

    normalized_cmd = _normalize_dashboard_command(command)
    task = task_manager.submit(normalized_cmd)
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


# ======================
# VERSION & UPDATE MANAGEMENT
# ======================

@app.route("/api/version", methods=["GET"])
def api_version():
    """Get current version and check for updates."""
    force = request.args.get("force", "false").lower() == "true"
    status = version_manager.check_for_updates(force=force)
    return jsonify(status)


@app.route("/api/update", methods=["POST"])
def api_update():
    """Perform git pull update."""
    result = version_manager.perform_update()
    return jsonify(result)


@app.route("/api/git-status", methods=["GET"])
def api_git_status():
    """Get git repository status."""
    status = version_manager.get_git_status()
    return jsonify(status)


# ======================
# CVSS CALCULATOR
# ======================

@app.route("/api/cvss/calculate", methods=["POST"])
def api_cvss_calculate():
    """Calculate CVSS score from metrics."""
    data = request.get_json()
    metrics = data.get("metrics", {})
    result = cvss_calculator.calculate(metrics)
    return jsonify(result)


# ======================
# FINDING TRACKER
# ======================

@app.route("/api/findings", methods=["GET"])
def api_findings_list():
    """List all findings with optional filters."""
    filters = {
        "status": request.args.get("status"),
        "severity": request.args.get("severity"),
        "target": request.args.get("target"),
        "platform": request.args.get("platform")
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    findings = finding_tracker.list_findings(filters if filters else None)
    return jsonify({"findings": findings})


@app.route("/api/findings", methods=["POST"])
def api_findings_add():
    """Add a new finding."""
    data = request.get_json()
    finding_id = finding_tracker.add_finding(data)
    return jsonify({"id": finding_id, "success": True})


@app.route("/api/findings/<finding_id>", methods=["GET"])
def api_findings_get(finding_id):
    """Get a specific finding."""
    finding = finding_tracker.get_finding(finding_id)
    if finding:
        return jsonify(finding)
    return jsonify({"error": "Finding not found"}), 404


@app.route("/api/findings/<finding_id>", methods=["PUT"])
def api_findings_update(finding_id):
    """Update a finding."""
    data = request.get_json()
    success = finding_tracker.update_finding(finding_id, data)
    return jsonify({"success": success})


@app.route("/api/findings/<finding_id>", methods=["DELETE"])
def api_findings_delete(finding_id):
    """Delete a finding."""
    success = finding_tracker.delete_finding(finding_id)
    return jsonify({"success": success})


@app.route("/api/findings/stats", methods=["GET"])
def api_findings_stats():
    """Get finding statistics."""
    stats = finding_tracker.get_stats()
    return jsonify(stats)


# ======================
# REPORT GENERATION
# ======================

@app.route("/api/report/generate", methods=["POST"])
def api_report_generate():
    """Generate a platform-specific vulnerability report."""
    data = request.get_json()
    finding = data.get("finding", {})
    platform = data.get("platform", "HackerOne")
    
    report = report_generator.generate_report(finding, platform)
    return jsonify({"report": report, "platform": platform})


@app.route("/api/report/platforms", methods=["GET"])
def api_report_platforms():
    """Get list of supported platforms."""
    platforms = list(report_generator.PLATFORM_TEMPLATES.keys())
    return jsonify({"platforms": platforms})


# ======================
# SCOPE MANAGEMENT
# ======================

@app.route("/api/scope/programs", methods=["GET"])
def api_scope_programs_list():
    """List all bug bounty programs."""
    filters = {
        "platform": request.args.get("platform"),
        "active": request.args.get("active"),
        "search": request.args.get("search")
    }
    # Remove None values and convert active to bool
    filters = {k: v for k, v in filters.items() if v is not None}
    if "active" in filters:
        filters["active"] = filters["active"].lower() == "true"
    
    programs = scope_manager.list_programs(filters if filters else None)
    return jsonify({"programs": programs})


@app.route("/api/scope/programs", methods=["POST"])
def api_scope_programs_add():
    """Add a new bug bounty program."""
    data = request.get_json()
    program_id = scope_manager.add_program(data)
    return jsonify({"id": program_id, "success": True})


@app.route("/api/scope/programs/<program_id>", methods=["GET"])
def api_scope_programs_get(program_id):
    """Get a specific program."""
    program = scope_manager.get_program(program_id)
    if program:
        return jsonify(program)
    return jsonify({"error": "Program not found"}), 404


@app.route("/api/scope/programs/<program_id>", methods=["PUT"])
def api_scope_programs_update(program_id):
    """Update a program."""
    data = request.get_json()
    success = scope_manager.update_program(program_id, data)
    return jsonify({"success": success})


@app.route("/api/scope/programs/<program_id>", methods=["DELETE"])
def api_scope_programs_delete(program_id):
    """Delete a program."""
    success = scope_manager.delete_program(program_id)
    return jsonify({"success": success})


@app.route("/api/scope/check", methods=["POST"])
def api_scope_check():
    """Check if a target is in scope."""
    data = request.get_json()
    target = data.get("target")
    program_id = data.get("program_id")
    
    if not target:
        return jsonify({"error": "Target required"}), 400
    
    result = scope_manager.check_in_scope(target, program_id)
    return jsonify(result)


@app.route("/api/scope/parse", methods=["POST"])
def api_scope_parse():
    """Parse scope from text."""
    data = request.get_json()
    text = data.get("text", "")
    
    parsed = scope_manager.parse_scope_from_text(text)
    return jsonify(parsed)


@app.route("/api/scope/stats", methods=["GET"])
def api_scope_stats():
    """Get scope statistics."""
    stats = scope_manager.get_stats()
    return jsonify(stats)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 1337))
    free_port(port)
    threading.Timer(1.2, lambda: open_browser(port)).start()
    print(f"Starting ZWANSKI dashboard on http://localhost:{port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
