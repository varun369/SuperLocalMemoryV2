#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Intelligent Local Memory System
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Repository: https://github.com/varun369/SuperLocalMemoryV2
Author: Varun Pratap Bhardwaj (Solution Architect)

NOTICE: This software is protected by MIT License.
Attribution must be preserved in all copies or derivatives.
"""

"""
Create demo database with safe, generic content for GitHub distribution.
No personal, client, or proprietary information included.
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from memory_store_v2 import MemoryStoreV2
from graph_engine import GraphEngine
from pattern_learner import PatternLearner

# Define output path
DEMO_DB_PATH = Path(__file__).parent / "demo-memory.db"


def create_demo_database():
    """Create demo database with 20 safe, generic memories."""

    # Remove existing demo database if present
    if DEMO_DB_PATH.exists():
        DEMO_DB_PATH.unlink()
        print(f"Removed existing demo database: {DEMO_DB_PATH}")

    # Initialize memory store with custom path
    store = MemoryStoreV2(db_path=DEMO_DB_PATH)
    print(f"Created new demo database: {DEMO_DB_PATH}")

    # Generic memories - organized by category
    memories = [
        # Frontend Development
        {
            "content": "Prefer React with TypeScript for frontend projects. Use functional components and hooks over class components.",
            "summary": "React + TypeScript preference",
            "category": "frontend",
            "tags": ["react", "typescript", "frontend"],
            "importance": 8
        },
        {
            "content": "For state management in React apps, use Redux Toolkit for complex state or React Context for simpler cases.",
            "summary": "State management strategy",
            "category": "frontend",
            "tags": ["react", "redux", "state-management"],
            "importance": 7
        },
        {
            "content": "CSS-in-JS with Styled Components or Emotion for component styling. Tailwind CSS for utility-first approach.",
            "summary": "CSS styling preferences",
            "category": "frontend",
            "tags": ["css", "styled-components", "tailwind"],
            "importance": 6
        },

        # Backend Development
        {
            "content": "Python FastAPI for REST APIs. Includes automatic OpenAPI docs, type validation with Pydantic, and async support.",
            "summary": "FastAPI for backend services",
            "category": "backend",
            "tags": ["python", "fastapi", "api"],
            "importance": 8
        },
        {
            "content": "Use PostgreSQL for relational data requiring ACID guarantees. Redis for caching and session storage.",
            "summary": "Database selection criteria",
            "category": "backend",
            "tags": ["postgresql", "redis", "database"],
            "importance": 9
        },
        {
            "content": "Implement JWT-based authentication for stateless API authentication. Store refresh tokens in HttpOnly cookies.",
            "summary": "Authentication pattern",
            "category": "backend",
            "tags": ["security", "jwt", "authentication"],
            "importance": 8
        },

        # Code Quality
        {
            "content": "Optimize for code readability first, performance second. Premature optimization is the root of all evil.",
            "summary": "Readability over premature optimization",
            "category": "best-practices",
            "tags": ["code-quality", "optimization"],
            "importance": 7
        },
        {
            "content": "Use meaningful variable names that describe intent. Avoid abbreviations unless universally understood.",
            "summary": "Naming conventions",
            "category": "best-practices",
            "tags": ["code-quality", "naming"],
            "importance": 6
        },
        {
            "content": "Keep functions small and focused. Single Responsibility Principle: each function should do one thing well.",
            "summary": "Function design principle",
            "category": "best-practices",
            "tags": ["clean-code", "solid"],
            "importance": 7
        },

        # Testing
        {
            "content": "Test-driven development with Jest for JavaScript/TypeScript and Pytest for Python. Write tests before implementation.",
            "summary": "TDD approach",
            "category": "testing",
            "tags": ["tdd", "jest", "pytest"],
            "importance": 8
        },
        {
            "content": "Aim for 80%+ code coverage but focus on testing critical paths and edge cases rather than chasing 100%.",
            "summary": "Test coverage strategy",
            "category": "testing",
            "tags": ["testing", "coverage"],
            "importance": 7
        },
        {
            "content": "Use integration tests for API endpoints. Mock external dependencies to ensure consistent test results.",
            "summary": "Integration testing pattern",
            "category": "testing",
            "tags": ["testing", "integration", "mocking"],
            "importance": 7
        },

        # DevOps & Infrastructure
        {
            "content": "Docker for containerization. Use multi-stage builds to minimize image size and improve security.",
            "summary": "Docker containerization",
            "category": "devops",
            "tags": ["docker", "containers"],
            "importance": 8
        },
        {
            "content": "CI/CD with GitHub Actions. Automated testing, linting, and deployment on every commit to main branch.",
            "summary": "CI/CD automation",
            "category": "devops",
            "tags": ["ci-cd", "github-actions"],
            "importance": 8
        },
        {
            "content": "Use environment variables for configuration. Never commit secrets to version control.",
            "summary": "Configuration management",
            "category": "devops",
            "tags": ["security", "configuration"],
            "importance": 9
        },

        # Architecture
        {
            "content": "Microservices for large-scale applications. Monolith first for MVPs and early-stage products.",
            "summary": "Architecture selection",
            "category": "architecture",
            "tags": ["microservices", "architecture"],
            "importance": 8
        },
        {
            "content": "API-first design: define OpenAPI spec before implementation. Ensures frontend/backend teams can work in parallel.",
            "summary": "API-first development",
            "category": "architecture",
            "tags": ["api", "design"],
            "importance": 7
        },
        {
            "content": "Event-driven architecture for asynchronous workflows. Use message queues like RabbitMQ or Kafka for reliability.",
            "summary": "Event-driven patterns",
            "category": "architecture",
            "tags": ["event-driven", "messaging"],
            "importance": 7
        },

        # Performance
        {
            "content": "Database query optimization: add indexes for frequently queried columns. Use EXPLAIN ANALYZE to identify bottlenecks.",
            "summary": "Database optimization",
            "category": "performance",
            "tags": ["database", "optimization"],
            "importance": 8
        },
        {
            "content": "Implement caching at multiple layers: browser cache, CDN, application cache, database query cache.",
            "summary": "Multi-layer caching strategy",
            "category": "performance",
            "tags": ["caching", "performance"],
            "importance": 8
        },
    ]

    print(f"\nAdding {len(memories)} generic memories...")

    for i, mem in enumerate(memories, 1):
        memory_id = store.add_memory(
            content=mem["content"],
            summary=mem.get("summary"),
            category=mem.get("category"),
            tags=mem.get("tags"),
            importance=mem.get("importance", 5),
            memory_type="long-term"
        )
        print(f"  [{i}/20] Added memory {memory_id}: {mem['summary']}")

    # Build graph relationships
    print("\nBuilding graph relationships...")
    graph = GraphEngine(db_path=DEMO_DB_PATH)
    graph.build_graph()
    print("  Graph constructed with entity relationships")

    # Learn patterns
    print("\nLearning patterns from demo data...")
    learner = PatternLearner(db_path=DEMO_DB_PATH)
    patterns = learner.get_patterns(min_confidence=0.5)
    print(f"  Discovered {len(patterns)} patterns")

    # Display statistics
    print("\n" + "="*60)
    print("DEMO DATABASE SUMMARY")
    print("="*60)

    stats = store.get_stats()
    print(f"\nTotal Memories: {stats['total_memories']}")
    print(f"Total Clusters: {stats['total_clusters']}")
    print(f"Max Tree Depth: {stats['max_tree_depth']}")

    print("\nMemories by Category:")
    for category, count in stats['by_category'].items():
        print(f"  {category}: {count}")

    # Check database size
    db_size_kb = DEMO_DB_PATH.stat().st_size / 1024
    print(f"\nDatabase Size: {db_size_kb:.1f} KB")

    if db_size_kb > 100:
        print("  ⚠ Warning: Database larger than 100KB. Consider reducing content.")
    else:
        print("  ✓ Database size appropriate for distribution")

    print(f"\n✓ Demo database created successfully: {DEMO_DB_PATH}")
    print("\nThis database contains ONLY generic, safe content:")
    print("  - No client names or company information")
    print("  - No personal data or proprietary details")
    print("  - No revenue numbers or business metrics")
    print("  - Generic tech stack and best practices only")
    print("\nSafe for public GitHub distribution.")


if __name__ == "__main__":
    create_demo_database()
