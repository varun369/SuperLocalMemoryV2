"""
SuperLocalMemory V2 - Profile Routes
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /api/profiles, /api/profiles/{name}/switch, /api/profiles/create, DELETE /api/profiles/{name}
"""

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException

from .helpers import (
    get_db_connection, get_active_profile, validate_profile_name,
    ProfileSwitch, MEMORY_DIR, DB_PATH
)

router = APIRouter()

# WebSocket manager reference (set by ui_server.py at startup)
ws_manager = None


@router.get("/api/profiles")
async def list_profiles():
    """List available memory profiles."""
    try:
        config_file = MEMORY_DIR / "profiles.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {'profiles': {'default': {'name': 'default', 'description': 'Default memory profile'}}, 'active_profile': 'default'}

        active = config.get('active_profile', 'default')
        profiles = []

        conn = get_db_connection()
        cursor = conn.cursor()
        for name, info in config.get('profiles', {}).items():
            cursor.execute("SELECT COUNT(*) FROM memories WHERE profile = ?", (name,))
            count = cursor.fetchone()[0]
            profiles.append({
                "name": name, "description": info.get('description', ''),
                "memory_count": count, "created_at": info.get('created_at', ''),
                "last_used": info.get('last_used', ''), "is_active": name == active
            })
        conn.close()

        return {"profiles": profiles, "active_profile": active, "total_profiles": len(profiles)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile list error: {str(e)}")


@router.post("/api/profiles/{name}/switch")
async def switch_profile(name: str):
    """Switch active memory profile."""
    try:
        if not validate_profile_name(name):
            raise HTTPException(status_code=400, detail="Invalid profile name.")

        config_file = MEMORY_DIR / "profiles.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {'profiles': {'default': {'name': 'default', 'description': 'Default memory profile'}}, 'active_profile': 'default'}

        if name not in config.get('profiles', {}):
            raise HTTPException(status_code=404, detail=f"Profile '{name}' not found. Available: {', '.join(config.get('profiles', {}).keys())}")

        previous = config.get('active_profile', 'default')
        config['active_profile'] = name
        config['profiles'][name]['last_used'] = datetime.now().isoformat()

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories WHERE profile = ?", (name,))
        count = cursor.fetchone()[0]
        conn.close()

        if ws_manager:
            await ws_manager.broadcast({
                "type": "profile_switched", "profile": name,
                "previous": previous, "memory_count": count,
                "timestamp": datetime.now().isoformat()
            })

        return {
            "success": True, "active_profile": name, "previous_profile": previous,
            "memory_count": count,
            "message": f"Switched to profile '{name}' ({count} memories). Changes take effect immediately."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile switch error: {str(e)}")


@router.post("/api/profiles/create")
async def create_profile(body: ProfileSwitch):
    """Create a new memory profile."""
    try:
        name = body.profile_name
        if not validate_profile_name(name):
            raise HTTPException(status_code=400, detail="Invalid profile name")

        config_file = MEMORY_DIR / "profiles.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {'profiles': {'default': {'name': 'default', 'description': 'Default memory profile'}}, 'active_profile': 'default'}

        if name in config.get('profiles', {}):
            raise HTTPException(status_code=409, detail=f"Profile '{name}' already exists")

        config['profiles'][name] = {
            'name': name, 'description': f'Memory profile: {name}',
            'created_at': datetime.now().isoformat(), 'last_used': None
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return {"success": True, "profile": name, "message": f"Profile '{name}' created"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile create error: {str(e)}")


@router.delete("/api/profiles/{name}")
async def delete_profile(name: str):
    """Delete a profile. Moves its memories to 'default'."""
    try:
        if name == 'default':
            raise HTTPException(status_code=400, detail="Cannot delete 'default' profile")

        config_file = MEMORY_DIR / "profiles.json"
        with open(config_file, 'r') as f:
            config = json.load(f)

        if name not in config.get('profiles', {}):
            raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
        if config.get('active_profile') == name:
            raise HTTPException(status_code=400, detail="Cannot delete active profile. Switch first.")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE memories SET profile = 'default' WHERE profile = ?", (name,))
        moved = cursor.rowcount
        conn.commit()
        conn.close()

        del config['profiles'][name]
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return {"success": True, "message": f"Profile '{name}' deleted. {moved} memories moved to 'default'."}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile delete error: {str(e)}")
