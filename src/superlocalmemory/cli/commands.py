# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""CLI command implementations.

Each function handles one CLI command. Dispatch routes by name.
All data-returning commands support --json for agent-native output.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import sys
from argparse import Namespace


def dispatch(args: Namespace) -> None:
    """Route CLI command to the appropriate handler."""
    handlers = {
        "setup": cmd_setup,
        "mode": cmd_mode,
        "provider": cmd_provider,
        "connect": cmd_connect,
        "migrate": cmd_migrate,
        "list": cmd_list,
        "remember": cmd_remember,
        "recall": cmd_recall,
        "forget": cmd_forget,
        "delete": cmd_delete,
        "update": cmd_update,
        "status": cmd_status,
        "health": cmd_health,
        "trace": cmd_trace,
        "mcp": cmd_mcp,
        "warmup": cmd_warmup,
        "dashboard": cmd_dashboard,
        "profile": cmd_profile,
    }
    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


# -- Setup & Config (no --json — interactive commands) ---------------------


def cmd_setup(_args: Namespace) -> None:
    """Run the interactive setup wizard."""
    from superlocalmemory.cli.setup_wizard import run_wizard

    run_wizard()


def cmd_mode(args: Namespace) -> None:
    """Get or set the operating mode."""
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.storage.models import Mode

    config = SLMConfig.load()

    if getattr(args, 'json', False):
        from superlocalmemory.cli.json_output import json_print
        if args.value:
            old_mode = config.mode.value.upper()
            updated = SLMConfig.for_mode(
                Mode(args.value),
                llm_provider=config.llm.provider,
                llm_model=config.llm.model,
                llm_api_key=config.llm.api_key,
                llm_api_base=config.llm.api_base,
            )
            updated.save()
            json_print("mode", data={
                "previous_mode": old_mode, "current_mode": args.value.upper(),
            }, next_actions=[
                {"command": "slm status --json", "description": "Check system status"},
            ])
        else:
            json_print("mode", data={"current_mode": config.mode.value.upper()},
                       next_actions=[
                           {"command": "slm mode a --json", "description": "Switch to zero-cloud mode"},
                           {"command": "slm mode c --json", "description": "Switch to full-power mode"},
                       ])
        return

    if args.value:
        updated = SLMConfig.for_mode(
            Mode(args.value),
            llm_provider=config.llm.provider,
            llm_model=config.llm.model,
            llm_api_key=config.llm.api_key,
            llm_api_base=config.llm.api_base,
        )
        updated.save()
        print(f"Mode set to: {args.value.upper()}")
    else:
        print(f"Current mode: {config.mode.value.upper()}")


def cmd_provider(args: Namespace) -> None:
    """Get or set the LLM provider."""
    from superlocalmemory.core.config import SLMConfig

    config = SLMConfig.load()

    if args.action == "set":
        from superlocalmemory.cli.setup_wizard import configure_provider

        configure_provider(config)
    else:
        print(f"Provider: {config.llm.provider or 'none (Mode A)'}")
        if config.llm.model:
            print(f"Model: {config.llm.model}")


def cmd_connect(args: Namespace) -> None:
    """Configure IDE integrations."""
    from superlocalmemory.hooks.ide_connector import IDEConnector

    connector = IDEConnector()

    if getattr(args, 'json', False):
        from superlocalmemory.cli.json_output import json_print
        if getattr(args, "list", False):
            json_print("connect", data={"ides": connector.get_status()},
                       next_actions=[
                           {"command": "slm connect --json", "description": "Auto-configure all IDEs"},
                       ])
        elif getattr(args, "ide", None):
            success = connector.connect(args.ide)
            json_print("connect", data={"ide": args.ide, "connected": success})
        else:
            json_print("connect", data={"results": connector.connect_all()},
                       next_actions=[
                           {"command": "slm status --json", "description": "Check system status"},
                       ])
        return

    if getattr(args, "list", False):
        status = connector.get_status()
        for s in status:
            mark = "[+]" if s["installed"] else "[-]"
            print(f"  {mark} {s['name']:20s} {s['config_path']}")
        return
    if getattr(args, "ide", None):
        success = connector.connect(args.ide)
        print(f"{'Connected' if success else 'Failed'}: {args.ide}")
    else:
        results = connector.connect_all()
        for ide_id, ide_status in results.items():
            print(f"  {ide_id}: {ide_status}")


def cmd_migrate(args: Namespace) -> None:
    """Run V2 to V3 migration."""
    from superlocalmemory.cli.migrate_cmd import cmd_migrate as _migrate

    _migrate(args)


# -- Memory Operations (all support --json) --------------------------------


def cmd_list(args: Namespace) -> None:
    """List recent memories chronologically."""
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.core.engine import MemoryEngine

    use_json = getattr(args, 'json', False)
    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()

        limit = getattr(args, "limit", 20)
        facts = engine._db.get_all_facts(engine.profile_id)
        facts.sort(key=lambda f: f.created_at or "", reverse=True)
        facts = facts[:limit]
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("list", error={"code": "ENGINE_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        items = []
        for f in facts:
            ftype_raw = getattr(f, "fact_type", "")
            ftype = ftype_raw.value if hasattr(ftype_raw, "value") else str(ftype_raw)
            items.append({
                "fact_id": f.fact_id, "content": f.content,
                "fact_type": ftype, "created_at": (f.created_at or "")[:19],
            })
        json_print("list", data={"results": items, "count": len(items)},
                   next_actions=[
                       {"command": "slm recall '<query>' --json", "description": "Search memories"},
                       {"command": "slm delete <fact_id> --json --yes", "description": "Delete a memory"},
                   ])
        return

    if not facts:
        print("No memories stored yet.")
        return

    print(f"Recent memories ({len(facts)}):\n")
    for i, f in enumerate(facts, 1):
        date = (f.created_at or "")[:19]
        ftype_raw = getattr(f, "fact_type", "")
        ftype = ftype_raw.value if hasattr(ftype_raw, "value") else str(ftype_raw)
        content = f.content[:100] + ("..." if len(f.content) > 100 else "")
        print(f"  {i:3d}. [{date}] ({ftype}) {content}")


def cmd_remember(args: Namespace) -> None:
    """Store a memory via the engine."""
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.core.engine import MemoryEngine

    use_json = getattr(args, 'json', False)
    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()

        metadata = {"tags": args.tags} if args.tags else {}
        fact_ids = engine.store(args.content, metadata=metadata)
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("remember", error={"code": "STORE_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        json_print("remember", data={"fact_ids": fact_ids, "count": len(fact_ids)},
                   next_actions=[
                       {"command": "slm recall '<query>' --json", "description": "Search your memories"},
                       {"command": "slm list --json -n 5", "description": "See recent memories"},
                   ])
        return

    print(f"Stored {len(fact_ids)} facts.")


def cmd_recall(args: Namespace) -> None:
    """Search memories via the engine."""
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.core.engine import MemoryEngine

    use_json = getattr(args, 'json', False)
    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()

        response = engine.recall(args.query, limit=args.limit)
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("recall", error={"code": "RECALL_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        items = []
        for r in response.results:
            item = {
                "fact_id": r.fact.fact_id, "content": r.fact.content,
                "score": round(r.score, 3),
            }
            if hasattr(r, "channel_scores") and r.channel_scores:
                item["channel_scores"] = {k: round(v, 3) for k, v in r.channel_scores.items()}
            items.append(item)
        json_print("recall", data={
            "results": items, "count": len(items),
            "query_type": getattr(response, "query_type", "unknown"),
        }, next_actions=[
            {"command": "slm list --json", "description": "List recent memories"},
        ])
        return

    if not response.results:
        print("No memories found.")
        return
    for i, r in enumerate(response.results, 1):
        print(f"  {i}. [{r.score:.2f}] {r.fact.content[:120]}")


def cmd_forget(args: Namespace) -> None:
    """Delete memories matching a query."""
    from superlocalmemory.core.engine import MemoryEngine
    from superlocalmemory.core.config import SLMConfig

    use_json = getattr(args, 'json', False)
    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()
        facts = engine._db.get_all_facts(engine.profile_id)
        query_lower = args.query.lower()
        matches = [f for f in facts if query_lower in f.content.lower()]
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("forget", error={"code": "ENGINE_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        if not matches:
            json_print("forget", data={"matched_count": 0, "deleted_count": 0, "matches": []})
            return
        match_items = [{"fact_id": f.fact_id, "content": f.content[:120]} for f in matches[:20]]
        if getattr(args, 'yes', False):
            for f in matches:
                engine._db.delete_fact(f.fact_id)
            json_print("forget", data={
                "matched_count": len(matches), "deleted_count": len(matches),
                "deleted": [f.fact_id for f in matches],
            }, next_actions=[
                {"command": "slm list --json", "description": "Verify remaining memories"},
            ])
        else:
            json_print("forget", data={
                "matched_count": len(matches), "deleted_count": 0,
                "matches": match_items,
                "hint": "Add --yes to confirm deletion",
            }, next_actions=[
                {"command": f"slm forget '{args.query}' --json --yes", "description": "Confirm deletion"},
            ])
        return

    if not matches:
        print(f"No memories matching '{args.query}'")
        return
    print(f"Found {len(matches)} matching memories:")
    for f in matches[:10]:
        print(f"  - {f.fact_id[:8]}... {f.content[:80]}")
    if getattr(args, 'yes', False):
        for f in matches:
            engine._db.delete_fact(f.fact_id)
        print(f"Deleted {len(matches)} memories.")
        return
    confirm = input(f"Delete {len(matches)} memories? [y/N] ").strip().lower()
    if confirm in ("y", "yes"):
        for f in matches:
            engine._db.delete_fact(f.fact_id)
        print(f"Deleted {len(matches)} memories.")
    else:
        print("Cancelled.")


def cmd_delete(args: Namespace) -> None:
    """Delete a specific memory by exact fact ID."""
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.core.engine import MemoryEngine

    use_json = getattr(args, 'json', False)
    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()

        fact_id = args.fact_id.strip()
        rows = engine._db.execute(
            "SELECT content FROM atomic_facts WHERE fact_id = ? AND profile_id = ?",
            (fact_id, engine.profile_id),
        )
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("delete", error={"code": "ENGINE_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        if not rows:
            json_print("delete", error={
                "code": "NOT_FOUND", "message": f"Memory not found: {fact_id}",
            })
            sys.exit(1)
        content = dict(rows[0]).get("content", "")
        if getattr(args, "yes", False):
            engine._db.delete_fact(fact_id)
            json_print("delete", data={"deleted": fact_id, "content": content[:120]},
                       next_actions=[
                           {"command": "slm list --json", "description": "Verify remaining memories"},
                       ])
        else:
            json_print("delete", data={
                "fact_id": fact_id, "content": content[:120], "deleted": False,
                "hint": "Add --yes to confirm deletion",
            }, next_actions=[
                {"command": f"slm delete {fact_id} --json --yes", "description": "Confirm deletion"},
            ])
        return

    if not rows:
        print(f"Memory not found: {fact_id}")
        return

    content_preview = dict(rows[0]).get("content", "")[:120]
    print(f"Memory: {content_preview}")

    if not getattr(args, "yes", False):
        confirm = input("Delete this memory? [y/N] ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Cancelled.")
            return

    engine._db.delete_fact(fact_id)
    print(f"Deleted: {fact_id}")


def cmd_update(args: Namespace) -> None:
    """Update the content of a specific memory by exact fact ID."""
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.core.engine import MemoryEngine

    use_json = getattr(args, 'json', False)
    fact_id = args.fact_id.strip()
    new_content = args.content.strip()

    if not new_content:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("update", error={"code": "INVALID_INPUT", "message": "content cannot be empty"})
            sys.exit(1)
        print("Error: content cannot be empty")
        return

    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()

        rows = engine._db.execute(
            "SELECT content FROM atomic_facts WHERE fact_id = ? AND profile_id = ?",
            (fact_id, engine.profile_id),
        )
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("update", error={"code": "ENGINE_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if not rows:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("update", error={
                "code": "NOT_FOUND", "message": f"Memory not found: {fact_id}",
            })
            sys.exit(1)
        print(f"Memory not found: {fact_id}")
        return

    old_content = dict(rows[0]).get("content", "")
    engine._db.execute(
        "UPDATE atomic_facts SET content = ? WHERE fact_id = ?",
        (new_content, fact_id),
    )

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        json_print("update", data={
            "fact_id": fact_id,
            "old_content": old_content[:120],
            "new_content": new_content[:120],
        }, next_actions=[
            {"command": "slm list --json", "description": "List recent memories"},
        ])
        return

    print(f"Old: {old_content[:100]}")
    print(f"New: {new_content[:100]}")
    print(f"Updated: {fact_id}")


# -- Diagnostics (all support --json) -------------------------------------


def cmd_status(args: Namespace) -> None:
    """Show system status."""
    from superlocalmemory.core.config import SLMConfig

    config = SLMConfig.load()

    if getattr(args, 'json', False):
        from superlocalmemory.cli.json_output import json_print
        data = {
            "mode": config.mode.value.upper(),
            "provider": config.llm.provider or "none",
            "base_dir": str(config.base_dir),
            "db_path": str(config.db_path),
        }
        if config.db_path.exists():
            data["db_size_mb"] = round(config.db_path.stat().st_size / 1024 / 1024, 2)
        json_print("status", data=data, next_actions=[
            {"command": "slm health --json", "description": "Check math layer health"},
            {"command": "slm list --json", "description": "List recent memories"},
        ])
        return

    print("SuperLocalMemory V3")
    print(f"  Mode: {config.mode.value.upper()}")
    print(f"  Provider: {config.llm.provider or 'none'}")
    print(f"  Base dir: {config.base_dir}")
    print(f"  Database: {config.db_path}")
    if config.db_path.exists():
        size_mb = round(config.db_path.stat().st_size / 1024 / 1024, 2)
        print(f"  DB size: {size_mb} MB")


def cmd_health(args: Namespace) -> None:
    """Show math layer health status."""
    from superlocalmemory.core.engine import MemoryEngine
    from superlocalmemory.core.config import SLMConfig

    use_json = getattr(args, 'json', False)
    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()
        facts = engine._db.get_all_facts(engine.profile_id)
        fisher_count = sum(1 for f in facts if f.fisher_mean is not None)
        langevin_count = sum(1 for f in facts if f.langevin_position is not None)
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("health", error={"code": "ENGINE_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        json_print("health", data={
            "total_facts": len(facts),
            "similarity_indexed": fisher_count,
            "lifecycle_positioned": langevin_count,
            "mode": config.mode.value.upper(),
        }, next_actions=[
            {"command": "slm status --json", "description": "Check system status"},
            {"command": "slm recall '<query>' --json", "description": "Test retrieval"},
        ])
        return

    print("Math Layer Health:")
    print(f"  Total facts: {len(facts)}")
    print(f"  Fisher-Rao indexed: {fisher_count}/{len(facts)}")
    print(f"  Langevin positioned: {langevin_count}/{len(facts)}")
    print(f"  Mode: {config.mode.value.upper()}")


def cmd_trace(args: Namespace) -> None:
    """Recall with per-channel score breakdown."""
    from superlocalmemory.core.engine import MemoryEngine
    from superlocalmemory.core.config import SLMConfig

    use_json = getattr(args, 'json', False)
    try:
        config = SLMConfig.load()
        engine = MemoryEngine(config)
        response = engine.recall(args.query, limit=5)
    except Exception as exc:
        if use_json:
            from superlocalmemory.cli.json_output import json_print
            json_print("trace", error={"code": "ENGINE_ERROR", "message": str(exc)})
            sys.exit(1)
        raise

    if use_json:
        from superlocalmemory.cli.json_output import json_print
        items = []
        for r in response.results:
            item = {
                "fact_id": r.fact.fact_id, "content": r.fact.content[:200],
                "score": round(r.score, 3),
            }
            if hasattr(r, "channel_scores") and r.channel_scores:
                item["channel_scores"] = {
                    k: round(v, 3) for k, v in r.channel_scores.items()
                }
            items.append(item)
        json_print("trace", data={
            "query": args.query,
            "query_type": getattr(response, "query_type", "unknown"),
            "retrieval_time_ms": round(getattr(response, "retrieval_time_ms", 0), 1),
            "results": items, "count": len(items),
        }, next_actions=[
            {"command": "slm recall '<query>' --json", "description": "Standard recall"},
        ])
        return

    print(f"Query: {args.query}")
    print(f"Type: {response.query_type} | Time: {response.retrieval_time_ms:.0f}ms")
    print(f"Results: {len(response.results)}")
    for i, r in enumerate(response.results, 1):
        print(f"\n  {i}. [{r.score:.3f}] {r.fact.content[:100]}")
        if hasattr(r, "channel_scores") and r.channel_scores:
            for ch, sc in r.channel_scores.items():
                print(f"       {ch}: {sc:.3f}")


# -- Services (no --json — these start long-running processes) -------------


def cmd_mcp(_args: Namespace) -> None:
    """Start the V3 MCP server (stdio transport for IDE integration)."""
    from superlocalmemory.mcp.server import server

    server.run(transport="stdio")


def cmd_warmup(_args: Namespace) -> None:
    """Pre-download the embedding model so first use is instant."""
    print("Downloading embedding model (nomic-ai/nomic-embed-text-v1.5)...")
    print("This is ~500MB and only needed once.\n")

    try:
        from superlocalmemory.core.config import EmbeddingConfig
        from superlocalmemory.core.embeddings import EmbeddingService

        config = EmbeddingConfig()
        svc = EmbeddingService(config)

        # Force model load (triggers download)
        if svc.is_available:
            # Verify it works
            emb = svc.embed("warmup test")
            if emb and len(emb) == config.dimension:
                print(f"\nModel ready: {config.model_name} ({config.dimension}-dim)")
                print("Semantic search is fully operational.")
            else:
                print("\nModel loaded but embedding verification failed.")
                print("Run: pip install sentence-transformers einops")
        else:
            print("\nModel could not load.")
            print("Install dependencies: pip install sentence-transformers einops torch")
    except ImportError as exc:
        print(f"\nMissing dependency: {exc}")
        print("Install with: pip install sentence-transformers einops torch")
    except Exception as exc:
        print(f"\nWarmup failed: {exc}")
        print("Check your internet connection and try again.")


def cmd_dashboard(args: Namespace) -> None:
    """Launch the web dashboard."""
    try:
        import uvicorn
    except ImportError:
        print("Dashboard requires: pip install 'fastapi[all]' uvicorn")
        sys.exit(1)

    import socket

    port = getattr(args, "port", 8765)

    def _find_port(preferred: int) -> int:
        for p in [preferred] + list(range(preferred + 1, preferred + 20)):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", p))
                    return p
            except OSError:
                continue
        return preferred

    ui_port = _find_port(port)
    if ui_port != port:
        print(f"  Port {port} in use — using {ui_port} instead")

    print("=" * 60)
    print("  SuperLocalMemory V3 — Web Dashboard")
    print("=" * 60)
    print(f"  Dashboard:  http://localhost:{ui_port}")
    print(f"  API Docs:   http://localhost:{ui_port}/api/docs")
    print("  Press Ctrl+C to stop\n")

    from superlocalmemory.server.ui import create_app

    app = create_app()
    uvicorn.run(app, host="127.0.0.1", port=ui_port, log_level="info")


# -- Profiles (supports --json) -------------------------------------------


def cmd_profile(args: Namespace) -> None:
    """Profile management (list, switch, create).

    Writes to BOTH SQLite and profiles.json so CLI, Dashboard, and
    MCP all see the same profiles.
    """
    from superlocalmemory.core.config import SLMConfig
    from superlocalmemory.storage.database import DatabaseManager
    from superlocalmemory.storage import schema
    from superlocalmemory.server.routes.helpers import (
        ensure_profile_in_json, set_active_profile_everywhere,
    )

    config = SLMConfig.load()
    db = DatabaseManager(config.db_path)
    db.initialize(schema)

    if getattr(args, 'json', False):
        from superlocalmemory.cli.json_output import json_print
        if args.action == "list":
            rows = db.execute("SELECT profile_id, name FROM profiles")
            profiles = [
                {"profile_id": dict(r)["profile_id"], "name": dict(r).get("name", "")}
                for r in rows
            ]
            json_print("profile", data={"profiles": profiles, "count": len(profiles)},
                       next_actions=[
                           {"command": "slm profile switch <name> --json", "description": "Switch profile"},
                       ])
        elif args.action == "switch":
            set_active_profile_everywhere(args.name)
            config.active_profile = args.name
            config.save()
            json_print("profile", data={"action": "switched", "profile": args.name})
        elif args.action == "create":
            db.execute(
                "INSERT OR IGNORE INTO profiles (profile_id, name) VALUES (?, ?)",
                (args.name, args.name),
            )
            ensure_profile_in_json(args.name)
            json_print("profile", data={"action": "created", "profile": args.name},
                       next_actions=[
                           {"command": f"slm profile switch {args.name} --json",
                            "description": "Switch to new profile"},
                       ])
        return

    if args.action == "list":
        rows = db.execute("SELECT profile_id, name FROM profiles")
        print("Profiles:")
        for r in rows:
            d = dict(r)
            print(f"  - {d['profile_id']}: {d.get('name', '')}")
    elif args.action == "switch":
        set_active_profile_everywhere(args.name)
        config.active_profile = args.name
        config.save()
        print(f"Switched to profile: {args.name}")
    elif args.action == "create":
        db.execute(
            "INSERT OR IGNORE INTO profiles (profile_id, name) VALUES (?, ?)",
            (args.name, args.name),
        )
        ensure_profile_in_json(args.name)
        print(f"Created profile: {args.name}")
