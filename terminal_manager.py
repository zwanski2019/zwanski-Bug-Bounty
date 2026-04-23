#!/usr/bin/env python3
"""
Multi-Terminal Manager - Unlimited Terminal Sessions
Manages multiple tmux/screen sessions with full control.
"""
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


class TerminalSession:
    """Represents a single terminal session."""
    
    def __init__(self, session_id: str, name: str, command: Optional[str] = None):
        self.session_id = session_id
        self.name = name
        self.command = command or "bash"
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_activity = self.created_at
        self.panes = []
        self.status = "active"
        self.tmux_session_name = f"zwanski-{session_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "command": self.command,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "panes": self.panes,
            "status": self.status,
            "tmux_session_name": self.tmux_session_name
        }


class MultiTerminalManager:
    """Manage unlimited terminal sessions with tmux backend."""
    
    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file or Path(__file__).parent / "terminals.json"
        self.sessions: Dict[str, TerminalSession] = {}
        self.tmux_available = self._check_tmux()
        self._load_sessions()
    
    def _check_tmux(self) -> bool:
        """Check if tmux is available."""
        try:
            result = subprocess.run(
                ["which", "tmux"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    def _load_sessions(self):
        """Load saved sessions."""
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text())
                for item in data:
                    session = TerminalSession(
                        item["session_id"],
                        item["name"],
                        item.get("command")
                    )
                    session.created_at = item["created_at"]
                    session.last_activity = item["last_activity"]
                    session.panes = item.get("panes", [])
                    session.status = item.get("status", "active")
                    self.sessions[session.session_id] = session
            except Exception as e:
                print(f"Failed to load sessions: {e}")
    
    def _save_sessions(self):
        """Save sessions to storage."""
        try:
            data = [s.to_dict() for s in self.sessions.values()]
            self.storage_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Failed to save sessions: {e}")
    
    def create_session(self, name: str, command: Optional[str] = None) -> Dict[str, Any]:
        """Create a new terminal session."""
        if not self.tmux_available:
            return {"error": "tmux not available", "success": False}
        
        session_id = f"term-{int(time.time())}-{len(self.sessions)}"
        session = TerminalSession(session_id, name, command)
        
        try:
            # Create tmux session
            cmd = command or "bash"
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", session.tmux_session_name, cmd],
                check=True,
                timeout=5
            )
            
            # Get pane info
            pane_info = subprocess.run(
                ["tmux", "list-panes", "-t", session.tmux_session_name, "-F", "#{pane_id}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if pane_info.returncode == 0:
                session.panes = pane_info.stdout.strip().split("\n")
            
            self.sessions[session_id] = session
            self._save_sessions()
            
            return {
                "success": True,
                "session": session.to_dict()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        # Update status from tmux
        self._sync_tmux_status()
        return [s.to_dict() for s in self.sessions.values()]
    
    def _sync_tmux_status(self):
        """Sync session status with tmux."""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                active_sessions = set(result.stdout.strip().split("\n"))
                
                for session in self.sessions.values():
                    if session.tmux_session_name in active_sessions:
                        session.status = "active"
                    else:
                        session.status = "closed"
        except:
            pass
    
    def get_session_output(self, session_id: str, lines: int = 100) -> Dict[str, Any]:
        """Get output from a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found", "success": False}
        
        session = self.sessions[session_id]
        
        try:
            # Capture pane content
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", session.tmux_session_name, "-p", "-S", f"-{lines}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                session.last_activity = datetime.now(timezone.utc).isoformat()
                self._save_sessions()
                
                return {
                    "success": True,
                    "output": result.stdout,
                    "session_id": session_id
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to capture output"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_command(self, session_id: str, command: str) -> Dict[str, Any]:
        """Send command to a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found", "success": False}
        
        session = self.sessions[session_id]
        
        try:
            # Send keys to tmux session
            subprocess.run(
                ["tmux", "send-keys", "-t", session.tmux_session_name, command, "Enter"],
                check=True,
                timeout=5
            )
            
            session.last_activity = datetime.now(timezone.utc).isoformat()
            self._save_sessions()
            
            return {
                "success": True,
                "session_id": session_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def split_pane(self, session_id: str, vertical: bool = True) -> Dict[str, Any]:
        """Split a pane in the session."""
        if session_id not in self.sessions:
            return {"error": "Session not found", "success": False}
        
        session = self.sessions[session_id]
        
        try:
            split_flag = "-h" if vertical else "-v"
            subprocess.run(
                ["tmux", "split-window", "-t", session.tmux_session_name, split_flag],
                check=True,
                timeout=5
            )
            
            # Update panes list
            pane_info = subprocess.run(
                ["tmux", "list-panes", "-t", session.tmux_session_name, "-F", "#{pane_id}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if pane_info.returncode == 0:
                session.panes = pane_info.stdout.strip().split("\n")
            
            self._save_sessions()
            
            return {
                "success": True,
                "panes": session.panes
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close a terminal session."""
        if session_id not in self.sessions:
            return {"error": "Session not found", "success": False}
        
        session = self.sessions[session_id]
        
        try:
            # Kill tmux session
            subprocess.run(
                ["tmux", "kill-session", "-t", session.tmux_session_name],
                timeout=5
            )
            
            session.status = "closed"
            self._save_sessions()
            
            return {
                "success": True,
                "session_id": session_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def save_session_history(self, session_id: str) -> Dict[str, Any]:
        """Save entire session history."""
        if session_id not in self.sessions:
            return {"error": "Session not found", "success": False}
        
        session = self.sessions[session_id]
        history_file = Path(__file__).parent / f"terminal_history_{session_id}.txt"
        
        try:
            # Capture full scrollback
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", session.tmux_session_name, "-p", "-S", "-"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                history_file.write_text(result.stdout)
                
                return {
                    "success": True,
                    "file": str(history_file),
                    "session_id": session_id
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to capture history"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get terminal statistics."""
        self._sync_tmux_status()
        
        active = sum(1 for s in self.sessions.values() if s.status == "active")
        closed = sum(1 for s in self.sessions.values() if s.status == "closed")
        total_panes = sum(len(s.panes) for s in self.sessions.values())
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active,
            "closed_sessions": closed,
            "total_panes": total_panes,
            "tmux_available": self.tmux_available
        }


# Global instance
terminal_manager = MultiTerminalManager()
