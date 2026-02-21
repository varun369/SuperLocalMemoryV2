# A2A Integration (Agent-to-Agent Protocol)

**Status:** Planned for v2.8.0 (Q3-Q4 2026)
**Protocol:** A2A v0.3+ (Google/Linux Foundation)
**SDK:** `a2a-sdk` v0.3.22+ (Official Python SDK)

SuperLocalMemory V2 will be the **first local-first memory system** to support both MCP (agent-to-tool) and A2A (agent-to-agent) protocols — enabling true multi-agent collaboration through shared local memory.

**Keywords:** a2a protocol, agent-to-agent, multi-agent, agent collaboration, agent interoperability, google a2a, linux foundation

---

## Why A2A?

### The Problem

You use multiple AI tools simultaneously — Cursor for coding, Claude Desktop for architecture, Continue.dev for code review. Each tool has its own MCP connection to SuperLocalMemory, but **they don't know about each other**.

When Cursor learns you switched to Tailwind CSS, Claude Desktop doesn't know. You have to tell it again.

### The Solution: A2A Protocol

A2A enables **agent-to-agent communication**. When one agent updates memory, all other authorized agents get notified instantly.

```
Before A2A (MCP only):
  Cursor Agent ─────→ SuperLocalMemory ←───── Claude Desktop Agent
  (each works independently, no cross-agent awareness)

After A2A + MCP:
  Cursor Agent ←────→ SuperLocalMemory ←────→ Claude Desktop Agent
  (agents collaborate through shared memory, real-time sync)
```

### MCP vs A2A — Complementary Protocols

| | MCP (Anthropic, 2024) | A2A (Google/LF, 2025) |
|---|---|---|
| **Direction** | Agent → Tool (vertical) | Agent ↔ Agent (horizontal) |
| **Purpose** | AI tool accesses external resources | AI agents discover & collaborate |
| **SuperLocalMemory** | Memory as a tool (remember/recall) | Memory as a collaborative agent |
| **Communication** | Request-response | Stateful tasks, streaming, push notifications |
| **Already in SLM?** | ✅ Yes (since v2.0.0) | ⏳ Planned (v2.8.0) |

**Google explicitly states:** Use MCP for tool access, A2A for agent collaboration. They're designed to work together.

---

## How It Will Work

### 1. Agent Discovery

SuperLocalMemory publishes an **Agent Card** — a machine-readable description of what it can do.

**Endpoint:** `http://localhost:8766/.well-known/agent.json`

```json
{
  "name": "SuperLocalMemory",
  "description": "Local-first persistent memory with knowledge graph, pattern learning, and hybrid search",
  "version": "2.8.0",
  "url": "http://localhost:8766",
  "provider": {
    "organization": "SuperLocalMemory",
    "url": "https://github.com/varun369/SuperLocalMemoryV2"
  },
  "skills": [
    {
      "name": "remember",
      "description": "Store a memory with tags, importance, and project context",
      "inputModes": ["text/plain", "application/json"],
      "outputModes": ["application/json"]
    },
    {
      "name": "recall",
      "description": "Search memories using hybrid search (semantic + FTS5 + graph)",
      "inputModes": ["text/plain"],
      "outputModes": ["application/json"]
    },
    {
      "name": "list_recent",
      "description": "Get recent memories with filtering by tags, project, or importance",
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    },
    {
      "name": "get_status",
      "description": "System health, memory count, graph stats, and pattern insights",
      "inputModes": [],
      "outputModes": ["application/json"]
    }
  ],
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "stateTransitionHistory": true
  },
  "preferredTransport": "jsonrpc",
  "additionalInterfaces": ["grpc"],
  "securitySchemes": ["signed_agent_card"],
  "authentication": {
    "schemes": ["bearer"],
    "credentials": "Local key store (~/.claude-memory/a2a_keys/)"
  }
}
```

Other agents discover SuperLocalMemory by querying this well-known endpoint.

### 2. Task-Based Memory Operations

A2A uses **tasks** as the fundamental unit of work. Memory operations become A2A tasks:

**Remember (Store Memory):**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "id": "task-uuid-123",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Remember: User switched from Bootstrap to Tailwind CSS for the dashboard project"
        },
        {
          "type": "data",
          "data": {
            "tags": ["css", "tailwind", "dashboard"],
            "importance": 7,
            "project": "dashboard-v2"
          }
        }
      ]
    }
  }
}
```

**Recall (Search Memory):**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "id": "task-uuid-456",
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Recall: What CSS framework does the user prefer?"
        }
      ]
    }
  }
}
```

### 3. Task Lifecycle

```
submitted → working → completed
     │          │          │
     │          │          └── Memory stored/results returned
     │          └── Processing (search, graph traversal, etc.)
     └── Task received, validated, queued

Alternative states:
  working → failed      (error during processing)
  submitted → canceled  (client cancels before processing)
```

### 4. Streaming Results

For large recall queries, results stream back in real-time:

```json
// First result
{"jsonrpc": "2.0", "method": "tasks/sendSubscribe", "params": {
  "id": "task-456",
  "message": {"role": "agent", "parts": [
    {"type": "data", "data": {"memory_id": 42, "content": "Switched to Tailwind CSS...", "score": 0.95}}
  ]}
}}

// Second result
{"jsonrpc": "2.0", "method": "tasks/sendSubscribe", "params": {
  "id": "task-456",
  "message": {"role": "agent", "parts": [
    {"type": "data", "data": {"memory_id": 38, "content": "Dashboard uses utility-first...", "score": 0.82}}
  ]}
}}
```

### 5. Real-Time Broadcasting

When Agent A stores a memory, all subscribed agents receive a push notification:

```
Cursor Agent → remember("Switched to Tailwind") → SuperLocalMemory
                                                        │
                                           broadcasts to subscribers
                                                        │
                                    ┌───────────────────┼────────────────────┐
                                    ▼                   ▼                    ▼
                             Claude Desktop      Continue.dev           Aider
                             (updates context)   (adjusts suggestions)  (notes preference)
```

---

## Security Model

### Local-First Authentication

No cloud auth servers. Everything stays on your machine.

**Key Store:** `~/.claude-memory/a2a_keys/`

**Agent Authorization Flow:**
1. New agent connects to SuperLocalMemory A2A server
2. Agent presents its signed Agent Card
3. SuperLocalMemory prompts user: "Agent 'Cursor AI' wants read/write access. Allow?"
4. User approves → agent added to authorized list
5. Future connections authenticated via stored credentials

### Permission Levels

| Level | Can Do | Use Case |
|-------|--------|----------|
| **read** | recall, list_recent, get_status | Agents that only need to read context |
| **write** | read + remember | Agents that actively save memories |
| **admin** | write + build_graph, switch_profile, delete | Trusted primary agent |

### Configuration

**File:** `~/.claude-memory/a2a_agents.json`

```json
{
  "server": {
    "port": 8766,
    "transport": ["jsonrpc", "grpc"],
    "auto_start": false
  },
  "authorized_agents": [
    {
      "agent_id": "cursor-ai-abc123",
      "name": "Cursor AI",
      "permissions": ["read", "write"],
      "authorized_date": "2026-02-11T10:30:00Z",
      "last_seen": "2026-02-11T14:22:00Z"
    },
    {
      "agent_id": "claude-desktop-def456",
      "name": "Claude Desktop",
      "permissions": ["read", "write", "admin"],
      "authorized_date": "2026-02-11T10:30:00Z",
      "last_seen": "2026-02-11T14:25:00Z"
    }
  ],
  "broadcasting": {
    "enabled": true,
    "filter_by_project": true,
    "max_subscribers": 10
  }
}
```

### Audit Logging

Every A2A interaction is logged:

**File:** `~/.claude-memory/a2a_audit.log`

```
2026-02-11 14:22:00 | cursor-ai | remember | "Switched to Tailwind CSS" | SUCCESS
2026-02-11 14:22:01 | broadcast | claude-desktop | memory_update | id=42
2026-02-11 14:23:15 | claude-desktop | recall | "CSS framework preference" | 3 results
```

---

## Technical Implementation

### Dependencies (Optional — A2A only)

```bash
# Install A2A support
pip install a2a-sdk>=0.3.22 grpcio>=1.60.0 protobuf>=4.25.0
```

**Core SuperLocalMemory requires NO additional dependencies.** A2A is fully optional.

### New Files (v2.8.0)

```
src/a2a_server.py          # A2A gRPC/JSON-RPC server (500-700 lines)
src/a2a_auth.py            # Agent authentication & authorization (200-300 lines)
bin/slm-a2a                # CLI wrapper to start/stop A2A server
configs/a2a_config.json    # Default A2A configuration
```

### CLI Commands

```bash
# Start A2A server
slm a2a start

# Stop A2A server
slm a2a stop

# Show A2A status
slm a2a status

# List authorized agents
slm a2a agents

# Authorize new agent
slm a2a authorize <agent-card-url>

# Revoke agent access
slm a2a revoke <agent-id>
```

### Python API

```python
from a2a_server import A2AMemoryAgent

# Start A2A server programmatically
agent = A2AMemoryAgent(port=8766)
agent.start()

# Server runs alongside MCP server
# MCP: port 8765 (tool access)
# A2A: port 8766 (agent collaboration)
```

---

## Relationship to Existing Layers

A2A (Layer 10) sits on top of the existing architecture. It uses Layers 1-9 internally but never modifies them.

```
Layer 10: A2A Agent Collaboration
  ├── Uses Layer 8 (Hybrid Search) for recall operations
  ├── Uses Layer 3 (Knowledge Graph) for graph-aware search
  ├── Uses Layer 4 (Pattern Learning) for identity context
  └── Uses Layer 1 (Raw Storage) for remember operations

Layer 6: MCP Integration (unchanged)
  └── Agent-to-tool communication continues as before
```

**Key principle:** If A2A server is not running, everything works exactly as before. A2A is purely additive.

---

## A2A Protocol Background

### What is A2A?

The **Agent-to-Agent (A2A) Protocol** was launched by Google in April 2025 and is now an open-source project under the Linux Foundation. It enables AI agents from different vendors and frameworks to discover each other and collaborate on tasks.

### Current Status (Feb 2026)

- **Version:** 0.3 (July 2025)
- **Adoption:** 150+ organizations
- **Backers:** Google, Microsoft, Cisco, Salesforce, UiPath, Cohere, ServiceNow
- **SDKs:** Python, JavaScript, Java, Go, .NET
- **Spec:** [a2a-protocol.org/latest/specification](https://a2a-protocol.org/latest/specification/)
- **GitHub:** [github.com/a2aproject/A2A](https://github.com/a2aproject/A2A) (21,800+ stars)

### Industry Context

- **Gartner:** 40% of enterprise apps will feature AI agents by 2026 (up from <5% in 2025)
- **29% of enterprises** already running agentic AI in production (2025 survey)
- Multi-agent collaboration entering operational phase in 2026

---

## FAQ

**Q: Does A2A replace MCP?**
No. MCP handles agent-to-tool communication (Cursor accessing memory database). A2A handles agent-to-agent communication (Cursor telling Claude Desktop about a decision). You need both.

**Q: Is A2A required to use SuperLocalMemory?**
No. A2A is completely optional and opt-in. All existing MCP, CLI, and Skills functionality remains unchanged.

**Q: Does A2A send my data to the cloud?**
No. A2A in SuperLocalMemory runs 100% locally on `localhost:8766`. No data leaves your machine.

**Q: Which agents support A2A?**
The protocol is early but growing fast. As of Feb 2026, SDKs exist for Python, JavaScript, Java, Go, and .NET. Major AI frameworks are adding A2A support.

**Q: Can I control which agents access my memory?**
Yes. Every agent must be explicitly authorized by you. You control permissions (read-only, read-write, admin) per agent.

---

## Related Pages

- [[Architecture-V2.5]] - Full architecture overview
- [[MCP-Integration]] - MCP protocol setup (agent-to-tool)
- [[Roadmap]] - v2.8 A2A milestone details
- [[Why-Local-Matters]] - Privacy and local-first philosophy

---

[[← Back to Home|Home]]

---

**Created by Varun Pratap Bhardwaj**
*Solution Architect • SuperLocalMemory V2*
