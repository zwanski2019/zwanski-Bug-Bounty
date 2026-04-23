#!/usr/bin/env python3
"""
Version Management and Auto-Update System
Handles version checking, update notifications, and changelog display.
"""
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import requests

# Current version - UPDATE THIS ON EACH RELEASE
CURRENT_VERSION = "2.1.0"
VERSION_FILE = Path(__file__).parent / "VERSION"
REPO_OWNER = "zwanski2019"
REPO_NAME = "zwanski-Bug-Bounty"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
UPDATE_CHECK_INTERVAL = 3600  # Check every hour
CACHE_FILE = Path(__file__).parent / ".update_cache.json"


class VersionManager:
    """Manages version checking and update notifications."""
    
    def __init__(self):
        self.current_version = self._get_current_version()
        self.latest_version = None
        self.latest_release = None
        self.update_available = False
        self.checking = False
        self.last_check = None
        self.error = None
        self._load_cache()
        
    def _get_current_version(self) -> str:
        """Get current version from VERSION file or fallback to hardcoded."""
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text().strip()
        return CURRENT_VERSION
    
    def _load_cache(self):
        """Load cached update check results."""
        if CACHE_FILE.exists():
            try:
                cache = json.loads(CACHE_FILE.read_text())
                self.latest_version = cache.get("latest_version")
                self.latest_release = cache.get("latest_release")
                self.last_check = cache.get("last_check")
                self.update_available = cache.get("update_available", False)
            except Exception as e:
                print(f"Failed to load update cache: {e}")
    
    def _save_cache(self):
        """Save update check results to cache."""
        try:
            cache = {
                "latest_version": self.latest_version,
                "latest_release": self.latest_release,
                "last_check": self.last_check,
                "update_available": self.update_available
            }
            CACHE_FILE.write_text(json.dumps(cache, indent=2))
        except Exception as e:
            print(f"Failed to save update cache: {e}")
    
    def check_for_updates(self, force: bool = False) -> Dict[str, Any]:
        """
        Check GitHub for new releases.
        
        Args:
            force: Force check even if recently checked
            
        Returns:
            Dict with update status and details
        """
        # Avoid frequent checks unless forced
        if not force and self.last_check:
            elapsed = time.time() - self.last_check
            if elapsed < UPDATE_CHECK_INTERVAL:
                return self.get_status()
        
        self.checking = True
        self.error = None
        
        try:
            # Get latest release from GitHub
            response = requests.get(
                f"{GITHUB_API_URL}/releases/latest",
                timeout=10,
                headers={"Accept": "application/vnd.github.v3+json"}
            )
            
            if response.status_code == 404:
                # No releases yet
                self.latest_version = self.current_version
                self.latest_release = None
                self.update_available = False
            elif response.status_code == 200:
                release = response.json()
                tag_name = release.get("tag_name", "").lstrip("v")
                
                self.latest_version = tag_name
                self.latest_release = {
                    "version": tag_name,
                    "name": release.get("name", ""),
                    "body": release.get("body", ""),
                    "html_url": release.get("html_url", ""),
                    "published_at": release.get("published_at", ""),
                    "assets": [
                        {
                            "name": asset.get("name"),
                            "download_url": asset.get("browser_download_url"),
                            "size": asset.get("size")
                        }
                        for asset in release.get("assets", [])
                    ]
                }
                
                # Compare versions
                self.update_available = self._compare_versions(tag_name, self.current_version)
            else:
                self.error = f"GitHub API returned {response.status_code}"
            
            self.last_check = time.time()
            self._save_cache()
            
        except requests.RequestException as e:
            self.error = f"Network error: {str(e)}"
        except Exception as e:
            self.error = f"Unexpected error: {str(e)}"
        finally:
            self.checking = False
        
        return self.get_status()
    
    def _compare_versions(self, v1: str, v2: str) -> bool:
        """
        Compare semantic versions.
        
        Returns:
            True if v1 > v2 (update available)
        """
        try:
            v1_parts = [int(x) for x in v1.split(".")]
            v2_parts = [int(x) for x in v2.split(".")]
            
            # Pad shorter version with zeros
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts += [0] * (max_len - len(v1_parts))
            v2_parts += [0] * (max_len - len(v2_parts))
            
            return v1_parts > v2_parts
        except:
            # Fallback to string comparison
            return v1 > v2
    
    def get_status(self) -> Dict[str, Any]:
        """Get current update status."""
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "checking": self.checking,
            "last_check": self.last_check,
            "last_check_iso": datetime.fromtimestamp(self.last_check, tz=timezone.utc).isoformat() if self.last_check else None,
            "error": self.error,
            "release": self.latest_release
        }
    
    def perform_update(self) -> Dict[str, Any]:
        """
        Perform git pull to update the repository.
        
        Returns:
            Dict with update result
        """
        try:
            repo_root = Path(__file__).parent
            
            # Check if we're in a git repository
            git_dir = repo_root / ".git"
            if not git_dir.exists():
                return {
                    "success": False,
                    "message": "Not a git repository. Please clone from GitHub.",
                    "error": "no_git_repo"
                }
            
            # Stash any local changes
            subprocess.run(
                ["git", "stash"],
                cwd=repo_root,
                capture_output=True,
                timeout=10
            )
            
            # Pull latest changes
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Update successful
                new_version = self._get_current_version()
                
                return {
                    "success": True,
                    "message": "Update successful! Please restart the server.",
                    "output": result.stdout,
                    "new_version": new_version,
                    "needs_restart": True
                }
            else:
                return {
                    "success": False,
                    "message": "Update failed. Please check git status.",
                    "error": result.stderr,
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Update timeout. Please try manually.",
                "error": "timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Update error: {str(e)}",
                "error": str(e)
            }
    
    def get_git_status(self) -> Dict[str, Any]:
        """Get current git repository status."""
        try:
            repo_root = Path(__file__).parent
            
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Get current commit
            commit_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Get uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Check if ahead/behind remote
            tracking_result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            ahead, behind = 0, 0
            if tracking_result.returncode == 0:
                parts = tracking_result.stdout.strip().split()
                if len(parts) == 2:
                    ahead, behind = int(parts[0]), int(parts[1])
            
            return {
                "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown",
                "commit": commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown",
                "uncommitted_changes": len(status_result.stdout.strip().split("\n")) if status_result.stdout.strip() else 0,
                "ahead": ahead,
                "behind": behind,
                "clean": not status_result.stdout.strip()
            }
        except Exception as e:
            return {
                "error": str(e),
                "branch": "unknown",
                "commit": "unknown"
            }


# Global version manager instance
version_manager = VersionManager()


def check_updates_background():
    """Background thread to periodically check for updates."""
    while True:
        try:
            version_manager.check_for_updates(force=False)
        except Exception as e:
            print(f"Background update check failed: {e}")
        
        time.sleep(UPDATE_CHECK_INTERVAL)


# Start background update checker
_update_thread = threading.Thread(target=check_updates_background, daemon=True)
_update_thread.start()
