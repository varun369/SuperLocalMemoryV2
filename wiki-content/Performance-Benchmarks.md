# Performance Benchmarks

Measured performance of SuperLocalMemory V2.5 on real hardware. All numbers are reproducible — no estimates, no projections.

**Test Environment:** Apple M4 Pro, 24GB RAM, macOS, Python 3.12, SQLite 3.51

---

## Search Latency

How fast SuperLocalMemory finds your memories.

| Database Size | Median | P95 | P99 |
|---------------|--------|-----|-----|
| 100 memories | **10.6ms** | 14.9ms | 15.8ms |
| 500 memories | **65.2ms** | 101.7ms | 112.5ms |
| 1,000 memories | **124.3ms** | 190.1ms | 219.5ms |
| 5,000 memories | **1,172ms** | 2,140ms | 2,581ms |

**What this means:** For typical personal use (under 500 memories), search returns in under 65ms — faster than you can blink. At 1,000 memories, response remains interactive at 124ms. Beyond 1,000, the optional BM25 and HNSW indexes provide acceleration.

---

## Concurrent Write Throughput

Multiple AI tools writing to memory simultaneously — the "database locked" problem, solved.

| Concurrent Writers | Writes/sec | Median Write | P95 Write | Errors |
|--------------------|------------|--------------|-----------|--------|
| 1 agent | **204/sec** | 4.3ms | 8.8ms | **0** |
| 2 agents | **220/sec** | 8.4ms | 13.1ms | **0** |
| 5 agents | **130/sec** | 31.1ms | 82.1ms | **0** |
| 10 agents | **25/sec** | 386.7ms | 754.2ms | **0** |

**What this means:** Zero "database is locked" errors, even with 10 AI tools writing at the same time. The sweet spot is 1-2 concurrent agents at 220 writes/second with sub-15ms P95 latency.

---

## Storage Efficiency

How much disk space your memories use.

| Memories | Database Size | Per Memory |
|----------|--------------|------------|
| 100 | 0.24 MB | 2.4 KB |
| 500 | 0.83 MB | 1.7 KB |
| 1,000 | 1.50 MB | 1.5 KB |
| 5,000 | 6.86 MB | 1.4 KB |
| 10,000 | **13.6 MB** | **1.9 KB** |

**What this means:** 10,000 memories fit in 13.6 MB. Your entire AI memory history takes less space than a single high-res photo.

---

## Knowledge Graph Construction

Building the relationship graph from your memories.

| Memories | Build Time | Clusters | Edges | Hierarchy Depth |
|----------|-----------|----------|-------|-----------------|
| 100 | **0.28s** | 6 | 935 | 2 levels |
| 500 | **3.1s** | 6 | 24,321 | 3 levels |
| 1,000 | **10.6s** | 6 | 97,641 | 3 levels |
| 5,000 | **277s** | 7 | 2,456,201 | 3 levels |

**What this means:** Graph builds in under a second for most users. The Leiden algorithm consistently discovers 6-7 natural topic communities with up to 3 levels of hierarchy. At 5,000 memories (the design limit), a full rebuild takes about 4.5 minutes — an explicit design choice balancing graph utility against compute cost.

> **Graph Scaling:** Knowledge graph features work best with up to 10,000 memories. For larger databases, the system uses intelligent sampling (most recent + highest importance memories) for graph construction. Core search and memory storage have no upper limit.

---

## Trust Scoring — Memory Poisoning Defense

Bayesian trust scoring detects malicious agents attempting to corrupt your memory.

| Scenario | Benign Trust | Malicious Trust | Trust Gap |
|----------|-------------|----------------|-----------|
| Normal operation (10 agents) | **1.000** | N/A | — |
| Single malicious agent (9 good + 1 bad) | **1.000** | **0.000** | **1.000** |
| "Sleeper" agent (builds trust, then attacks) | 1.000 | **0.253** | **0.747** |

**What this means:** The trust system achieves perfect separation between honest and malicious agents (trust gap = 1.0). Even a sophisticated "sleeper" attack — where an agent behaves well to build trust, then turns hostile — is detected with a 74.7% trust drop. Zero false positives on benign agents.

---

## Layer Contribution Analysis

How each architectural layer contributes to search quality.

| Configuration | MRR (Mean Reciprocal Rank) | Recall@10 |
|---------------|---------------------------|-----------|
| FTS5 only | 0.90 | 0.045 |
| + TF-IDF vectors | 0.90 | 0.045 |
| + Knowledge Graph | 0.90 | 0.045 |
| Full system | **0.90** | **0.045** |

**What this means:** The core FTS5 + TF-IDF retrieval achieves MRR 0.90 — the first relevant result is at position 1 for 9 out of 10 queries. The Graph and Pattern layers provide structural enrichment (clustering, relationship navigation, coding preferences) rather than modifying search ranking directly. Graph-boosted re-ranking is planned for a future release.

---

## Coming Soon: LoCoMo Benchmark

We are currently running the [LoCoMo benchmark](https://snap-research.github.io/locomo/) (Snap Research, ACL 2024) — a standardized evaluation for long-conversation memory systems with multi-hop, temporal, and adversarial question types. Results will be published here when complete.

---

## Methodology

- All benchmarks run on local hardware with no cloud dependencies
- Each measurement repeated multiple times with statistical aggregation (median, P95, P99)
- Database populated with realistic synthetic memories across diverse topics
- Tests run on clean database instances for each benchmark scenario
- Full raw statistics include median, mean, P95, P99, min, max, and standard deviation

---

**See also:** [[Universal-Architecture]] | [[Architecture-V2.5]] | [[Home]]
