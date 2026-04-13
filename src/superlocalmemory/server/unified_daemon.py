# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SLM Unified Daemon — single FastAPI process for ALL routes.

Replaces the dual-process architecture (stdlib daemon + FastAPI dashboard).
One MemoryEngine singleton shared by CLI, MCP, Dashboard, and Mesh routes.

Architecture:
  slm serve       → starts unified daemon (uvicorn on port 8765)
  slm remember X  → HTTP POST to daemon → instant
  slm recall X    → HTTP GET from daemon → instant
  slm dashboard   → opens browser to http://localhost:8765
  slm serve stop  → POST /stop → graceful uvicorn shutdown

Port 8765: primary (dashboard + API + daemon routes)
Port 8767: TCP redirect for backward compat (deprecated)

24/7 by default. Opt-in auto-kill: --idle-timeout=1800

Part of Qualixar | Author: Varun Pratap Bhardwaj
License: Elastic-2.0
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import signal
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel

logger = logging.getLogger("superlocalmemory.unified_daemon")

_DEFAULT_PORT = 8765
_LEGACY_PORT = 8767
_PID_FILE = Path.home() / ".superlocalmemory" / "daemon.pid"
_PORT_FILE = Path.home() / ".superlocalmemory" / "daemon.port"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RememberRequest(BaseModel):
    content: str
    tags: str = ""


class ObserveRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Observation debounce buffer (migrated from daemon.py)
# ---------------------------------------------------------------------------

class ObserveBuffer:
    """Thread-safe debounce buffer for observation processing.

    Buffers observations for a configurable window, deduplicates by content
    hash, then processes as a batch via the singleton MemoryEngine.
    """

    def __init__(self, debounce_sec: float = 3.0):
        self._debounce_sec = debounce_sec
        self._buffer: list[str] = []
        self._seen: set[str] = set()
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._engine = None

    def set_engine(self, engine) -> None:
        self._engine = engine

    def enqueue(self, content: str) -> dict:
        content_hash = hashlib.md5(content.encode()).hexdigest()
        with self._lock:
            if content_hash in self._seen:
                return {"captured": False, "reason": "duplicate within debounce window"}
            self._seen.add(content_hash)
            self._buffer.append(content)
            buf_size = len(self._buffer)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_sec, self._flush)
            self._timer.daemon = True
            self._timer.start()
        return {"captured": True, "queued": True, "buffer_size": buf_size}

    def _flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            batch = list(self._buffer)
            self._buffer.clear()
            self._seen.clear()
            self._timer = None

        if self._engine is None:
            return

        try:
            from superlocalmemory.hooks.auto_capture import AutoCapture
            auto = AutoCapture(engine=self._engine)
            for content in batch:
                try:
                    decision = auto.evaluate(content)
                    if decision.capture:
                        auto.capture(content, category=decision.category)
                except Exception:
                    pass
            logger.info("Observe debounce: processed %d observations", len(batch))
        except Exception:
            pass

    def flush_sync(self) -> None:
        """Force flush for shutdown."""
        if self._timer is not None:
            self._timer.cancel()
        self._flush()


_observe_buffer = ObserveBuffer(
    debounce_sec=float(os.environ.get("SLM_OBSERVE_DEBOUNCE_SEC", "3.0"))
)


# ---------------------------------------------------------------------------
# Idle watchdog (opt-in)
# ---------------------------------------------------------------------------

_last_activity = time.monotonic()


def _start_idle_watchdog(timeout_sec: int) -> None:
    """Auto-shutdown after idle. Only if timeout > 0."""
    if timeout_sec <= 0:
        return

    def _watch():
        while True:
            time.sleep(30)
            idle = time.monotonic() - _last_activity
            if idle > timeout_sec:
                logger.info("Daemon idle for %ds, shutting down", int(idle))
                os.kill(os.getpid(), signal.SIGTERM)
                break

    t = threading.Thread(target=_watch, daemon=True, name="idle-watchdog")
    t.start()


# ---------------------------------------------------------------------------
# Legacy port TCP redirect (backward compat for port 8767)
# ---------------------------------------------------------------------------

async def _start_legacy_redirect(primary_port: int, legacy_port: int) -> None:
    """Start TCP redirect from legacy_port → primary_port.

    Simple byte-level proxy. No shared event loop with uvicorn — runs
    in its own asyncio task within the same loop.
    """
    _deprecation_warned = False

    async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        nonlocal _deprecation_warned
        if not _deprecation_warned:
            logger.warning(
                "Request on deprecated port %d. Update config to use port %d.",
                legacy_port, primary_port,
            )
            _deprecation_warned = True

        try:
            upstream_r, upstream_w = await asyncio.open_connection("127.0.0.1", primary_port)
            await asyncio.gather(
                _pipe(reader, upstream_w),
                _pipe(upstream_r, writer),
            )
        except Exception:
            pass
        finally:
            writer.close()

    async def _pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter):
        try:
            while True:
                data = await src.read(8192)
                if not data:
                    break
                dst.write(data)
                await dst.drain()
        except Exception:
            pass
        finally:
            try:
                dst.close()
            except Exception:
                pass

    try:
        server = await asyncio.start_server(_handle_client, "127.0.0.1", legacy_port)
        logger.info("Legacy redirect: port %d → %d (deprecated)", legacy_port, primary_port)
        await server.serve_forever()
    except OSError:
        logger.info("Port %d in use (old daemon?), skipping legacy redirect", legacy_port)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize engine, workers, and optional services on startup."""
    global _last_activity

    engine = None
    config = None

    try:
        from superlocalmemory.core.config import SLMConfig
        from superlocalmemory.core.engine import MemoryEngine

        config = SLMConfig.load()
        engine = MemoryEngine(config)
        engine.initialize()

        # Enforce WAL mode for concurrent reads
        db = getattr(engine, '_db', None) or getattr(engine, '_storage', None)
        if db and hasattr(db, 'execute'):
            try:
                db.execute("PRAGMA journal_mode=WAL")
                db.execute("PRAGMA synchronous=NORMAL")
            except Exception:
                pass

        application.state.engine = engine
        application.state.config = config
        logger.info("Unified daemon: MemoryEngine initialized (mode=%s)", config.mode.value)

        # Set up observe buffer
        _observe_buffer.set_engine(engine)

        # Pre-warm workers (background)
        from superlocalmemory.core.worker_pool import WorkerPool
        WorkerPool.shared().warmup()

        # Force reranker warmup
        retrieval_eng = getattr(engine, '_retrieval_engine', None)
        if retrieval_eng:
            reranker = getattr(retrieval_eng, '_reranker', None)
            if reranker and hasattr(reranker, 'warmup_sync'):
                reranker.warmup_sync(timeout=120)

    except Exception as exc:
        logger.warning("Engine init failed: %s", exc)
        application.state.engine = None
        application.state.config = None

    application.state.observe_buffer = _observe_buffer

    # Phase B: Start health monitor
    try:
        from superlocalmemory.core.health_monitor import HealthMonitor
        health_config = getattr(config, 'health', None)
        monitor = HealthMonitor(
            global_rss_budget_mb=getattr(health_config, 'global_rss_budget_mb', 4096) if health_config else 4096,
            heartbeat_timeout_sec=getattr(health_config, 'heartbeat_timeout_sec', 60) if health_config else 60,
            check_interval_sec=getattr(health_config, 'health_check_interval_sec', 30) if health_config else 30,
            enable_structured_logging=getattr(health_config, 'enable_structured_logging', True) if health_config else True,
        )
        monitor.start()
        application.state.health_monitor = monitor
    except Exception as exc:
        logger.debug("Health monitor init: %s", exc)
        application.state.health_monitor = None

    # Phase C: Start mesh broker
    try:
        mesh_enabled = getattr(config, 'mesh_enabled', True) if config else True
        if mesh_enabled:
            from superlocalmemory.mesh.broker import MeshBroker
            db_path = config.db_path if config else Path.home() / ".superlocalmemory" / "memory.db"
            mesh_broker = MeshBroker(str(db_path))
            mesh_broker.start_cleanup()
            application.state.mesh_broker = mesh_broker
            logger.info("Mesh broker started")
        else:
            application.state.mesh_broker = None
    except Exception as exc:
        logger.debug("Mesh broker init: %s", exc)
        application.state.mesh_broker = None

    # Start idle watchdog if configured
    idle_timeout = int(os.environ.get("SLM_DAEMON_IDLE_TIMEOUT", "0"))
    if config and hasattr(config, 'daemon_idle_timeout'):
        idle_timeout = idle_timeout or config.daemon_idle_timeout
    _start_idle_watchdog(idle_timeout)

    # Start legacy port redirect
    enable_legacy = os.environ.get("SLM_DISABLE_LEGACY_PORT", "").lower() not in ("1", "true")
    if enable_legacy:
        asyncio.create_task(_start_legacy_redirect(_DEFAULT_PORT, _LEGACY_PORT))

    _last_activity = time.monotonic()
    logger.info("Unified daemon ready on port %d (24/7 mode)" if idle_timeout <= 0
                else "Unified daemon ready on port %d (idle timeout: %ds)",
                _DEFAULT_PORT, idle_timeout)

    yield

    # Shutdown
    _observe_buffer.flush_sync()
    if engine is not None:
        try:
            engine.close()
        except Exception:
            pass
    _PID_FILE.unlink(missing_ok=True)
    _PORT_FILE.unlink(missing_ok=True)
    logger.info("Unified daemon shutdown complete")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create the unified FastAPI application."""
    from superlocalmemory.server.routes.helpers import SLM_VERSION

    application = FastAPI(
        title="SuperLocalMemory V3 — Unified Daemon",
        description="Memory + Dashboard + Mesh — one process, one engine.",
        version=SLM_VERSION,
        lifespan=lifespan,
    )

    # -- Middleware --
    from superlocalmemory.server.security_middleware import SecurityHeadersMiddleware
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8765", "http://127.0.0.1:8765",
            "http://localhost:8767", "http://127.0.0.1:8767",  # legacy compat
            "http://localhost:8417", "http://127.0.0.1:8417",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-SLM-API-Key"],
    )

    # -- Register all dashboard routes (from existing api.py) --
    _register_dashboard_routes(application)

    # -- Mesh routes (Phase C) --
    try:
        from superlocalmemory.server.routes.mesh import router as mesh_router
        application.include_router(mesh_router)
    except ImportError:
        pass

    # -- Entity routes (Phase D) --
    try:
        from superlocalmemory.server.routes.entity import router as entity_router
        application.include_router(entity_router)
    except ImportError:
        pass

    # -- Ingestion route (Phase E) --
    try:
        from superlocalmemory.server.routes.ingest import router as ingest_router
        application.include_router(ingest_router)
    except ImportError:
        pass

    # -- Daemon-specific routes --
    _register_daemon_routes(application)

    return application


def _register_dashboard_routes(application: FastAPI) -> None:
    """Mount all existing dashboard routes from server/routes/*.

    Extracted from api.py's create_app() to avoid duplicate MemoryEngine.
    """
    from superlocalmemory.server.api import UI_DIR

    # Rate limiting (graceful)
    try:
        from superlocalmemory.infra.rate_limiter import RateLimiter
        _write_limiter = RateLimiter(max_requests=30, window_seconds=60)
        _read_limiter = RateLimiter(max_requests=120, window_seconds=60)

        @application.middleware("http")
        async def rate_limit_middleware(request, call_next):
            client_ip = request.client.host if request.client else "unknown"
            is_write = request.method in ("POST", "PUT", "DELETE", "PATCH")
            limiter = _write_limiter if is_write else _read_limiter
            allowed, remaining = limiter.is_allowed(client_ip)
            if not allowed:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many requests."},
                    headers={"Retry-After": str(limiter.window_seconds)},
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
    except (ImportError, Exception):
        pass

    # Auth middleware (graceful)
    try:
        from superlocalmemory.infra.auth_middleware import check_api_key

        @application.middleware("http")
        async def auth_middleware(request, call_next):
            is_write = request.method in ("POST", "PUT", "DELETE", "PATCH")
            headers = dict(request.headers)
            if not check_api_key(headers, is_write=is_write):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid or missing API key."},
                )
            return await call_next(request)
    except (ImportError, Exception):
        pass

    # Static files
    from fastapi.staticfiles import StaticFiles
    UI_DIR.mkdir(exist_ok=True)
    application.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

    # Route modules
    from superlocalmemory.server.routes.memories import router as memories_router
    from superlocalmemory.server.routes.stats import router as stats_router
    from superlocalmemory.server.routes.profiles import router as profiles_router
    from superlocalmemory.server.routes.backup import router as backup_router
    from superlocalmemory.server.routes.data_io import router as data_io_router
    from superlocalmemory.server.routes.events import (
        router as events_router, register_event_listener,
    )
    from superlocalmemory.server.routes.agents import router as agents_router
    from superlocalmemory.server.routes.ws import router as ws_router, manager as ws_manager
    from superlocalmemory.server.routes.v3_api import router as v3_router
    from superlocalmemory.server.routes.adapters import router as adapters_router

    application.include_router(memories_router)
    application.include_router(stats_router)
    application.include_router(profiles_router)
    application.include_router(backup_router)
    application.include_router(data_io_router)
    application.include_router(events_router)
    application.include_router(agents_router)
    application.include_router(ws_router)
    application.include_router(v3_router)
    application.include_router(adapters_router)

    # v3.4.1 chat SSE
    for _mod_name in ("chat",):
        try:
            _mod = __import__(
                f"superlocalmemory.server.routes.{_mod_name}", fromlist=["router"],
            )
            application.include_router(_mod.router)
        except (ImportError, Exception):
            pass

    # Optional routers
    for _mod_name in ("learning", "lifecycle", "behavioral", "compliance", "insights", "timeline"):
        try:
            _mod = __import__(
                f"superlocalmemory.server.routes.{_mod_name}", fromlist=["router"],
            )
            application.include_router(_mod.router)
        except (ImportError, Exception):
            pass

    # Wire WebSocket manager
    import superlocalmemory.server.routes.profiles as _profiles_mod
    import superlocalmemory.server.routes.data_io as _data_io_mod
    _profiles_mod.ws_manager = ws_manager
    _data_io_mod.ws_manager = ws_manager

    # Root page
    from fastapi.responses import HTMLResponse

    @application.get("/", response_class=HTMLResponse)
    async def root():
        index_path = UI_DIR / "index.html"
        if not index_path.exists():
            return (
                "<html><head><title>SuperLocalMemory V3</title></head>"
                "<body style='font-family:Arial;padding:40px'>"
                "<h1>SuperLocalMemory V3 — Unified Daemon</h1>"
                "<p><a href='/docs'>API Documentation</a></p>"
                "</body></html>"
            )
        return index_path.read_text()

    # Startup event for event listener
    @application.on_event("startup")
    async def startup_event():
        register_event_listener()


def _register_daemon_routes(application: FastAPI) -> None:
    """Add daemon-specific routes for CLI integration."""
    global _last_activity

    @application.get("/health")
    async def health():
        _update_activity()
        engine = application.state.engine
        return {
            "status": "ok",
            "pid": os.getpid(),
            "engine": "initialized" if engine else "unavailable",
            "version": getattr(application, 'version', 'unknown'),
        }

    @application.get("/recall")
    async def recall(q: str = "", limit: int = 20):
        _update_activity()
        engine = application.state.engine
        if engine is None:
            raise HTTPException(503, detail="Engine not initialized")
        try:
            response = engine.recall(q, limit=limit)
            results = [
                {
                    "content": r.fact.content,
                    "score": round(r.score, 4),
                    "fact_type": getattr(r.fact.fact_type, 'value', str(r.fact.fact_type)),
                    "fact_id": r.fact.fact_id,
                }
                for r in response.results
            ]
            return {
                "results": results,
                "count": len(results),
                "query_type": response.query_type,
                "retrieval_time_ms": round(response.retrieval_time_ms, 1),
            }
        except Exception as exc:
            raise HTTPException(500, detail=str(exc))

    @application.post("/remember")
    async def remember(req: RememberRequest):
        _update_activity()
        engine = application.state.engine
        if engine is None:
            raise HTTPException(503, detail="Engine not initialized")
        try:
            metadata = {"tags": req.tags} if req.tags else {}
            fact_ids = engine.store(req.content, metadata=metadata)
            return {"fact_ids": fact_ids, "count": len(fact_ids)}
        except Exception as exc:
            raise HTTPException(500, detail=str(exc))

    @application.post("/observe")
    async def observe(req: ObserveRequest):
        _update_activity()
        result = _observe_buffer.enqueue(req.content)
        return result

    @application.get("/status")
    async def status():
        _update_activity()
        engine = application.state.engine
        uptime = time.monotonic() - _last_activity
        fact_count = engine.fact_count if engine else 0
        mode = engine._config.mode.value if engine and hasattr(engine, '_config') else "unknown"
        return {
            "status": "running",
            "pid": os.getpid(),
            "uptime_s": round(time.monotonic() - (_start_time or time.monotonic())),
            "mode": mode,
            "fact_count": fact_count,
            "idle_s": round(time.monotonic() - _last_activity),
            "port": _DEFAULT_PORT,
            "legacy_port": _LEGACY_PORT,
        }

    @application.get("/list")
    async def list_facts(limit: int = 50):
        _update_activity()
        engine = application.state.engine
        if engine is None:
            raise HTTPException(503, detail="Engine not initialized")
        try:
            facts = engine.list_facts(limit=limit)
            items = [
                {
                    "content": f.content[:100],
                    "fact_type": getattr(f.fact_type, 'value', str(f.fact_type)),
                    "created_at": (f.created_at or "")[:19],
                    "fact_id": f.fact_id,
                }
                for f in facts
            ]
            return {"results": items, "count": len(items)}
        except Exception as exc:
            raise HTTPException(500, detail=str(exc))

    @application.post("/stop")
    async def stop():
        """Graceful shutdown via uvicorn's mechanism."""
        logger.info("Stop requested via API")
        _observe_buffer.flush_sync()
        # Signal uvicorn to shut down gracefully
        os.kill(os.getpid(), signal.SIGTERM)
        return {"status": "stopping"}


def _update_activity():
    global _last_activity
    _last_activity = time.monotonic()


_start_time: float | None = None


# ---------------------------------------------------------------------------
# Server entry point
# ---------------------------------------------------------------------------

def _start_memory_watchdog() -> None:
    """v3.4.7: Background watchdog that kills child workers exceeding memory limit.

    Prevents the orphan worker memory explosion that caused 16GB+ RAM usage.
    Checks every 60 seconds. Kills workers over 2GB RSS. Auto-restarts them
    on next request (workers are lazy-spawned).
    """
    import threading

    MAX_WORKER_MB = 2048  # 2GB per worker — kill if exceeded

    def watchdog_loop():
        while True:
            time.sleep(60)
            try:
                import psutil
                parent = psutil.Process(os.getpid())
                for child in parent.children(recursive=True):
                    try:
                        rss_mb = child.memory_info().rss / (1024 * 1024)
                        if rss_mb > MAX_WORKER_MB:
                            logger.warning(
                                "Memory watchdog: killing %s (PID %d, %.0f MB > %d MB limit)",
                                child.name(), child.pid, rss_mb, MAX_WORKER_MB,
                            )
                            child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except ImportError:
                pass  # psutil not available — watchdog disabled
            except Exception as exc:
                logger.debug("Memory watchdog error: %s", exc)

    t = threading.Thread(target=watchdog_loop, daemon=True, name="memory-watchdog")
    t.start()
    logger.info("Memory watchdog started (limit: %d MB per worker)", MAX_WORKER_MB)


def start_server(port: int = _DEFAULT_PORT) -> None:
    """Start the unified daemon. Blocks until stopped."""
    global _start_time
    import uvicorn

    _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(os.getpid()))
    _PORT_FILE.write_text(str(port))
    _start_time = time.monotonic()

    # v3.4.7: Start memory watchdog to prevent runaway workers
    _start_memory_watchdog()

    log_dir = Path.home() / ".superlocalmemory" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    config = uvicorn.Config(
        app="superlocalmemory.server.unified_daemon:create_app",
        factory=True,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        timeout_graceful_shutdown=10,
    )
    server = uvicorn.Server(config)

    try:
        server.run()
    finally:
        _PID_FILE.unlink(missing_ok=True)
        _PORT_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    port = _DEFAULT_PORT
    for arg in sys.argv:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])
    if "--start" in sys.argv:
        start_server(port=port)
    else:
        print("Usage: python -m superlocalmemory.server.unified_daemon --start [--port=8765]")
