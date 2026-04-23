#!/usr/bin/env python3
"""
Scope Management Module
Manages bug bounty program scopes, tracks targets, and validates endpoints.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse


class ScopeManager:
    """Manage bug bounty program scopes."""
    
    def __init__(self, storage_file: Optional[Path] = None):
        self.storage_file = storage_file or Path(__file__).parent / "scopes.json"
        self.scopes = self._load_scopes()
    
    def _load_scopes(self) -> Dict[str, Any]:
        """Load scopes from storage."""
        if self.storage_file.exists():
            try:
                return json.loads(self.storage_file.read_text())
            except Exception as e:
                print(f"Failed to load scopes: {e}")
                return {}
        return {}
    
    def _save_scopes(self):
        """Save scopes to storage."""
        try:
            self.storage_file.write_text(json.dumps(self.scopes, indent=2))
        except Exception as e:
            print(f"Failed to save scopes: {e}")
    
    def add_program(self, program: Dict[str, Any]) -> str:
        """Add a new bug bounty program."""
        program_id = program.get("id") or f"prog-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        program["id"] = program_id
        program["created_at"] = datetime.now(timezone.utc).isoformat()
        program["updated_at"] = program["created_at"]
        
        # Ensure required fields
        if "name" not in program:
            program["name"] = program_id
        if "platform" not in program:
            program["platform"] = "custom"
        if "in_scope" not in program:
            program["in_scope"] = []
        if "out_of_scope" not in program:
            program["out_of_scope"] = []
        
        self.scopes[program_id] = program
        self._save_scopes()
        
        return program_id
    
    def update_program(self, program_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing program."""
        if program_id in self.scopes:
            self.scopes[program_id].update(updates)
            self.scopes[program_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_scopes()
            return True
        return False
    
    def delete_program(self, program_id: str) -> bool:
        """Delete a program."""
        if program_id in self.scopes:
            del self.scopes[program_id]
            self._save_scopes()
            return True
        return False
    
    def get_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific program."""
        return self.scopes.get(program_id)
    
    def list_programs(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List programs with optional filters."""
        programs = list(self.scopes.values())
        
        if filters:
            if "platform" in filters:
                programs = [p for p in programs if p.get("platform") == filters["platform"]]
            if "active" in filters:
                programs = [p for p in programs if p.get("active", True) == filters["active"]]
            if "search" in filters:
                search = filters["search"].lower()
                programs = [p for p in programs if search in p.get("name", "").lower()]
        
        return programs
    
    def check_in_scope(self, target: str, program_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if a target is in scope.
        
        Args:
            target: URL, domain, or IP to check
            program_id: Specific program to check (if None, check all)
            
        Returns:
            Dict with in_scope status and matching programs
        """
        parsed = urlparse(target if "://" in target else f"http://{target}")
        host = parsed.netloc or parsed.path.split("/")[0]
        
        # Extract domain from host
        domain = host.split(":")[0] if ":" in host else host
        
        matching_programs = []
        in_scope = False
        out_of_scope = False
        
        programs_to_check = (
            [self.scopes[program_id]] if program_id and program_id in self.scopes
            else list(self.scopes.values())
        )
        
        for program in programs_to_check:
            if not program.get("active", True):
                continue
            
            # Check in-scope rules
            for scope_item in program.get("in_scope", []):
                if self._matches_scope_pattern(target, domain, scope_item):
                    in_scope = True
                    matching_programs.append({
                        "id": program["id"],
                        "name": program["name"],
                        "platform": program["platform"],
                        "scope_type": "in_scope",
                        "matched_pattern": scope_item
                    })
                    break
            
            # Check out-of-scope rules
            for scope_item in program.get("out_of_scope", []):
                if self._matches_scope_pattern(target, domain, scope_item):
                    out_of_scope = True
                    matching_programs.append({
                        "id": program["id"],
                        "name": program["name"],
                        "platform": program["platform"],
                        "scope_type": "out_of_scope",
                        "matched_pattern": scope_item
                    })
                    break
        
        return {
            "target": target,
            "in_scope": in_scope and not out_of_scope,
            "out_of_scope": out_of_scope,
            "matching_programs": matching_programs
        }
    
    def _matches_scope_pattern(self, target: str, domain: str, pattern: str) -> bool:
        """Check if target matches a scope pattern."""
        # Handle different pattern formats
        pattern_clean = pattern.strip()
        
        # Wildcard domain (*.example.com)
        if pattern_clean.startswith("*."):
            wildcard_domain = pattern_clean[2:]
            return domain.endswith(wildcard_domain)
        
        # Exact domain match
        if domain == pattern_clean:
            return True
        
        # Subdomain match (example.com matches *.example.com)
        if "." in domain:
            parent_domain = ".".join(domain.split(".")[1:])
            if parent_domain == pattern_clean:
                return True
        
        # CIDR range (basic IP check)
        if "/" in pattern_clean and domain.replace(".", "").isdigit():
            # Simple IP in range check (not full CIDR implementation)
            ip_prefix = pattern_clean.split("/")[0]
            if domain.startswith(ip_prefix.rsplit(".", 1)[0]):
                return True
        
        # Regex pattern
        if pattern_clean.startswith("regex:"):
            regex = pattern_clean[6:]
            try:
                if re.search(regex, target, re.IGNORECASE):
                    return True
            except re.error:
                pass
        
        # Direct URL match
        if pattern_clean in target:
            return True
        
        return False
    
    def bulk_add_scope(self, program_id: str, scope_items: List[str], scope_type: str = "in_scope") -> bool:
        """Add multiple scope items to a program."""
        if program_id not in self.scopes:
            return False
        
        if scope_type not in ["in_scope", "out_of_scope"]:
            scope_type = "in_scope"
        
        current_scope = self.scopes[program_id].get(scope_type, [])
        
        # Add unique items only
        for item in scope_items:
            item_clean = item.strip()
            if item_clean and item_clean not in current_scope:
                current_scope.append(item_clean)
        
        self.scopes[program_id][scope_type] = current_scope
        self.scopes[program_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._save_scopes()
        
        return True
    
    def parse_scope_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        Parse scope from text (HackerOne/Bugcrowd format).
        
        Returns:
            Dict with in_scope and out_of_scope lists
        """
        in_scope = []
        out_of_scope = []
        
        current_section = None
        
        for line in text.split("\n"):
            line = line.strip()
            
            # Section headers
            if re.match(r"in[- ]scope", line, re.IGNORECASE):
                current_section = "in_scope"
                continue
            elif re.match(r"out[- ]of[- ]scope", line, re.IGNORECASE):
                current_section = "out_of_scope"
                continue
            
            # Skip empty lines and comments
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            
            # Extract domain/URL patterns
            # Remove markdown bullets
            line = re.sub(r"^[-*+]\s+", "", line)
            
            # Extract from common formats
            # - https://example.com
            # - *.example.com
            # - example.com
            match = re.search(r"(?:https?://)?([*a-zA-Z0-9][-*.a-zA-Z0-9]*[a-zA-Z0-9])", line)
            if match:
                scope_item = match.group(0)
                
                if current_section == "in_scope":
                    if scope_item not in in_scope:
                        in_scope.append(scope_item)
                elif current_section == "out_of_scope":
                    if scope_item not in out_of_scope:
                        out_of_scope.append(scope_item)
        
        return {
            "in_scope": in_scope,
            "out_of_scope": out_of_scope
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scope statistics."""
        total_programs = len(self.scopes)
        active_programs = sum(1 for p in self.scopes.values() if p.get("active", True))
        
        by_platform = {}
        total_in_scope = 0
        total_out_of_scope = 0
        
        for program in self.scopes.values():
            platform = program.get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + 1
            
            total_in_scope += len(program.get("in_scope", []))
            total_out_of_scope += len(program.get("out_of_scope", []))
        
        return {
            "total_programs": total_programs,
            "active_programs": active_programs,
            "by_platform": by_platform,
            "total_in_scope_items": total_in_scope,
            "total_out_of_scope_items": total_out_of_scope
        }


# Global instance
scope_manager = ScopeManager()
