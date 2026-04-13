# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""OS-level service installer — daemon survives reboots.

Cross-platform:
  - macOS:   LaunchAgent plist (user-level, no sudo)
  - Linux:   systemd user service (no sudo)
  - Windows: Task Scheduler (runs at logon)

Usage:
  slm serve install   — install OS service
  slm serve uninstall — remove OS service
  slm serve status    — show daemon + service status
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_SERVICE_NAME = "com.qualixar.superlocalmemory"
_DISPLAY_NAME = "SuperLocalMemory Daemon"


def get_python_path() -> str:
    """Get the full path to the Python interpreter running SLM."""
    return sys.executable


def get_log_path() -> Path:
    log_dir = Path.home() / ".superlocalmemory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "daemon.log"


def get_error_log_path() -> Path:
    log_dir = Path.home() / ".superlocalmemory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "daemon-error.log"


# ─── macOS: LaunchAgent ───────────────────────────────────────────────────

def _macos_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_SERVICE_NAME}.plist"


def _macos_plist_content() -> str:
    python = get_python_path()
    log = get_log_path()
    err_log = get_error_log_path()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_SERVICE_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>superlocalmemory.server.unified_daemon</string>
        <string>--start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <key>StandardOutPath</key>
    <string>{log}</string>
    <key>StandardErrorPath</key>
    <string>{err_log}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:{Path(python).parent}</string>
        <key>HOME</key>
        <string>{Path.home()}</string>
    </dict>
</dict>
</plist>
"""


def install_macos() -> bool:
    plist = _macos_plist_path()
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(_macos_plist_content())
    logger.info("Wrote LaunchAgent plist: %s", plist)

    # Load the service
    try:
        subprocess.run(
            ["launchctl", "unload", str(plist)],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass

    result = subprocess.run(
        ["launchctl", "load", str(plist)],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        logger.info("LaunchAgent loaded successfully")
        return True
    else:
        logger.error("launchctl load failed: %s", result.stderr)
        return False


def uninstall_macos() -> bool:
    plist = _macos_plist_path()
    if plist.exists():
        try:
            subprocess.run(
                ["launchctl", "unload", str(plist)],
                capture_output=True, timeout=10,
            )
        except Exception:
            pass
        plist.unlink()
        logger.info("LaunchAgent removed: %s", plist)
    return True


def status_macos() -> dict:
    result = subprocess.run(
        ["launchctl", "list", _SERVICE_NAME],
        capture_output=True, text=True, timeout=10,
    )
    installed = result.returncode == 0
    return {
        "platform": "macOS",
        "service_type": "LaunchAgent",
        "installed": installed,
        "plist_path": str(_macos_plist_path()),
        "details": result.stdout.strip() if installed else "Not installed",
    }


# ─── Linux: systemd user service ──────────────────────────────────────────

def _linux_service_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "superlocalmemory.service"


def _linux_service_content() -> str:
    python = get_python_path()
    log = get_log_path()

    return f"""[Unit]
Description={_DISPLAY_NAME}
After=network.target

[Service]
Type=simple
ExecStart={python} -m superlocalmemory.server.unified_daemon --start
Restart=on-failure
RestartSec=30
StandardOutput=append:{log}
StandardError=append:{get_error_log_path()}
Environment=HOME={Path.home()}
Environment=PATH=/usr/local/bin:/usr/bin:/bin:{Path(python).parent}

[Install]
WantedBy=default.target
"""


def install_linux() -> bool:
    service = _linux_service_path()
    service.parent.mkdir(parents=True, exist_ok=True)
    service.write_text(_linux_service_content())
    logger.info("Wrote systemd user service: %s", service)

    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=10)
        subprocess.run(["systemctl", "--user", "enable", "superlocalmemory"], capture_output=True, timeout=10)
        result = subprocess.run(
            ["systemctl", "--user", "start", "superlocalmemory"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            logger.info("systemd user service started")
            return True
        else:
            logger.error("systemctl start failed: %s", result.stderr)
            return False
    except FileNotFoundError:
        logger.warning("systemctl not found — systemd not available on this system")
        return False


def uninstall_linux() -> bool:
    try:
        subprocess.run(["systemctl", "--user", "stop", "superlocalmemory"], capture_output=True, timeout=10)
        subprocess.run(["systemctl", "--user", "disable", "superlocalmemory"], capture_output=True, timeout=10)
    except Exception:
        pass
    service = _linux_service_path()
    if service.exists():
        service.unlink()
        logger.info("systemd user service removed: %s", service)
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=10)
    except Exception:
        pass
    return True


def status_linux() -> dict:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "superlocalmemory"],
            capture_output=True, text=True, timeout=10,
        )
        active = result.stdout.strip() == "active"
        return {
            "platform": "Linux",
            "service_type": "systemd user service",
            "installed": True,
            "active": active,
            "details": result.stdout.strip(),
        }
    except Exception:
        return {"platform": "Linux", "service_type": "systemd", "installed": False}


# ─── Windows: Task Scheduler ─────────────────────────────────────────────

_WINDOWS_TASK_NAME = "SuperLocalMemory"


def install_windows() -> bool:
    python = get_python_path()
    log = get_log_path()

    # Create a VBS wrapper to run Python without console window
    vbs_path = Path.home() / ".superlocalmemory" / "start-daemon.vbs"
    vbs_path.parent.mkdir(parents=True, exist_ok=True)
    vbs_content = (
        f'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.Run """{python}"" -m superlocalmemory.server.unified_daemon --start", 0, False\n'
    )
    vbs_path.write_text(vbs_content)

    # Use schtasks to create a logon trigger task
    try:
        # Remove existing task if any
        subprocess.run(
            ["schtasks", "/Delete", "/TN", _WINDOWS_TASK_NAME, "/F"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass

    try:
        result = subprocess.run(
            [
                "schtasks", "/Create",
                "/TN", _WINDOWS_TASK_NAME,
                "/TR", f'wscript.exe "{vbs_path}"',
                "/SC", "ONLOGON",
                "/RL", "LIMITED",
                "/F",
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            logger.info("Windows Task Scheduler task created: %s", _WINDOWS_TASK_NAME)
            return True
        else:
            logger.error("schtasks create failed: %s", result.stderr)
            return False
    except FileNotFoundError:
        logger.warning("schtasks not found — not a standard Windows system")
        return False


def uninstall_windows() -> bool:
    try:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", _WINDOWS_TASK_NAME, "/F"],
            capture_output=True, timeout=10,
        )
        logger.info("Windows Task Scheduler task removed")
    except Exception:
        pass

    vbs_path = Path.home() / ".superlocalmemory" / "start-daemon.vbs"
    if vbs_path.exists():
        vbs_path.unlink()

    return True


def status_windows() -> dict:
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", _WINDOWS_TASK_NAME, "/FO", "LIST"],
            capture_output=True, text=True, timeout=10,
        )
        installed = result.returncode == 0
        return {
            "platform": "Windows",
            "service_type": "Task Scheduler",
            "installed": installed,
            "task_name": _WINDOWS_TASK_NAME,
            "details": result.stdout.strip()[:200] if installed else "Not installed",
        }
    except Exception:
        return {"platform": "Windows", "service_type": "Task Scheduler", "installed": False}


# ─── Cross-platform dispatcher ───────────────────────────────────────────

def install_service() -> bool:
    """Install OS-level service for auto-start on login/boot."""
    if sys.platform == "darwin":
        return install_macos()
    elif sys.platform == "win32":
        return install_windows()
    elif sys.platform.startswith("linux"):
        return install_linux()
    else:
        logger.warning("Unsupported platform: %s", sys.platform)
        return False


def uninstall_service() -> bool:
    """Remove OS-level service."""
    if sys.platform == "darwin":
        return uninstall_macos()
    elif sys.platform == "win32":
        return uninstall_windows()
    elif sys.platform.startswith("linux"):
        return uninstall_linux()
    else:
        return False


def service_status() -> dict:
    """Get OS-level service status."""
    if sys.platform == "darwin":
        return status_macos()
    elif sys.platform == "win32":
        return status_windows()
    elif sys.platform.startswith("linux"):
        return status_linux()
    else:
        return {"platform": sys.platform, "installed": False, "details": "Unsupported platform"}
