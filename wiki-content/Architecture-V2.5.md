# SuperLocalMemory V2.5 Architecture — "Your AI Memory Has a Heartbeat"

**Version:** 2.5.0 | **Date:** February 12, 2026 | **Author:** Varun Pratap Bhardwaj

---

## What Changed in v2.5

SuperLocalMemory transforms from **passive storage** (filing cabinet) to **active coordination layer** (nervous system). Every memory write, update, delete, or recall now triggers real-time events visible across all connected tools.

### Before v2.5 (Passive)
```
Claude writes memory → saved to SQLite → done (silent)
Cursor reads memory → returned → done (silent)
```

### After v2.5 (Active)
```
Claude writes memory → saved to SQLite → Event Bus fires
                                           ├── SSE → Dashboard shows it live
                                           ├── Agent registered in registry
                                           ├── Trust signal recorded
                                           ├── Provenance tracked
                                           └── Webhook dispatched (if configured)
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ACCESS LAYER                              │
│  MCP Server │ CLI │ REST API │ Skills │ Python Import │ A2A  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                MEMORY STORE V2                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  DbConnectionManager (Singleton)                     │    │
│  │  ├── WAL Mode (concurrent reads + serialized writes) │    │
│  │  ├── Busy Timeout (5s wait, not fail)                │    │
│  │  ├── Thread-Local Read Pool                          │    │
│  │  ├── Serialized Write Queue (threading.Queue)        │    │
│  │  └── Post-Write Hooks → Event Bus                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  On every write:                                             │
│  ├── EventBus.emit() → memory_events table + SSE + WS + WH  │
│  ├── ProvenanceTracker → created_by, source_protocol columns │
│  ├── AgentRegistry → agent tracking + write/recall counters  │
│  └── TrustScorer → signal collection (silent, no enforcement)│
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    STORAGE LAYER                             │
│  SQLite (single file: ~/.claude-memory/memory.db)            │
│                                                              │
│  Tables:                                                     │
│  ├── memories (+ provenance columns: created_by,             │
│  │            source_protocol, trust_score, provenance_chain) │
│  ├── memory_events (event log with tiered retention)         │
│  ├── subscriptions (durable + ephemeral event subscriptions) │
│  ├── agent_registry (connected agents + statistics)          │
│  ├── trust_signals (trust signal audit trail)                │
│  ├── graph_nodes, graph_edges, graph_clusters (knowledge graph)│
│  ├── identity_patterns (learned preferences)                 │
│  ├── sessions, creator_metadata                              │
│  └── memories_fts (FTS5 full-text search index)              │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    DASHBOARD LAYER                            │
│  FastAPI UI Server (modular routes)                          │
│  ├── 8 route modules in routes/ directory                    │
│  ├── 28 API endpoints                                        │
│  ├── SSE /events/stream (real-time, cross-process)           │
│  ├── WebSocket /ws/updates                                   │
│  ├── 13 modular JS files in ui/js/                           │
│  └── 8 dashboard tabs (Graph, Memories, Clusters, Patterns,  │
│       Timeline, Live Events, Agents, Settings)               │
└──────────────────────────────────────────────────────────────┘
```

---

## New Components (v2.5)

| Component | File | Purpose |
|-----------|------|---------|
| **DbConnectionManager** | `src/db_connection_manager.py` | WAL mode, busy timeout, read pool, write queue, post-write hooks |
| **EventBus** | `src/event_bus.py` | Event emission, persistence, in-memory buffer, tiered retention |
| **SubscriptionManager** | `src/subscription_manager.py` | Durable + ephemeral event subscriptions with filters |
| **WebhookDispatcher** | `src/webhook_dispatcher.py` | Background HTTP POST delivery with retry logic |
| **AgentRegistry** | `src/agent_registry.py` | Agent tracking, write/recall counters, protocol detection |
| **ProvenanceTracker** | `src/provenance_tracker.py` | Memory origin tracking (who, how, trust, lineage) |
| **TrustScorer** | `src/trust_scorer.py` | Bayesian trust scoring with decay, burst detection |

## New Database Tables (v2.5)

| Table | Columns | Purpose |
|-------|---------|---------|
| `memory_events` | id, event_type, memory_id, source_agent, source_protocol, payload, importance, tier, created_at | Event log with tiered retention |
| `subscriptions` | id, subscriber_id, channel, filter, webhook_url, durable, last_event_id | Event subscriptions |
| `agent_registry` | id, agent_id, agent_name, protocol, first_seen, last_seen, memories_written, memories_recalled, trust_score, metadata | Agent tracking |
| `trust_signals` | id, agent_id, signal_type, delta, old_score, new_score, context, created_at | Trust audit trail |

## New Columns on `memories` Table (v2.5)

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `created_by` | TEXT | 'user' | Agent ID that created this memory |
| `source_protocol` | TEXT | 'cli' | Protocol used (mcp, cli, rest, python, a2a) |
| `trust_score` | REAL | 1.0 | Trust score at creation time |
| `provenance_chain` | TEXT | '[]' | JSON derivation lineage |

---

## Event Types

| Event | Trigger |
|-------|---------|
| `memory.created` | New memory written |
| `memory.updated` | Existing memory modified |
| `memory.deleted` | Memory removed |
| `memory.recalled` | Memory retrieved by an agent |
| `graph.updated` | Knowledge graph rebuilt |
| `pattern.learned` | New pattern detected |
| `agent.connected` | New agent connects |
| `agent.disconnected` | Agent disconnects |

## Event Retention Tiers

| Tier | Window | Kept |
|------|--------|------|
| Hot | 0-48h | All events |
| Warm | 2-14d | Importance >= 5 only |
| Cold | 14-30d | Daily aggregates |
| Archive | 30d+ | Pruned (stats in pattern_learner) |

---

## Trust Scoring (Silent Collection — v2.5)

All agents start at trust 1.0. Signals adjust the score with a Bayesian decay factor that stabilizes over time. Trust is deliberately asymmetric — negative signals carry larger magnitude, making trust harder to gain than to lose.

**Positive signals:** High-importance writes, memories recalled by other agents, consistent behavior patterns.

**Negative signals:** Quick deletes (memory deleted shortly after creation), high-volume write bursts, contradictory content.

**v2.5:** Silent collection only. **v2.6:** Trust-weighted recall ranking + enforcement mode.

---

## API Endpoints (28 total)

| Route | Method | Module | Purpose |
|-------|--------|--------|---------|
| `/` | GET | ui_server.py | Dashboard |
| `/health` | GET | ui_server.py | Health check |
| `/api/memories` | GET | routes/memories.py | List memories |
| `/api/graph` | GET | routes/memories.py | Knowledge graph data |
| `/api/search` | POST | routes/memories.py | Semantic search |
| `/api/clusters` | GET | routes/memories.py | Cluster info |
| `/api/clusters/{id}` | GET | routes/memories.py | Cluster detail |
| `/api/stats` | GET | routes/stats.py | System statistics |
| `/api/timeline` | GET | routes/stats.py | Timeline aggregation |
| `/api/patterns` | GET | routes/stats.py | Learned patterns |
| `/api/profiles` | GET | routes/profiles.py | List profiles |
| `/api/profiles/{n}/switch` | POST | routes/profiles.py | Switch profile |
| `/api/profiles/create` | POST | routes/profiles.py | Create profile |
| `/api/profiles/{n}` | DELETE | routes/profiles.py | Delete profile |
| `/api/export` | GET | routes/data_io.py | Export memories |
| `/api/import` | POST | routes/data_io.py | Import memories |
| `/api/backup/*` | GET/POST | routes/backup.py | Backup management |
| `/events/stream` | GET | routes/events.py | SSE real-time stream |
| `/api/events` | GET | routes/events.py | Event polling |
| `/api/events/stats` | GET | routes/events.py | Event statistics |
| `/api/agents` | GET | routes/agents.py | Agent list |
| `/api/agents/stats` | GET | routes/agents.py | Agent statistics |
| `/api/trust/stats` | GET | routes/agents.py | Trust overview |
| `/api/trust/signals/{id}` | GET | routes/agents.py | Agent trust signals |
| `/ws/updates` | WS | routes/ws.py | WebSocket |

---

*SuperLocalMemory V2.5 — Created by Varun Pratap Bhardwaj. MIT License.*
