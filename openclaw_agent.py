#!/usr/bin/env python3
"""
OpenClaw Bug Bounty Agent - Mobile C2 for Automated Bug Hunting
Full integration with Telegram/WhatsApp/Discord for remote control.
"""
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


class BugBountyAgent:
    """OpenClaw-powered bug bounty automation agent."""
    
    def __init__(self):
        self.agent_id = f"agent-{int(time.time())}"
        self.status = "idle"
        self.current_target = None
        self.running_tasks: List[Dict[str, Any]] = []
        self.completed_tasks: List[Dict[str, Any]] = []
        self.findings: List[Dict[str, Any]] = []
        self.auto_mode = False
        self.telegram_enabled = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
        self.whatsapp_enabled = bool(os.getenv("WHATSAPP_SESSION_PATH"))
        self.discord_enabled = bool(os.getenv("DISCORD_BOT_TOKEN"))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "current_target": self.current_target,
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "findings": len(self.findings),
            "auto_mode": self.auto_mode,
            "integrations": {
                "telegram": self.telegram_enabled,
                "whatsapp": self.whatsapp_enabled,
                "discord": self.discord_enabled
            }
        }


class OpenClawBugBountyAgent:
    """Full OpenClaw integration for bug bounty automation."""
    
    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file or Path(__file__).parent / "openclaw_agents.json"
        self.agents: Dict[str, BugBountyAgent] = {}
        self.command_queue: List[Dict[str, Any]] = []
        self.results_queue: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self._load_agents()
        
        # Workflow presets
        self.workflows = {
            "full_recon": [
                {"tool": "subfinder", "desc": "Subdomain enumeration"},
                {"tool": "httpx", "desc": "Live host detection"},
                {"tool": "nuclei", "desc": "Vulnerability scanning"},
                {"tool": "katana", "desc": "Crawling and endpoint discovery"}
            ],
            "quick_scan": [
                {"tool": "subfinder", "desc": "Quick subdomain check"},
                {"tool": "httpx", "desc": "Live hosts"},
                {"tool": "nuclei", "args": ["-severity", "high,critical"], "desc": "High-severity only"}
            ],
            "deep_hunt": [
                {"tool": "amass", "args": ["enum", "-passive"], "desc": "Deep subdomain enum"},
                {"tool": "nmap", "desc": "Port scanning"},
                {"tool": "nuclei", "desc": "Full vulnerability scan"},
                {"tool": "sqlmap", "desc": "SQL injection testing"},
                {"tool": "dalfox", "desc": "XSS hunting"}
            ],
            "api_hunt": [
                {"tool": "katana", "desc": "API endpoint discovery"},
                {"tool": "arjun", "desc": "Parameter discovery"},
                {"tool": "ffuf", "desc": "API fuzzing"},
                {"tool": "nuclei", "args": ["-tags", "api"], "desc": "API-specific vulns"}
            ]
        }
    
    def _load_agents(self):
        """Load saved agents."""
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text())
                for item in data:
                    agent = BugBountyAgent()
                    agent.agent_id = item["agent_id"]
                    agent.status = item.get("status", "idle")
                    agent.current_target = item.get("current_target")
                    agent.completed_tasks = item.get("completed_tasks", [])
                    agent.findings = item.get("findings", [])
                    self.agents[agent.agent_id] = agent
            except Exception as e:
                print(f"Failed to load agents: {e}")
    
    def _save_agents(self):
        """Save agents to storage."""
        try:
            data = []
            for agent in self.agents.values():
                data.append({
                    "agent_id": agent.agent_id,
                    "status": agent.status,
                    "current_target": agent.current_target,
                    "completed_tasks": agent.completed_tasks,
                    "findings": agent.findings
                })
            self.storage_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Failed to save agents: {e}")
    
    def create_agent(self, auto_mode: bool = False) -> Dict[str, Any]:
        """Create a new bug bounty agent."""
        agent = BugBountyAgent()
        agent.auto_mode = auto_mode
        
        with self.lock:
            self.agents[agent.agent_id] = agent
        
        self._save_agents()
        
        return {
            "success": True,
            "agent": agent.to_dict()
        }
    
    def start_recon(
        self,
        agent_id: str,
        target: str,
        workflow: str = "full_recon",
        notify: bool = True
    ) -> Dict[str, Any]:
        """Start reconnaissance workflow."""
        if agent_id not in self.agents:
            return {"error": "Agent not found", "success": False}
        
        agent = self.agents[agent_id]
        
        if agent.status == "running":
            return {"error": "Agent already running", "success": False}
        
        agent.status = "running"
        agent.current_target = target
        
        # Get workflow steps
        steps = self.workflows.get(workflow, self.workflows["full_recon"])
        
        # Start workflow in background
        thread = threading.Thread(
            target=self._run_workflow,
            args=(agent, target, steps, notify)
        )
        thread.daemon = True
        thread.start()
        
        return {
            "success": True,
            "agent_id": agent_id,
            "target": target,
            "workflow": workflow,
            "steps": len(steps)
        }
    
    def _run_workflow(
        self,
        agent: BugBountyAgent,
        target: str,
        steps: List[Dict[str, Any]],
        notify: bool
    ):
        """Execute workflow steps."""
        for i, step in enumerate(steps, 1):
            tool = step["tool"]
            desc = step.get("desc", "")
            args = step.get("args", [])
            
            # Notify start
            if notify:
                self._send_notification(
                    f"🔍 Step {i}/{len(steps)}: {desc}",
                    f"Running {tool} on {target}"
                )
            
            task = {
                "tool": tool,
                "target": target,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "running"
            }
            
            agent.running_tasks.append(task)
            
            try:
                # Build command
                cmd = [tool]
                if tool in ["subfinder", "amass"]:
                    cmd.extend(["-d", target])
                elif tool == "httpx":
                    cmd.extend(["-l", "-"])  # Read from stdin
                elif tool == "nuclei":
                    cmd.extend(["-u", target] + args)
                elif tool == "nmap":
                    cmd.extend(["-p-", target])
                else:
                    cmd.extend([target] + args)
                
                # Execute
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=1800  # 30 min per tool
                )
                
                task["status"] = "completed"
                task["completed_at"] = datetime.now(timezone.utc).isoformat()
                task["output"] = result.stdout[:1000]  # Store first 1000 chars
                
                # Parse for findings
                self._parse_findings(agent, tool, result.stdout, target)
                
                agent.running_tasks.remove(task)
                agent.completed_tasks.append(task)
                
                # Notify completion
                if notify and agent.findings:
                    latest_findings = [f for f in agent.findings if f.get("tool") == tool]
                    if latest_findings:
                        self._send_notification(
                            f"✅ {tool} completed",
                            f"Found {len(latest_findings)} results"
                        )
                
            except subprocess.TimeoutExpired:
                task["status"] = "timeout"
                agent.running_tasks.remove(task)
                agent.completed_tasks.append(task)
            except Exception as e:
                task["status"] = "failed"
                task["error"] = str(e)
                agent.running_tasks.remove(task)
                agent.completed_tasks.append(task)
            
            # Small delay between steps
            time.sleep(2)
        
        agent.status = "idle"
        agent.current_target = None
        
        # Final notification
        if notify:
            self._send_notification(
                f"🎉 Recon complete: {target}",
                f"Total findings: {len(agent.findings)}\nCompleted: {len(agent.completed_tasks)}"
            )
        
        self._save_agents()
    
    def _parse_findings(
        self,
        agent: BugBountyAgent,
        tool: str,
        output: str,
        target: str
    ):
        """Parse tool output for findings."""
        findings = []
        
        if tool == "subfinder":
            # Each line is a subdomain
            for line in output.strip().split("\n"):
                if line.strip():
                    findings.append({
                        "type": "subdomain",
                        "value": line.strip(),
                        "tool": tool,
                        "target": target,
                        "found_at": datetime.now(timezone.utc).isoformat()
                    })
        
        elif tool == "nuclei":
            # Parse nuclei output (simplified)
            if "[" in output and "]" in output:
                findings.append({
                    "type": "vulnerability",
                    "value": "Potential vulnerability detected",
                    "tool": tool,
                    "target": target,
                    "found_at": datetime.now(timezone.utc).isoformat(),
                    "details": output[:500]
                })
        
        elif tool == "httpx":
            # Each line is a live host
            for line in output.strip().split("\n"):
                if line.strip() and line.startswith("http"):
                    findings.append({
                        "type": "live_host",
                        "value": line.strip(),
                        "tool": tool,
                        "target": target,
                        "found_at": datetime.now(timezone.utc).isoformat()
                    })
        
        agent.findings.extend(findings)
    
    def _send_notification(self, title: str, message: str):
        """Send notification via enabled channels."""
        # This would integrate with actual OpenClaw
        # For now, just log
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"[{timestamp}] {title}: {message}")
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent status."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            data = agent.to_dict()
            data["tasks"] = agent.running_tasks + agent.completed_tasks[-10:]  # Last 10
            data["recent_findings"] = agent.findings[-20:]  # Last 20
            return data
        return None
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents."""
        return [a.to_dict() for a in self.agents.values()]
    
    def stop_agent(self, agent_id: str) -> Dict[str, Any]:
        """Stop running agent."""
        if agent_id not in self.agents:
            return {"error": "Agent not found", "success": False}
        
        agent = self.agents[agent_id]
        agent.status = "stopped"
        agent.current_target = None
        agent.running_tasks = []
        
        self._save_agents()
        
        return {
            "success": True,
            "agent_id": agent_id
        }
    
    def get_workflows(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get available workflows."""
        return self.workflows
    
    def add_custom_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Add custom workflow."""
        self.workflows[name] = steps
        
        return {
            "success": True,
            "workflow": name,
            "steps": len(steps)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        total_agents = len(self.agents)
        running = sum(1 for a in self.agents.values() if a.status == "running")
        total_findings = sum(len(a.findings) for a in self.agents.values())
        total_tasks = sum(len(a.completed_tasks) for a in self.agents.values())
        
        # Finding types distribution
        finding_types = {}
        for agent in self.agents.values():
            for finding in agent.findings:
                ftype = finding.get("type", "unknown")
                finding_types[ftype] = finding_types.get(ftype, 0) + 1
        
        return {
            "total_agents": total_agents,
            "running_agents": running,
            "total_findings": total_findings,
            "total_tasks": total_tasks,
            "finding_types": finding_types,
            "available_workflows": list(self.workflows.keys()),
            "integrations": {
                "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
                "whatsapp": bool(os.getenv("WHATSAPP_SESSION_PATH")),
                "discord": bool(os.getenv("DISCORD_BOT_TOKEN"))
            }
        }


# Global instance
openclaw_agent = OpenClawBugBountyAgent()
