#!/usr/bin/env python3
"""
Port Scanner Dashboard - Real-time Port Scanning with Visual Attack Surface
Integrates nmap, masscan, and rustscan for comprehensive port discovery.
"""
import json
import re
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


class PortScanResult:
    """Represents a port scan result."""
    
    def __init__(self, target: str, scanner: str):
        self.scan_id = f"scan-{int(time.time())}"
        self.target = target
        self.scanner = scanner
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at = None
        self.ports: List[Dict[str, Any]] = []
        self.total_ports = 0
        self.open_ports = 0
        self.services: Dict[str, int] = {}
        self.output = ""
        self.error = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "target": self.target,
            "scanner": self.scanner,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "ports": self.ports,
            "total_ports": self.total_ports,
            "open_ports": self.open_ports,
            "services": self.services,
            "output": self.output,
            "error": self.error
        }


class PortScannerDashboard:
    """Real-time port scanning dashboard."""
    
    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file or Path(__file__).parent / "port_scans.json"
        self.scans: Dict[str, PortScanResult] = {}
        self.lock = threading.Lock()
        self._load_scans()
        
        # Check available scanners
        self.nmap_available = shutil.which("nmap") is not None
        self.masscan_available = shutil.which("masscan") is not None
        self.rustscan_available = shutil.which("rustscan") is not None
    
    def _load_scans(self):
        """Load saved scans."""
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text())
                # Only load completed scans
                for item in data:
                    if item.get("status") == "completed":
                        scan = PortScanResult(item["target"], item["scanner"])
                        scan.scan_id = item["scan_id"]
                        scan.status = item["status"]
                        scan.started_at = item["started_at"]
                        scan.completed_at = item["completed_at"]
                        scan.ports = item.get("ports", [])
                        scan.total_ports = item.get("total_ports", 0)
                        scan.open_ports = item.get("open_ports", 0)
                        scan.services = item.get("services", {})
                        scan.output = item.get("output", "")
                        self.scans[scan.scan_id] = scan
            except Exception as e:
                print(f"Failed to load scans: {e}")
    
    def _save_scans(self):
        """Save scans to storage."""
        try:
            data = [s.to_dict() for s in self.scans.values()]
            self.storage_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Failed to save scans: {e}")
    
    def start_nmap_scan(
        self,
        target: str,
        ports: str = "1-65535",
        aggressive: bool = False,
        service_detection: bool = True
    ) -> Dict[str, Any]:
        """Start nmap scan."""
        if not self.nmap_available:
            return {"error": "nmap not available", "success": False}
        
        scan = PortScanResult(target, "nmap")
        
        # Build nmap command
        cmd = ["nmap", "-p", ports]
        
        if service_detection:
            cmd.append("-sV")
        
        if aggressive:
            cmd.extend(["-A", "-T4"])
        else:
            cmd.append("-T3")
        
        cmd.extend(["-oX", "-", target])
        
        # Start scan in background thread
        thread = threading.Thread(
            target=self._run_nmap_scan,
            args=(scan, cmd)
        )
        thread.daemon = True
        thread.start()
        
        with self.lock:
            self.scans[scan.scan_id] = scan
        
        return {
            "success": True,
            "scan_id": scan.scan_id,
            "target": target,
            "scanner": "nmap"
        }
    
    def _run_nmap_scan(self, scan: PortScanResult, cmd: List[str]):
        """Run nmap scan in background."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour max
            )
            
            scan.output = result.stdout
            
            # Parse XML output
            self._parse_nmap_output(scan, result.stdout)
            
            scan.status = "completed"
            scan.completed_at = datetime.now(timezone.utc).isoformat()
            
        except subprocess.TimeoutExpired:
            scan.status = "timeout"
            scan.error = "Scan timeout after 1 hour"
        except Exception as e:
            scan.status = "failed"
            scan.error = str(e)
        
        self._save_scans()
    
    def _parse_nmap_output(self, scan: PortScanResult, output: str):
        """Parse nmap XML output."""
        # Simple regex parsing for ports
        port_pattern = r'<port protocol="(\w+)" portid="(\d+)"><state state="(\w+)"'
        service_pattern = r'<service name="([^"]+)"'
        
        for match in re.finditer(port_pattern, output):
            protocol, port, state = match.groups()
            
            if state == "open":
                port_info = {
                    "port": int(port),
                    "protocol": protocol,
                    "state": state,
                    "service": None
                }
                
                # Try to find service info
                service_match = re.search(service_pattern, output[match.end():match.end()+200])
                if service_match:
                    service_name = service_match.group(1)
                    port_info["service"] = service_name
                    scan.services[service_name] = scan.services.get(service_name, 0) + 1
                
                scan.ports.append(port_info)
                scan.open_ports += 1
        
        scan.total_ports = len(scan.ports)
    
    def start_masscan_scan(
        self,
        target: str,
        ports: str = "0-65535",
        rate: int = 10000
    ) -> Dict[str, Any]:
        """Start masscan (fast) scan."""
        if not self.masscan_available:
            return {"error": "masscan not available", "success": False}
        
        scan = PortScanResult(target, "masscan")
        
        # Build masscan command
        cmd = [
            "masscan",
            target,
            "-p", ports,
            "--rate", str(rate),
            "-oJ", "-"
        ]
        
        # Start scan in background thread
        thread = threading.Thread(
            target=self._run_masscan_scan,
            args=(scan, cmd)
        )
        thread.daemon = True
        thread.start()
        
        with self.lock:
            self.scans[scan.scan_id] = scan
        
        return {
            "success": True,
            "scan_id": scan.scan_id,
            "target": target,
            "scanner": "masscan"
        }
    
    def _run_masscan_scan(self, scan: PortScanResult, cmd: List[str]):
        """Run masscan in background."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes max
            )
            
            scan.output = result.stdout
            
            # Parse JSON output
            self._parse_masscan_output(scan, result.stdout)
            
            scan.status = "completed"
            scan.completed_at = datetime.now(timezone.utc).isoformat()
            
        except subprocess.TimeoutExpired:
            scan.status = "timeout"
            scan.error = "Scan timeout after 30 minutes"
        except Exception as e:
            scan.status = "failed"
            scan.error = str(e)
        
        self._save_scans()
    
    def _parse_masscan_output(self, scan: PortScanResult, output: str):
        """Parse masscan JSON output."""
        try:
            # Masscan outputs one JSON object per line
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    
                    if "ports" in data:
                        for port_data in data["ports"]:
                            port_info = {
                                "port": port_data.get("port"),
                                "protocol": port_data.get("proto", "tcp"),
                                "state": "open",
                                "service": None
                            }
                            
                            scan.ports.append(port_info)
                            scan.open_ports += 1
                except json.JSONDecodeError:
                    continue
            
            scan.total_ports = len(scan.ports)
        except Exception as e:
            scan.error = f"Parse error: {str(e)}"
    
    def start_rustscan_scan(
        self,
        target: str,
        ports: Optional[str] = None,
        fast: bool = True
    ) -> Dict[str, Any]:
        """Start rustscan (fastest) scan."""
        if not self.rustscan_available:
            return {"error": "rustscan not available", "success": False}
        
        scan = PortScanResult(target, "rustscan")
        
        # Build rustscan command
        cmd = ["rustscan", "-a", target]
        
        if ports:
            cmd.extend(["-p", ports])
        
        if fast:
            cmd.extend(["-b", "10000"])  # 10k batch size
        
        cmd.extend(["--", "-sV"])  # Pass to nmap for service detection
        
        # Start scan in background thread
        thread = threading.Thread(
            target=self._run_rustscan_scan,
            args=(scan, cmd)
        )
        thread.daemon = True
        thread.start()
        
        with self.lock:
            self.scans[scan.scan_id] = scan
        
        return {
            "success": True,
            "scan_id": scan.scan_id,
            "target": target,
            "scanner": "rustscan"
        }
    
    def _run_rustscan_scan(self, scan: PortScanResult, cmd: List[str]):
        """Run rustscan in background."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes max
            )
            
            scan.output = result.stdout
            
            # Parse rustscan output
            self._parse_rustscan_output(scan, result.stdout)
            
            scan.status = "completed"
            scan.completed_at = datetime.now(timezone.utc).isoformat()
            
        except subprocess.TimeoutExpired:
            scan.status = "timeout"
            scan.error = "Scan timeout after 30 minutes"
        except Exception as e:
            scan.status = "failed"
            scan.error = str(e)
        
        self._save_scans()
    
    def _parse_rustscan_output(self, scan: PortScanResult, output: str):
        """Parse rustscan output."""
        # Rustscan shows ports in format: Open 80
        port_pattern = r'Open\s+(\d+)'
        
        for match in re.finditer(port_pattern, output):
            port = int(match.group(1))
            
            port_info = {
                "port": port,
                "protocol": "tcp",
                "state": "open",
                "service": None
            }
            
            scan.ports.append(port_info)
            scan.open_ports += 1
        
        scan.total_ports = len(scan.ports)
    
    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get scan results."""
        if scan_id in self.scans:
            return self.scans[scan_id].to_dict()
        return None
    
    def list_scans(self, target: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all scans."""
        scans = list(self.scans.values())
        
        if target:
            scans = [s for s in scans if target.lower() in s.target.lower()]
        
        return [s.to_dict() for s in scans]
    
    def delete_scan(self, scan_id: str) -> bool:
        """Delete a scan."""
        if scan_id in self.scans:
            del self.scans[scan_id]
            self._save_scans()
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scanning statistics."""
        total = len(self.scans)
        completed = sum(1 for s in self.scans.values() if s.status == "completed")
        running = sum(1 for s in self.scans.values() if s.status == "running")
        failed = sum(1 for s in self.scans.values() if s.status == "failed")
        
        total_open_ports = sum(s.open_ports for s in self.scans.values())
        
        # Aggregate services
        all_services = {}
        for scan in self.scans.values():
            for service, count in scan.services.items():
                all_services[service] = all_services.get(service, 0) + count
        
        return {
            "total_scans": total,
            "completed_scans": completed,
            "running_scans": running,
            "failed_scans": failed,
            "total_open_ports": total_open_ports,
            "top_services": dict(sorted(all_services.items(), key=lambda x: x[1], reverse=True)[:10]),
            "scanners_available": {
                "nmap": self.nmap_available,
                "masscan": self.masscan_available,
                "rustscan": self.rustscan_available
            }
        }


# Global instance
port_scanner = PortScannerDashboard()
