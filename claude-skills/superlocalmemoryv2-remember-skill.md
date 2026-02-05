---
name: superlocalmemoryv2:remember
description: Save a memory to SuperLocalMemory V2 with intelligent indexing
arguments: content (required), --tags (optional), --project (optional)
---

# SuperLocalMemory V2: Remember

Saves content to SuperLocalMemory V2's intelligent memory system with:
- Semantic search indexing using TF-IDF vectorization
- Knowledge graph integration for concept relationships
- Pattern learning engine for implicit knowledge extraction
- Hierarchical organization by project and tags

## Usage

```bash
/superlocalmemoryv2:remember "Your memory content here"
/superlocalmemoryv2:remember "React hooks pattern" --tags react,frontend
/superlocalmemoryv2:remember "API design" --project myapp --tags backend,api
```

## Features

**Semantic Indexing**: Automatically creates TF-IDF vectors for semantic similarity search
**Knowledge Graph**: Extracts entities and relationships, integrates into graph database
**Pattern Learning**: Identifies recurring patterns and implicit knowledge
**Metadata**: Supports tags, projects, importance scores, and custom metadata

## Implementation

This skill executes: `~/.claude-memory/bin/superlocalmemoryv2:remember`

The command:
1. Parses content and metadata
2. Generates semantic embeddings
3. Extracts knowledge graph entities
4. Updates pattern learning models
5. Stores in SQLite with full-text search index

## Examples

**Basic memory:**
```bash
/superlocalmemoryv2:remember "Always validate user input before database queries"
```

**Tagged memory:**
```bash
/superlocalmemoryv2:remember "Use React.memo for expensive component re-renders" --tags react,performance,optimization
```

**Project-scoped memory:**
```bash
/superlocalmemoryv2:remember "API rate limit: 100 req/min per user" --project ecommerce --tags api,limits
```

## Notes

- Content is required; tags and project are optional
- Multiple tags separated by commas (no spaces)
- Automatic deduplication based on semantic similarity
- Creates backup before modifications
