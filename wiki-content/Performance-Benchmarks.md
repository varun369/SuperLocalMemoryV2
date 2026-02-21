# Performance Benchmarks

Measured performance of SuperLocalMemory V2 on real hardware. Results reflect real-world use cases.

---

## Search Latency

How fast SuperLocalMemory finds your memories.

| Database Size | Performance |
|---------------|------------|
| Under 500 memories | Sub-100ms search — faster than you can blink |
| Around 1,000 memories | Sub-200ms — fully interactive response |
| 5,000 memories | Seconds range — optional indexes provide acceleration |

**What this means:** For typical personal use (under 500 memories), search is effectively instant. Beyond 1,000 memories, optional acceleration indexes are available.

---

## Concurrent Write Throughput

Multiple AI tools writing to memory simultaneously — the "database locked" problem, solved.

| Scenario | Result |
|----------|--------|
| 1-2 agents writing simultaneously | High throughput, sub-15ms latency, zero errors |
| 5 agents writing simultaneously | Moderate throughput, low latency, zero errors |
| 10 agents writing simultaneously | Stable throughput, zero errors |

**What this means:** Zero "database is locked" errors, even with 10 AI tools writing at the same time.

---

## Storage Efficiency

How much disk space your memories use.

| Scale | Approximate Size |
|-------|-----------------|
| 1,000 memories | ~1.5 MB |
| 10,000 memories | ~14 MB |

**What this means:** Your entire AI memory history takes less space than a single high-res photo.

---

## Knowledge Graph Construction

Building the relationship graph from your memories.

| Scale | Build Time |
|-------|-----------|
| Under 100 memories | Under 1 second |
| Around 1,000 memories | Several seconds |
| 5,000 memories | Several minutes |

**What this means:** Graph builds quickly for most users. The system consistently discovers natural topic communities across your memories. At 5,000 memories (the design limit), a full rebuild is an explicit design choice balancing graph utility against compute cost.

> **Graph Scaling:** Knowledge graph features work best with up to 10,000 memories. For larger databases, the system uses intelligent sampling (most recent + highest importance memories) for graph construction. Core search and memory storage have no upper limit.

---

## Trust Scoring — Memory Poisoning Defense

Bayesian trust scoring detects malicious agents attempting to corrupt your memory.

The trust system achieves strong separation between honest and malicious agents. Even a sophisticated "sleeper" attack — where an agent behaves well to build trust, then turns hostile — is detected with a significant trust drop. Zero false positives on benign agents.

---

## Layer Contribution Analysis

The core retrieval system achieves high precision — the first relevant result is at position 1 for the vast majority of queries. The graph and pattern layers provide structural enrichment (clustering, relationship navigation, coding preferences) rather than modifying search ranking directly.

---

## Coming Soon: LoCoMo Benchmark

We are currently running the [LoCoMo benchmark](https://snap-research.github.io/locomo/) (Snap Research, ACL 2024) — a standardized evaluation for long-conversation memory systems with multi-hop, temporal, and adversarial question types. Results will be published here when complete.

---

## Methodology

- All benchmarks run on local hardware with no cloud dependencies
- Each measurement repeated multiple times with statistical aggregation
- Database populated with realistic synthetic memories across diverse topics
- Tests run on clean database instances for each benchmark scenario

---

**See also:** [[Architecture-V2.5]] | [[Home]]
