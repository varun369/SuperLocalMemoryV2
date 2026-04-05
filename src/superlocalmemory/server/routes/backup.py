# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com
"""SuperLocalMemory V3 - Backup Routes
 - Elastic License 2.0

Routes: /api/backup/status, /api/backup/create, /api/backup/configure, /api/backup/list
Uses V3 infra.backup.BackupManager.
"""
import logging

from fastapi import APIRouter, HTTPException

from .helpers import BackupConfigRequest, DB_PATH, MEMORY_DIR

logger = logging.getLogger("superlocalmemory.routes.backup")
router = APIRouter()

# Feature flag
BACKUP_AVAILABLE = False
try:
    from superlocalmemory.infra.backup import BackupManager
    BACKUP_AVAILABLE = True
except ImportError:
    pass


def _get_backup_manager() -> "BackupManager":
    """Get V3 backup manager instance."""
    return BackupManager(db_path=DB_PATH, base_dir=MEMORY_DIR)


@router.get("/api/backup/status")
async def backup_status():
    """Get auto-backup system status."""
    if not BACKUP_AVAILABLE:
        return {"status": "not_implemented", "message": "Backup module not available"}
    try:
        manager = _get_backup_manager()
        return manager.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup status error: {str(e)}")


@router.post("/api/backup/create")
async def backup_create():
    """Create a manual backup immediately."""
    if not BACKUP_AVAILABLE:
        return {"success": False, "message": "Backup module not available"}
    try:
        manager = _get_backup_manager()
        filename = manager.create_backup(label='manual')
        if filename:
            return {
                "success": True, "filename": str(filename),
                "message": f"Backup created: {filename}",
                "status": manager.get_status(),
            }
        return {"success": False, "message": "Backup failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup create error: {str(e)}")


@router.post("/api/backup/configure")
async def backup_configure(request: BackupConfigRequest):
    """Update auto-backup configuration."""
    if not BACKUP_AVAILABLE:
        return {"success": False, "message": "Backup module not available"}
    try:
        manager = _get_backup_manager()
        result = manager.configure(
            interval_hours=request.interval_hours,
            max_backups=request.max_backups,
            enabled=request.enabled,
        )
        return {"success": True, "message": "Backup configuration updated", "status": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup configure error: {str(e)}")


@router.get("/api/backup/list")
async def backup_list():
    """List all available backups."""
    if not BACKUP_AVAILABLE:
        return {"backups": [], "count": 0, "message": "Backup module not available"}
    try:
        manager = _get_backup_manager()
        backups = manager.list_backups()
        return {"backups": backups, "count": len(backups)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup list error: {str(e)}")
