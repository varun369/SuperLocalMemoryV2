# Progressive Summarization Compression for SuperLocalMemory

## Overview

The compression system implements tier-based progressive summarization to efficiently manage 100+ memories without performance degradation. It uses **extractive summarization** (no external LLM calls) to compress older memories while preserving essential information.

## Architecture

### Compression Tiers

```
┌─────────────────────────────────────────────────────────┐
│ TIER 1: Recent (0-30 days)                             │
│ Storage: Full content + summary                        │
│ Size: ~50KB per memory                                 │
│ Access: Instant, no decompression needed               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ TIER 2: Active (30-90 days)                            │
│ Storage: Summary + key excerpts                        │
│ Size: ~10KB per memory (80% reduction)                 │
│ Access: Fast, show summary with "expand" option        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ TIER 3: Archived (90+ days)                            │
│ Storage: Bullet-point summary only                     │
│ Size: ~2KB per memory (96% reduction)                  │
│ Access: Show bullets, full content in cold storage     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ COLD STORAGE: Very Old (1+ year)                       │
│ Storage: Compressed JSON file (gzip)                   │
│ Size: ~1KB per memory (98% reduction)                  │
│ Access: Manual restore from archive                    │
└─────────────────────────────────────────────────────────┘
```

### Key Features

1. **No External APIs**: All compression is local using extractive summarization
2. **Preserves Important Memories**: High-importance (≥8) memories stay in Tier 1
3. **Access-Based Protection**: Recently accessed memories remain uncompressed
4. **Reversible**: Full content stored in archive table until moved to cold storage
5. **Automatic**: Daily cron job handles all compression tasks
6. **Safe**: Database backup before each compression run

## Implementation

### Core Classes

#### 1. TierClassifier
Classifies memories into tiers based on:
- Age (days since creation)
- Importance score
- Last access time
- Access count

#### 2. Tier2Compressor
Compresses to summary + key excerpts using:
- Sentence scoring (tech terms, position, numbers)
- Code block extraction
- Bullet list extraction
- Important paragraph detection

#### 3. Tier3Compressor
Ultra-compresses to 5 bullet points:
- Converts summary to brief bullets
- Each bullet max 80 characters
- Preserves core information only

#### 4. ColdStorageManager
Archives very old memories:
- Gzipped JSON format
- Monthly archive files
- Restoreable on demand

#### 5. CompressionOrchestrator
Main controller that runs full compression cycle:
1. Classify memories into tiers
2. Compress Tier 2 memories
3. Compress Tier 3 memories
4. Move candidates to cold storage
5. Calculate space savings

## Configuration

Located in `~/.claude-memory/config.json`:

```json
{
  "compression": {
    "enabled": true,
    "tier2_threshold_days": 30,
    "tier3_threshold_days": 90,
    "cold_storage_threshold_days": 365,
    "preserve_high_importance": true,
    "preserve_recently_accessed": true
  }
}
```

### Configuration Options

- `enabled`: Enable/disable compression system
- `tier2_threshold_days`: Days before compressing to Tier 2 (default: 30)
- `tier3_threshold_days`: Days before compressing to Tier 3 (default: 90)
- `cold_storage_threshold_days`: Days before moving to cold storage (default: 365)
- `preserve_high_importance`: Keep importance ≥8 in Tier 1 (default: true)
- `preserve_recently_accessed`: Keep recently accessed in Tier 1 (default: true)

## Usage

### Command Line Interface

```bash
# Initialize compression configuration
~/.claude-memory/memory-compress init-config

# Classify memories into tiers
~/.claude-memory/memory-compress classify

# Run full compression cycle
~/.claude-memory/memory-compress compress

# Show compression statistics
~/.claude-memory/memory-compress stats

# Compress specific memory to Tier 2
~/.claude-memory/memory-compress tier2 <id>

# Compress specific memory to Tier 3
~/.claude-memory/memory-compress tier3 <id>

# Move old memories to cold storage
~/.claude-memory/memory-compress cold-storage

# Restore memory from cold storage
~/.claude-memory/memory-compress restore <id>
```

### Python API

```python
from memory_compression import CompressionOrchestrator

# Run full compression
orchestrator = CompressionOrchestrator()
stats = orchestrator.run_full_compression()

print(f"Compressed {stats['tier2_compressed']} to Tier 2")
print(f"Compressed {stats['tier3_compressed']} to Tier 3")
print(f"Space savings: {stats['space_savings']['savings_percent']}%")
```

## Automated Compression

### Daily Cron Job

The system includes a daily cron job script at:
```
~/.claude-memory/jobs/compress-memories.sh
```

#### Setup Cron Job

1. Open crontab editor:
```bash
crontab -e
```

2. Add this line (runs daily at 3 AM):
```
0 3 * * * ~/.claude-memory/jobs/compress-memories.sh >> ~/.claude-memory/logs/compression.log 2>&1
```

3. Save and exit

#### What the Daily Job Does

1. Creates database backup
2. Classifies memories into tiers
3. Compresses Tier 2 memories
4. Compresses Tier 3 memories
5. Moves old memories to cold storage
6. Logs results to `~/.claude-memory/logs/compression.log`
7. Cleans up backups older than 7 days

## Database Schema

### New Columns in `memories` Table

```sql
tier INTEGER DEFAULT 1              -- Compression tier (1, 2, or 3)
last_accessed TIMESTAMP            -- Last access time
access_count INTEGER DEFAULT 0     -- Number of accesses
```

### New `memory_archive` Table

```sql
CREATE TABLE memory_archive (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER UNIQUE NOT NULL,
    full_content TEXT NOT NULL,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);
```

## Extractive Summarization Algorithm

### Sentence Scoring Heuristics

Each sentence is scored based on:

1. **Tech Terms** (+1 per term): api, database, auth, component, function, class, method, variable, error, bug, fix, implement, refactor, test, deploy

2. **Position Boost** (+2): First or last sentence (thesis/conclusion)

3. **Numbers/Specifics** (+1): Contains digits (measurements, versions, dates)

4. **Important Keywords** (+2 per keyword): important, critical, note, remember, key, main, primary, must, should

Top-scored sentences are selected until max_length is reached.

### Excerpt Extraction

Priority order:
1. Code blocks (markdown or indented) - max 2
2. Bullet lists - max 1
3. Paragraphs with important keywords - remaining slots

## Performance Impact

### Before Compression (100 memories @ 50KB each)
- Database size: 5MB
- Search time: 150ms (scan all content)
- Memory load: 5MB into RAM

### After Compression (100 memories, tiered)
- Tier 1 (30 memories @ 50KB): 1.5MB
- Tier 2 (40 memories @ 10KB): 400KB
- Tier 3 (30 memories @ 2KB): 60KB
- **Total: 1.96MB (61% reduction)**
- **Search time: Sub-11ms median for typical databases** (only scan Tier 1+2, see wiki Performance Benchmarks)
- **Memory load: 1.9MB** (Tier 3 loaded on-demand)

### Space Savings Scale
- 500 memories: ~10MB → ~4MB (60% reduction)
- 1000 memories: ~50MB → ~15MB (70% reduction)

## Safety & Rollback

### Data Preservation

1. **Archive Table**: Full content preserved until moved to cold storage
2. **Cold Storage**: Gzipped JSON archives (restorable)
3. **Daily Backups**: Database backup before each compression run
4. **7-Day Retention**: Last 7 backups kept automatically

### Restore Operations

#### Restore from Archive (Tier 2/3 → Tier 1)
```python
from memory_compression import ColdStorageManager

cold_storage = ColdStorageManager()
content = cold_storage.restore_from_cold_storage(memory_id)
```

#### Manual Restore from Backup
```bash
# List backups
ls ~/.claude-memory/backups/

# Restore from backup
cp ~/.claude-memory/backups/memory-20260205.db ~/.claude-memory/memory.db
```

## Monitoring

### Check Compression Stats
```bash
~/.claude-memory/memory-compress stats
```

### View Compression Logs
```bash
tail -f ~/.claude-memory/logs/compression.log
```

### Check Cron Job Status
```bash
# View cron jobs
crontab -l

# Check last run
ls -lt ~/.claude-memory/logs/compression.log
```

## Troubleshooting

### Compression Not Running

1. Check if enabled in config:
```bash
cat ~/.claude-memory/config.json | grep -A 6 compression
```

2. Check cron job is set:
```bash
crontab -l | grep compress
```

3. Check logs for errors:
```bash
tail -50 ~/.claude-memory/logs/compression.log
```

### Memory Not Being Compressed

Check tier classification:
```bash
sqlite3 ~/.claude-memory/memory.db "SELECT id, tier, importance, created_at FROM memories WHERE id = <id>;"
```

Possible reasons:
- Memory is too recent (< 30 days)
- High importance (≥8) - stays in Tier 1
- Recently accessed (< 7 days) - stays in Tier 1

### Restore Failed

1. Check if in archive table:
```bash
sqlite3 ~/.claude-memory/memory.db "SELECT memory_id FROM memory_archive WHERE memory_id = <id>;"
```

2. Check cold storage:
```bash
ls ~/.claude-memory/cold-storage/
zgrep '"id": <id>' ~/.claude-memory/cold-storage/archive-*.json.gz
```

## Files

### Main Files
- `memory_compression.py` - Main compression implementation
- `memory-compress` - CLI wrapper script
- `jobs/compress-memories.sh` - Daily cron job script
- `COMPRESSION-README.md` - This file

### Generated Files
- `cold-storage/archive-YYYY-MM.json.gz` - Monthly archive files
- `logs/compression.log` - Compression job logs
- `backups/memory-YYYYMMDD.db` - Daily database backups

## Integration with memory_store.py

The compression system works alongside the existing memory system:

1. **Add Memory**: New memories created with `tier=1` by default
2. **Search**: Searches work across all tiers (compressed content is JSON)
3. **Access Tracking**: Can update `last_accessed` when retrieving memories
4. **Display**: UI can check tier and format display accordingly:
   - Tier 1: Show full content
   - Tier 2: Show summary + excerpts with "expand" button
   - Tier 3: Show bullets with "restore" button

## Future Enhancements

1. **Access Tracking Integration**: Update `last_accessed` in memory_store.py
2. **UI Indicators**: Show compression tier in memory list
3. **Manual Override**: CLI command to change tier manually
4. **Compression Preview**: Show what will be compressed before running
5. **Selective Compression**: Compress by project or tag
6. **Adaptive Thresholds**: Adjust thresholds based on storage constraints

## References

- [Progressive Summarization](https://fortelabs.co/blog/progressive-summarization-a-practical-technique-for-designing-discoverable-notes/) by Tiago Forte
- [PageIndex](https://pageindex.ai/) - Vectorless hierarchical RAG
- [GraphRAG](https://microsoft.github.io/graphrag/) - Knowledge graph clustering

---

**Compression system ready. Run daily job to maintain optimal memory performance.**
