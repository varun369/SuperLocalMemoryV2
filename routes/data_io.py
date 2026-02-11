"""
SuperLocalMemory V2 - Import/Export Routes
Copyright (c) 2026 Varun Pratap Bhardwaj — MIT License

Routes: /api/export, /api/import
"""

import io
import gzip
import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from .helpers import get_db_connection, dict_factory, DB_PATH

import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude-memory"))
from memory_store_v2 import MemoryStoreV2

# WebSocket manager reference (set by ui_server.py at startup)
ws_manager = None

router = APIRouter()


@router.get("/api/export")
async def export_memories(
    format: str = Query("json", pattern="^(json|jsonl)$"),
    category: Optional[str] = None,
    project_name: Optional[str] = None
):
    """Export memories as JSON or JSONL."""
    try:
        conn = get_db_connection()
        conn.row_factory = dict_factory
        cursor = conn.cursor()

        query = "SELECT * FROM memories WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if project_name:
            query += " AND project_name = ?"
            params.append(project_name)
        query += " ORDER BY created_at"

        cursor.execute(query, params)
        memories = cursor.fetchall()
        conn.close()

        if format == "jsonl":
            content = "\n".join(json.dumps(m) for m in memories)
            media_type = "application/x-ndjson"
        else:
            content = json.dumps({
                "version": "2.5.0", "exported_at": datetime.now().isoformat(),
                "total_memories": len(memories),
                "filters": {"category": category, "project_name": project_name},
                "memories": memories
            }, indent=2)
            media_type = "application/json"

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        if len(content) > 10000:
            compressed = gzip.compress(content.encode())
            return StreamingResponse(io.BytesIO(compressed), media_type="application/gzip",
                headers={"Content-Disposition": f"attachment; filename=memories_export_{ts}.{format}.gz"})
        else:
            return StreamingResponse(io.BytesIO(content.encode()), media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename=memories_export_{ts}.{format}"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@router.post("/api/import")
async def import_memories(file: UploadFile = File(...)):
    """Import memories from JSON file."""
    try:
        content = await file.read()
        if file.filename.endswith('.gz'):
            content = gzip.decompress(content)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        if isinstance(data, dict) and 'memories' in data:
            memories = data['memories']
        elif isinstance(data, list):
            memories = data
        else:
            raise HTTPException(status_code=400, detail="Invalid format: expected 'memories' array")

        store = MemoryStoreV2(DB_PATH)
        imported = 0
        skipped = 0
        errors = []

        for idx, memory in enumerate(memories):
            try:
                if 'content' not in memory:
                    errors.append(f"Memory {idx}: missing 'content' field")
                    continue
                store.add_memory(
                    content=memory.get('content'),
                    summary=memory.get('summary'),
                    project_path=memory.get('project_path'),
                    project_name=memory.get('project_name'),
                    tags=memory.get('tags', '').split(',') if memory.get('tags') else None,
                    category=memory.get('category'),
                    importance=memory.get('importance', 5)
                )
                imported += 1

                if ws_manager:
                    await ws_manager.broadcast({
                        "type": "memory_added", "memory_id": imported,
                        "timestamp": datetime.now().isoformat()
                    })

            except Exception as e:
                if "UNIQUE constraint failed" in str(e):
                    skipped += 1
                else:
                    errors.append(f"Memory {idx}: {str(e)}")

        return {
            "success": True, "imported_count": imported, "skipped_count": skipped,
            "total_processed": len(memories), "errors": errors[:10]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")
