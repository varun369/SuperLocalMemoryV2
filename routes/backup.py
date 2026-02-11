"""
SuperLocalMemory V2 - Backup Routes
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /api/backup/status, /api/backup/create, /api/backup/configure, /api/backup/list
"""

from fastapi import APIRouter, HTTPException

from .helpers import BackupConfigRequest

router = APIRouter()


@router.get("/api/backup/status")
async def backup_status():
    """Get auto-backup system status."""
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        return backup.get_status()
    except ImportError:
        raise HTTPException(status_code=501, detail="Auto-backup module not installed. Update SuperLocalMemory to v2.4.0+.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup status error: {str(e)}")


@router.post("/api/backup/create")
async def backup_create():
    """Create a manual backup immediately."""
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        filename = backup.create_backup(label='manual')
        if filename:
            return {"success": True, "filename": filename, "message": f"Backup created: {filename}", "status": backup.get_status()}
        else:
            return {"success": False, "message": "Backup failed", "status": backup.get_status()}
    except ImportError:
        raise HTTPException(status_code=501, detail="Auto-backup module not installed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup create error: {str(e)}")


@router.post("/api/backup/configure")
async def backup_configure(request: BackupConfigRequest):
    """Update auto-backup configuration."""
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        result = backup.configure(
            interval_hours=request.interval_hours,
            max_backups=request.max_backups,
            enabled=request.enabled
        )
        return {"success": True, "message": "Backup configuration updated", "status": result}
    except ImportError:
        raise HTTPException(status_code=501, detail="Auto-backup module not installed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup configure error: {str(e)}")


@router.get("/api/backup/list")
async def backup_list():
    """List all available backups."""
    try:
        from auto_backup import AutoBackup
        backup = AutoBackup()
        backups = backup.list_backups()
        return {"backups": backups, "count": len(backups)}
    except ImportError:
        raise HTTPException(status_code=501, detail="Auto-backup module not installed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup list error: {str(e)}")
