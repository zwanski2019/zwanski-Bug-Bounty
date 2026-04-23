#!/usr/bin/env python3
"""
Enhanced Reporting Module
CVSS calculator, finding tracking, and platform-specific templates.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


class CVSSCalculator:
    """CVSS 3.1 calculator for vulnerability scoring."""
    
    # Metric weights
    IMPACT_WEIGHTS = {
        "NONE": 0,
        "LOW": 0.22,
        "HIGH": 0.56
    }
    
    EXPLOITABILITY_WEIGHTS = {
        "NETWORK": 0.85,
        "ADJACENT": 0.62,
        "LOCAL": 0.55,
        "PHYSICAL": 0.2
    }
    
    COMPLEXITY_WEIGHTS = {
        "LOW": 0.77,
        "HIGH": 0.44
    }
    
    PRIVILEGES_WEIGHTS = {
        "NONE": 0.85,
        "LOW": 0.62,
        "HIGH": 0.27
    }
    
    USER_INTERACTION_WEIGHTS = {
        "NONE": 0.85,
        "REQUIRED": 0.62
    }
    
    SCOPE_MULTIPLIER = {
        "UNCHANGED": 1.0,
        "CHANGED": 1.08
    }
    
    def calculate(self, metrics: Dict[str, str]) -> Dict[str, Any]:
        """
        Calculate CVSS 3.1 score from metrics.
        
        Args:
            metrics: Dict with CVSS metric values
            
        Returns:
            Dict with base_score, severity, and vector string
        """
        try:
            # Extract metrics
            av = metrics.get("attack_vector", "NETWORK").upper()
            ac = metrics.get("attack_complexity", "LOW").upper()
            pr = metrics.get("privileges_required", "NONE").upper()
            ui = metrics.get("user_interaction", "NONE").upper()
            scope = metrics.get("scope", "UNCHANGED").upper()
            c = metrics.get("confidentiality", "NONE").upper()
            i = metrics.get("integrity", "NONE").upper()
            a = metrics.get("availability", "NONE").upper()
            
            # Calculate Impact Sub Score (ISS)
            iss = 1 - (
                (1 - self.IMPACT_WEIGHTS.get(c, 0)) *
                (1 - self.IMPACT_WEIGHTS.get(i, 0)) *
                (1 - self.IMPACT_WEIGHTS.get(a, 0))
            )
            
            # Calculate Impact
            if scope == "UNCHANGED":
                impact = 6.42 * iss
            else:
                impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
            
            # Calculate Exploitability
            exploitability = (
                8.22 *
                self.EXPLOITABILITY_WEIGHTS.get(av, 0.85) *
                self.COMPLEXITY_WEIGHTS.get(ac, 0.77) *
                self.PRIVILEGES_WEIGHTS.get(pr, 0.85) *
                self.USER_INTERACTION_WEIGHTS.get(ui, 0.85)
            )
            
            # Calculate Base Score
            if impact <= 0:
                base_score = 0.0
            else:
                if scope == "UNCHANGED":
                    base_score = min(impact + exploitability, 10.0)
                else:
                    base_score = min(1.08 * (impact + exploitability), 10.0)
            
            # Round up to 1 decimal
            base_score = round(base_score, 1)
            
            # Determine severity
            if base_score == 0:
                severity = "NONE"
            elif base_score < 4.0:
                severity = "LOW"
            elif base_score < 7.0:
                severity = "MEDIUM"
            elif base_score < 9.0:
                severity = "HIGH"
            else:
                severity = "CRITICAL"
            
            # Generate vector string
            vector = f"CVSS:3.1/AV:{av[0]}/AC:{ac[0]}/PR:{pr[0]}/UI:{ui[0]}/S:{scope[0]}/C:{c[0]}/I:{i[0]}/A:{a[0]}"
            
            return {
                "base_score": base_score,
                "severity": severity,
                "vector_string": vector,
                "metrics": {
                    "attack_vector": av,
                    "attack_complexity": ac,
                    "privileges_required": pr,
                    "user_interaction": ui,
                    "scope": scope,
                    "confidentiality": c,
                    "integrity": i,
                    "availability": a
                },
                "sub_scores": {
                    "impact": round(impact, 2),
                    "exploitability": round(exploitability, 2)
                }
            }
        except Exception as e:
            return {
                "error": str(e),
                "base_score": 0.0,
                "severity": "UNKNOWN"
            }


class FindingTracker:
    """Track and manage bug bounty findings."""
    
    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file or Path(__file__).parent / "findings.json"
        self.findings = self._load_findings()
        self.cvss = CVSSCalculator()
    
    def _load_findings(self) -> List[Dict[str, Any]]:
        """Load findings from storage."""
        if self.storage_file.exists():
            try:
                return json.loads(self.storage_file.read_text())
            except Exception as e:
                print(f"Failed to load findings: {e}")
                return []
        return []
    
    def _save_findings(self):
        """Save findings to storage."""
        try:
            self.storage_file.write_text(json.dumps(self.findings, indent=2))
        except Exception as e:
            print(f"Failed to save findings: {e}")
    
    def add_finding(self, finding: Dict[str, Any]) -> str:
        """Add a new finding."""
        finding_id = f"ZWBB-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{len(self.findings) + 1:04d}"
        
        # Calculate CVSS if metrics provided
        if "cvss_metrics" in finding:
            cvss_result = self.cvss.calculate(finding["cvss_metrics"])
            finding["cvss"] = cvss_result
        
        finding["id"] = finding_id
        finding["created_at"] = datetime.now(timezone.utc).isoformat()
        finding["updated_at"] = finding["created_at"]
        finding["status"] = finding.get("status", "new")
        
        self.findings.append(finding)
        self._save_findings()
        
        return finding_id
    
    def update_finding(self, finding_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing finding."""
        for finding in self.findings:
            if finding["id"] == finding_id:
                # Recalculate CVSS if metrics updated
                if "cvss_metrics" in updates:
                    cvss_result = self.cvss.calculate(updates["cvss_metrics"])
                    updates["cvss"] = cvss_result
                
                finding.update(updates)
                finding["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_findings()
                return True
        return False
    
    def get_finding(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific finding."""
        for finding in self.findings:
            if finding["id"] == finding_id:
                return finding
        return None
    
    def list_findings(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List findings with optional filters."""
        results = self.findings
        
        if filters:
            if "status" in filters:
                results = [f for f in results if f.get("status") == filters["status"]]
            if "severity" in filters:
                results = [f for f in results if f.get("cvss", {}).get("severity") == filters["severity"]]
            if "target" in filters:
                results = [f for f in results if filters["target"].lower() in f.get("target", "").lower()]
            if "platform" in filters:
                results = [f for f in results if f.get("platform") == filters["platform"]]
        
        return results
    
    def delete_finding(self, finding_id: str) -> bool:
        """Delete a finding."""
        initial_len = len(self.findings)
        self.findings = [f for f in self.findings if f["id"] != finding_id]
        
        if len(self.findings) < initial_len:
            self._save_findings()
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get finding statistics."""
        total = len(self.findings)
        
        by_severity = {}
        by_status = {}
        by_platform = {}
        
        for finding in self.findings:
            # Count by severity
            severity = finding.get("cvss", {}).get("severity", "UNKNOWN")
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Count by status
            status = finding.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            
            # Count by platform
            platform = finding.get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + 1
        
        return {
            "total": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "by_platform": by_platform
        }


class ReportGenerator:
    """Generate platform-specific vulnerability reports."""
    
    PLATFORM_TEMPLATES = {
        "HackerOne": {
            "format": "markdown",
            "sections": ["summary", "steps", "impact", "remediation", "attachments"],
            "tone": "professional"
        },
        "Bugcrowd": {
            "format": "markdown",
            "sections": ["summary", "impact", "steps", "remediation", "cvss"],
            "tone": "concise"
        },
        "Synack": {
            "format": "markdown",
            "sections": ["summary", "steps", "technical_details", "impact", "remediation"],
            "tone": "technical"
        },
        "Intigriti": {
            "format": "markdown",
            "sections": ["summary", "impact", "proof_of_concept", "remediation"],
            "tone": "detailed"
        },
        "YesWeHack": {
            "format": "markdown",
            "sections": ["summary", "vulnerability_type", "steps", "impact", "remediation"],
            "tone": "structured"
        },
        "Bug Bounty Switzerland": {
            "format": "markdown",
            "sections": ["summary", "affected_component", "steps", "impact", "remediation", "cvss"],
            "tone": "formal"
        }
    }
    
    def generate_report(self, finding: Dict[str, Any], platform: str = "HackerOne") -> str:
        """Generate a platform-specific report."""
        template = self.PLATFORM_TEMPLATES.get(platform, self.PLATFORM_TEMPLATES["HackerOne"])
        
        report_parts = []
        
        # Title
        title = finding.get("title", "Vulnerability Report")
        report_parts.append(f"# {title}\n")
        
        # Summary
        if "summary" in template["sections"]:
            summary = finding.get("summary", finding.get("description", "No summary provided"))
            report_parts.append(f"## Summary\n\n{summary}\n")
        
        # CVSS Score (if available)
        if "cvss" in template["sections"] and "cvss" in finding:
            cvss = finding["cvss"]
            report_parts.append(f"## Severity\n\n")
            report_parts.append(f"**CVSS Score:** {cvss['base_score']} ({cvss['severity']})\n\n")
            report_parts.append(f"**Vector String:** `{cvss['vector_string']}`\n")
        
        # Impact
        if "impact" in template["sections"]:
            impact = finding.get("impact", "Impact assessment pending")
            report_parts.append(f"## Impact\n\n{impact}\n")
        
        # Steps to Reproduce
        if "steps" in template["sections"]:
            steps = finding.get("steps", finding.get("reproduction_steps", []))
            if isinstance(steps, list):
                report_parts.append("## Steps to Reproduce\n\n")
                for i, step in enumerate(steps, 1):
                    report_parts.append(f"{i}. {step}\n")
                report_parts.append("\n")
            else:
                report_parts.append(f"## Steps to Reproduce\n\n{steps}\n")
        
        # Technical Details / Proof of Concept
        if "technical_details" in template["sections"] or "proof_of_concept" in template["sections"]:
            poc = finding.get("proof_of_concept", finding.get("technical_details", ""))
            if poc:
                report_parts.append(f"## Proof of Concept\n\n{poc}\n")
        
        # Remediation
        if "remediation" in template["sections"]:
            remediation = finding.get("remediation", "Remediation recommendations to be provided")
            report_parts.append(f"## Remediation\n\n{remediation}\n")
        
        # Attachments
        if "attachments" in template["sections"]:
            attachments = finding.get("attachments", [])
            if attachments:
                report_parts.append("## Attachments\n\n")
                for attachment in attachments:
                    report_parts.append(f"- {attachment}\n")
                report_parts.append("\n")
        
        return "\n".join(report_parts)


# Global instances
cvss_calculator = CVSSCalculator()
finding_tracker = FindingTracker()
report_generator = ReportGenerator()
