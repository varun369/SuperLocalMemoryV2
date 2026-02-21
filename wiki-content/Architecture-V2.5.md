# SuperLocalMemory V2.5 Architecture — "Your AI Memory Has a Heartbeat"

**Version:** 2.5.0 | **Date:** February 12, 2026 | **Author:** Varun Pratap Bhardwaj

---

## What Changed in v2.5

SuperLocalMemory transforms from **passive storage** (filing cabinet) to **active coordination layer** (nervous system). Every memory write, update, delete, or recall now triggers real-time events visible across all connected tools.

### Before v2.5 (Passive)

Claude or Cursor writes a memory — it is saved silently. No other tool knows it happened.

### After v2.5 (Active)

Every write instantly propagates: the dashboard updates live, the connected agent is registered, and provenance is recorded — all automatically.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ACCESS LAYER                              │
│  MCP Server │ CLI │ REST API │ Skills │ Python Import │ A2A  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                MEMORY STORE                                  │
│  Concurrent read/write with zero "database locked" errors    │
│  Real-time event broadcasting on every operation             │
│  Provenance and agent tracking on every memory               │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    STORAGE LAYER                             │
│  SQLite (single file: ~/.claude-memory/memory.db)            │
│  Full-text search, knowledge graph, identity patterns,       │
│  event log, agent registry, trust signals                    │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    DASHBOARD LAYER                            │
│  Web dashboard with real-time updates                        │
│  Tabs: Graph, Memories, Clusters, Patterns,                  │
│       Timeline, Live Events, Agents, Settings                │
└──────────────────────────────────────────────────────────────┘
```

> For technical details, see our published research: https://zenodo.org/records/18709670

---

## New Capabilities (v2.5)

| Capability | What It Does |
|------------|-------------|
| **Concurrent Write Safety** | Multiple AI tools write simultaneously — zero conflicts, zero errors |
| **Real-Time Events** | Dashboard and connected tools see every write/recall/delete instantly |
| **Agent Tracking** | Know which tools are connected, what they've written, and when |
| **Provenance** | Every memory records which tool created it and via which protocol |
| **Trust Scoring** | Background monitoring of agent behavior patterns (silent collection) |

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

Events are streamed live to the dashboard and available via API polling.

---

## Trust Scoring (Silent Collection — v2.5)

All agents start at full trust. The system silently collects behavioral signals over time. Trust is asymmetric — trust is harder to gain than to lose, which makes the system robust against manipulation.

**Positive signals:** High-importance writes, memories recalled by other agents, consistent behavior patterns.

**Negative signals:** Quick deletes (memory deleted shortly after creation), high-volume write bursts, contradictory content.

**v2.5:** Silent collection only. **v2.6:** Trust-weighted recall ranking + enforcement mode.

---

## API Endpoints

The dashboard exposes 25+ REST endpoints covering: memory CRUD, search, graph data, clusters, stats, timeline, profiles, export/import, backup, real-time event streaming, WebSocket updates, agent list, and trust overview.

---

*SuperLocalMemory V2.5 — Created by Varun Pratap Bhardwaj. MIT License.*
