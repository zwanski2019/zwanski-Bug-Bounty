#!/usr/bin/env python3
"""
ZWANSKI dashboard monitor.
Automatically clears port 1337, restarts the server on crashes, and reloads when watched files change.
"""
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from shutil import which

import psutil

ROOT = Path(__file__).resolve().parent
SERVER_SCRIPT = ROOT / "server.py"
WATCH_PATHS = [ROOT / "server.py", ROOT / "config.json", ROOT / "ui"]
STOP_FLAG = ROOT / ".monitor_stop"


def find_files(paths):
    files = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for item in path.rglob("*"):
                if item.is_file():
                    files.append(item)
    return sorted(files, key=lambda p: str(p))


def read_mtimes(paths):
    mtimes = {}
    for path in paths:
        try:
            mtimes[str(path)] = path.stat().st_mtime
        except OSError:
            mtimes[str(path)] = None
    return mtimes


def kill_port_process(port):
    pids = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if not conn.laddr or conn.laddr.port != port:
                continue
            if conn.status != psutil.CONN_LISTEN or not conn.pid:
                continue
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
        time.sleep(0.25)
    if which("fuser"):
        subprocess.run(["fuser", "-k", f"{port}/tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if which("lsof"):
        result = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.strip().isdigit():
                try:
                    os.kill(int(line.strip()), signal.SIGKILL)
                except OSError:
                    pass
        return
    if not pids:
        print("Warning: no fuser/lsof and psutil found no listener; bind may fail.", file=sys.stderr)


def safe_terminate(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def main():
    parser = argparse.ArgumentParser(description="ZWANSKI dashboard monitor")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "1337")))
    parser.add_argument("--no-watch", action="store_true", help="Disable file watch reloads")
    args = parser.parse_args()

    if not SERVER_SCRIPT.exists():
        print(f"Error: server script not found at {SERVER_SCRIPT}", file=sys.stderr)
        return 1

    if STOP_FLAG.exists():
        STOP_FLAG.unlink(missing_ok=True)

    while True:
        if STOP_FLAG.exists():
            print("Monitor stop requested. Exiting without restart.")
            STOP_FLAG.unlink(missing_ok=True)
            break

        print(f"Checking port {args.port} and stopping any occupant.")
        kill_port_process(args.port)

        watched_files = find_files(WATCH_PATHS)
        last_mtimes = read_mtimes(watched_files)

        print(f"Starting ZWANSKI dashboard on http://localhost:{args.port}")
        env = os.environ.copy()
        env["PORT"] = str(args.port)
        proc = subprocess.Popen([sys.executable, str(SERVER_SCRIPT)], env=env)

        while True:
            if proc.poll() is not None:
                print(f"Server process exited with code {proc.returncode}.")
                break
            if not args.no_watch:
                current_mtimes = read_mtimes(watched_files)
                if current_mtimes != last_mtimes:
                    print("Detected code or UI changes, restarting dashboard.")
                    last_mtimes = current_mtimes
                    safe_terminate(proc)
                    break
            if STOP_FLAG.exists():
                print("Monitor stop requested. Stopping dashboard.")
                safe_terminate(proc)
                break
            time.sleep(1)

        if STOP_FLAG.exists():
            print("Monitor stop flag present. Exiting monitor.")
            STOP_FLAG.unlink(missing_ok=True)
            break

        if proc.poll() is None:
            safe_terminate(proc)
        print("Restarting ZWANSKI dashboard in 2 seconds...")
        time.sleep(2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
