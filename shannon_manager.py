#!/usr/bin/env python3
"""
Shannon AI Pentest Manager
Integrates Shannon (KeygraphHQ/shannon) into the zwanski-BB dashboard.
Manages scan lifecycle, log streaming, and Temporal workflow state.
"""

import json
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

SHANNON_ROOT = Path(os.environ.get("SHANNON_ROOT", Path.home() / "shannon"))
SCANS_FILE = Path(__file__).resolve().parent / "shannon_scans.json"
TEMPORAL_API = "http://localhost:8233/api/v1"

ALL_AGENTS = [
    "pre-recon",
    "recon",
    "injection-vuln",
    "xss-vuln",
    "auth-vuln",
    "ssrf-vuln",
    "authz-vuln",
    "oauth-sso-vuln",
    "env-bleed-vuln",
    "second-order-vuln",
    "injection-exploit",
    "xss-exploit",
    "auth-exploit",
    "ssrf-exploit",
    "authz-exploit",
    "oauth-sso-exploit",
    "env-bleed-exploit",
    "second-order-exploit",
    "report",
]

PHASE_MAP = {
    "pre-recon": "Pre-Recon",
    "recon": "Recon",
    "injection-vuln": "Vuln Analysis",
    "xss-vuln": "Vuln Analysis",
    "auth-vuln": "Vuln Analysis",
    "ssrf-vuln": "Vuln Analysis",
    "authz-vuln": "Vuln Analysis",
    "oauth-sso-vuln": "Vuln Analysis",
    "env-bleed-vuln": "Vuln Analysis",
    "second-order-vuln": "Vuln Analysis",
    "injection-exploit": "Exploitation",
    "xss-exploit": "Exploitation",
    "auth-exploit": "Exploitation",
    "ssrf-exploit": "Exploitation",
    "authz-exploit": "Exploitation",
    "oauth-sso-exploit": "Exploitation",
    "env-bleed-exploit": "Exploitation",
    "second-order-exploit": "Exploitation",
    "report": "Reporting",
}


# ─────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────

class ShannonScan:
    def __init__(self, scan_id, target, workspace, config_path=None):
        self.scan_id = scan_id
        self.target = target
        self.workspace = workspace
        self.config_path = config_path
        self.status = "starting"       # starting | running | completed | failed | stopped
        self.workflow_id = None
        self.current_phase = None
        self.current_agent = None
        self.completed_agents = []
        self.failed_agent = None
        self.error = None
        self.cost_usd = 0.0
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at = None
        self.report_path = None
        self._process = None           # subprocess handle (not serialised)

    def to_dict(self):
        return {
            "scan_id": self.scan_id,
            "target": self.target,
            "workspace": self.workspace,
            "config_path": self.config_path,
            "status": self.status,
            "workflow_id": self.workflow_id,
            "current_phase": self.current_phase,
            "current_agent": self.current_agent,
            "completed_agents": self.completed_agents,
            "failed_agent": self.failed_agent,
            "error": self.error,
            "cost_usd": self.cost_usd,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "report_path": self.report_path,
            "progress_pct": self._progress_pct(),
            "agent_count": len(ALL_AGENTS),
            "agents_done": len(self.completed_agents),
        }

    def _progress_pct(self):
        if not self.completed_agents:
            return 0
        return round(len(self.completed_agents) / len(ALL_AGENTS) * 100)

    @staticmethod
    def from_dict(d):
        s = ShannonScan(d["scan_id"], d["target"], d["workspace"], d.get("config_path"))
        s.status = d.get("status", "unknown")
        s.workflow_id = d.get("workflow_id")
        s.current_phase = d.get("current_phase")
        s.current_agent = d.get("current_agent")
        s.completed_agents = d.get("completed_agents", [])
        s.failed_agent = d.get("failed_agent")
        s.error = d.get("error")
        s.cost_usd = d.get("cost_usd", 0.0)
        s.started_at = d.get("started_at")
        s.completed_at = d.get("completed_at")
        s.report_path = d.get("report_path")
        return s


# ─────────────────────────────────────────────
# Manager
# ─────────────────────────────────────────────

class ShannonManager:
    def __init__(self):
        self._scans: dict[str, ShannonScan] = {}
        self._lock = threading.Lock()
        self._emit_fn = None           # injected by server.py
        self._load_scans()

    # ── Dependency injection ──────────────────

    def set_emit(self, fn):
        """Inject the emit_to_all function from server.py."""
        self._emit_fn = fn

    def _emit(self, event, data):
        if self._emit_fn:
            try:
                self._emit_fn(event, data)
            except Exception:
                pass

    # ── Persistence ───────────────────────────

    def _load_scans(self):
        if SCANS_FILE.exists():
            try:
                data = json.loads(SCANS_FILE.read_text())
                for d in data:
                    s = ShannonScan.from_dict(d)
                    self._scans[s.scan_id] = s
            except Exception:
                pass

    def _save_scans(self):
        try:
            SCANS_FILE.write_text(
                json.dumps([s.to_dict() for s in self._scans.values()], indent=2)
            )
        except Exception:
            pass

    # ── Shannon CLI helpers ───────────────────

    @property
    def shannon_cli(self):
        return str(SHANNON_ROOT / "shannon")

    def _shannon_available(self):
        return (SHANNON_ROOT / "shannon").exists()

    # ── Infrastructure ────────────────────────

    def get_infra_status(self):
        """Check Temporal health and whether the shannon-temporal container is up."""
        temporal_ok = False
        temporal_version = None
        try:
            r = requests.get(f"{TEMPORAL_API}/cluster-info", timeout=3)
            if r.status_code == 200:
                temporal_ok = True
                info = r.json()
                temporal_version = info.get("serverVersion")
        except Exception:
            pass

        shannon_path_ok = self._shannon_available()

        # Count active workflows
        active_workflows = 0
        try:
            r = requests.get(
                f"{TEMPORAL_API}/namespaces/default/workflows",
                params={"query": 'ExecutionStatus="Running"', "pageSize": 50},
                timeout=3,
            )
            if r.status_code == 200:
                executions = r.json().get("executions", [])
                active_workflows = len(executions)
        except Exception:
            pass

        return {
            "temporal_ok": temporal_ok,
            "temporal_version": temporal_version,
            "shannon_path": str(SHANNON_ROOT),
            "shannon_available": shannon_path_ok,
            "active_workflows": active_workflows,
        }

    def start_infra(self):
        """Start Shannon's Temporal docker-compose."""
        if not self._shannon_available():
            return {"success": False, "error": "Shannon not found"}
        try:
            proc = subprocess.Popen(
                [self.shannon_cli, "start-infra"],
                cwd=str(SHANNON_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            out, _ = proc.communicate(timeout=60)
            return {"success": proc.returncode == 0, "output": out}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Config file listing ───────────────────

    def list_configs(self):
        """List available YAML engagement configs."""
        configs_dir = SHANNON_ROOT / "apps" / "worker" / "configs"
        if not configs_dir.exists():
            return []
        configs = []
        for f in sorted(configs_dir.glob("*.yaml")):
            configs.append({"name": f.stem, "path": str(f)})
        return configs

    # ── Scan lifecycle ────────────────────────

    def start_scan(self, target, workspace=None, config_path=None):
        """Launch a new Shannon scan."""
        if not self._shannon_available():
            return {"success": False, "error": f"Shannon CLI not found at {SHANNON_ROOT}"}

        if not target:
            return {"success": False, "error": "Target URL required"}

        workspace = workspace or f"scan-{int(time.time())}"
        scan_id = str(uuid.uuid4())[:8]

        scan = ShannonScan(scan_id, target, workspace, config_path)

        # Derive repo name from workspace
        repo_name = re.sub(r"[^a-zA-Z0-9_-]", "-", workspace.lower())
        repo_path = SHANNON_ROOT / "repos" / repo_name

        # Ensure repo directory exists with git init
        if not (repo_path / ".git").exists():
            repo_path.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init"], cwd=str(repo_path), capture_output=True)
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "init"],
                cwd=str(repo_path),
                capture_output=True,
                env={**os.environ, "GIT_AUTHOR_NAME": "zwanski", "GIT_AUTHOR_EMAIL": "agent@localhost",
                     "GIT_COMMITTER_NAME": "zwanski", "GIT_COMMITTER_EMAIL": "agent@localhost"},
            )

        with self._lock:
            self._scans[scan_id] = scan
            self._save_scans()

        # Launch in background thread
        t = threading.Thread(
            target=self._run_scan,
            args=(scan, repo_name, config_path),
            daemon=True,
        )
        t.start()

        return {"success": True, "scan": scan.to_dict()}

    def _run_scan(self, scan: ShannonScan, repo_name: str, config_path: str | None):
        """Background thread: run the Shannon CLI and stream logs."""
        cmd = [
            self.shannon_cli, "start",
            "-u", scan.target,
            "-r", repo_name,
            "-w", scan.workspace,
        ]
        if config_path:
            cmd += ["-c", config_path]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(SHANNON_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            scan._process = proc
            scan.status = "running"
            self._update_and_emit(scan)

            for line in proc.stdout:
                line = line.rstrip()
                # Extract workflow ID from CLI output
                if "baloise" in line.lower() or "_shannon-" in line:
                    m = re.search(r"workflows/(\S+)", line)
                    if m and not scan.workflow_id:
                        scan.workflow_id = m.group(1).split("?")[0]

                self._emit("shannon_log", {
                    "scan_id": scan.scan_id,
                    "workspace": scan.workspace,
                    "line": line,
                })

            proc.wait()

            if proc.returncode == 0:
                scan.status = "completed"
            else:
                scan.status = "failed"

        except Exception as e:
            scan.status = "failed"
            scan.error = str(e)

        scan.completed_at = datetime.now(timezone.utc).isoformat()

        # Try to locate the final report
        report_candidates = [
            SHANNON_ROOT / "workspaces" / scan.workspace / ".shannon" / "deliverables" / "comprehensive_security_assessment_report.md",
            SHANNON_ROOT / "workspaces" / scan.workspace / "comprehensive_security_assessment_report.md",
        ]
        for path in report_candidates:
            if path.exists():
                scan.report_path = str(path)
                break

        self._update_and_emit(scan)

    def stop_scan(self, scan_id):
        """Stop a running scan."""
        scan = self._scans.get(scan_id)
        if not scan:
            return {"success": False, "error": "Scan not found"}
        if scan._process:
            try:
                scan._process.terminate()
            except Exception:
                pass
        scan.status = "stopped"
        scan.completed_at = datetime.now(timezone.utc).isoformat()
        self._update_and_emit(scan)
        return {"success": True}

    def delete_scan(self, scan_id):
        with self._lock:
            if scan_id in self._scans:
                del self._scans[scan_id]
                self._save_scans()
                return True
        return False

    # ── Temporal workflow state polling ───────

    def sync_from_temporal(self, scan_id):
        """Pull latest workflow state from Temporal REST API."""
        scan = self._scans.get(scan_id)
        if not scan or not scan.workflow_id:
            return

        try:
            r = requests.get(
                f"{TEMPORAL_API}/namespaces/default/workflows/{scan.workflow_id}",
                timeout=5,
            )
            if r.status_code != 200:
                return
            wf = r.json()
            status = wf.get("workflowExecutionInfo", {}).get("status", "")
            if "RUNNING" in status:
                scan.status = "running"
            elif "COMPLETED" in status:
                scan.status = "completed"
            elif "FAILED" in status or "TERMINATED" in status:
                scan.status = "failed"
        except Exception:
            pass

        # Also parse the workflow.log for completed agents
        self._parse_workflow_log(scan)
        self._update_and_emit(scan)

    def _parse_workflow_log(self, scan: ShannonScan):
        """Parse Shannon's workflow.log to extract agent completion status."""
        log_path = SHANNON_ROOT / "workspaces" / scan.workspace / "workflow.log"
        if not log_path.exists():
            return

        try:
            text = log_path.read_text(errors="replace")
        except Exception:
            return

        # Extract completed agents from log lines like "Agent pre-recon completed"
        completed = set(scan.completed_agents)
        for agent in ALL_AGENTS:
            if re.search(rf"\b{re.escape(agent)}\b.*complet", text, re.I):
                completed.add(agent)

        scan.completed_agents = [a for a in ALL_AGENTS if a in completed]

        # Extract current phase/agent
        phase_match = re.findall(r"Phase transition.*?→.*?(\w[\w-]+)", text)
        if phase_match:
            scan.current_phase = phase_match[-1]

        # Extract error
        err_match = re.search(r"Error:\s+(.+?)(?:\n|$)", text)
        if err_match and scan.status == "failed":
            scan.error = err_match.group(1).strip()

        # Extract cost
        cost_match = re.search(r"Total Cost:\s+\$([0-9.]+)", text)
        if cost_match:
            scan.cost_usd = float(cost_match.group(1))

        # Find report
        if scan.status == "completed" and not scan.report_path:
            deliverables = SHANNON_ROOT / "repos" / re.sub(r"[^a-zA-Z0-9_-]", "-", scan.workspace.lower()) / ".shannon" / "deliverables"
            report = deliverables / "comprehensive_security_assessment_report.md"
            if report.exists():
                scan.report_path = str(report)

    # ── Log retrieval ─────────────────────────

    def get_logs(self, workspace, lines=100):
        """Return recent lines from Shannon's workflow log."""
        log_path = SHANNON_ROOT / "workspaces" / workspace / "workflow.log"
        if not log_path.exists():
            return []
        try:
            text = log_path.read_text(errors="replace")
            return text.splitlines()[-lines:]
        except Exception:
            return []

    def get_report(self, workspace):
        """Return the final markdown report for a workspace."""
        # Check multiple possible locations
        candidates = [
            SHANNON_ROOT / "repos" / re.sub(r"[^a-zA-Z0-9_-]", "-", workspace.lower()) / ".shannon" / "deliverables" / "comprehensive_security_assessment_report.md",
            SHANNON_ROOT / "workspaces" / workspace / "comprehensive_security_assessment_report.md",
        ]
        for path in candidates:
            if path.exists():
                try:
                    return path.read_text(errors="replace")
                except Exception:
                    pass
        return None

    def get_deliverables(self, workspace):
        """List deliverable files for a workspace."""
        repo_name = re.sub(r"[^a-zA-Z0-9_-]", "-", workspace.lower())
        deliverables_dir = SHANNON_ROOT / "repos" / repo_name / ".shannon" / "deliverables"
        if not deliverables_dir.exists():
            return []
        files = []
        for f in sorted(deliverables_dir.glob("*.md")):
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "path": str(f),
            })
        return files

    # ── Scan listing ─────────────────────────

    def list_scans(self):
        # Sync running scans with Temporal before returning
        for scan in self._scans.values():
            if scan.status in ("running", "starting") and scan.workflow_id:
                self._parse_workflow_log(scan)
        return [s.to_dict() for s in sorted(
            self._scans.values(),
            key=lambda s: s.started_at or "",
            reverse=True,
        )]

    def get_scan(self, scan_id):
        scan = self._scans.get(scan_id)
        if not scan:
            return None
        self._parse_workflow_log(scan)
        return scan.to_dict()

    def get_stats(self):
        scans = list(self._scans.values())
        return {
            "total": len(scans),
            "running": sum(1 for s in scans if s.status == "running"),
            "completed": sum(1 for s in scans if s.status == "completed"),
            "failed": sum(1 for s in scans if s.status == "failed"),
            "total_cost_usd": round(sum(s.cost_usd for s in scans), 4),
        }

    # ── Internal helpers ──────────────────────

    def _update_and_emit(self, scan: ShannonScan):
        with self._lock:
            self._save_scans()
        self._emit("shannon_scan_update", scan.to_dict())

    # ── Background poller ─────────────────────

    def start_poller(self):
        """Poll running scans every 10s to sync Temporal state."""
        def _poll():
            while True:
                time.sleep(10)
                for scan in list(self._scans.values()):
                    if scan.status in ("running", "starting"):
                        self._parse_workflow_log(scan)
                        self._update_and_emit(scan)
        t = threading.Thread(target=_poll, daemon=True)
        t.start()


shannon_manager = ShannonManager()
