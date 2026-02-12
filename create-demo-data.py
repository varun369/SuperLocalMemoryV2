#!/usr/bin/env python3
"""
SuperLocalMemory V2 - Demo Data Generator
Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License

Creates synthetic demo data for dashboard screenshots.
"""

import subprocess
import sys
import time
from pathlib import Path

# Synthetic demo memories with realistic software development content
DEMO_MEMORIES = [
    {
        "content": "Use FastAPI for REST APIs - better performance than Flask, built-in async support",
        "tags": ["api", "architecture", "python"],
        "project": "api-service",
        "importance": 8
    },
    {
        "content": "JWT tokens expire after 24 hours - implement refresh token mechanism before expiry",
        "tags": ["security", "auth", "api"],
        "project": "api-service",
        "importance": 9
    },
    {
        "content": "PostgreSQL 15 with UUID primary keys for distributed scalability and no collisions",
        "tags": ["database", "architecture", "postgresql"],
        "project": "demo-app",
        "importance": 8
    },
    {
        "content": "Authentication flow: Login → JWT generation → Refresh token → Secure logout with token invalidation",
        "tags": ["auth", "security", "architecture"],
        "project": "api-service",
        "importance": 9
    },
    {
        "content": "React components should be functional with hooks, not class-based - better performance and cleaner code",
        "tags": ["react", "frontend", "best-practices"],
        "project": "frontend",
        "importance": 7
    },
    {
        "content": "API rate limiting: 100 requests per minute per user, 1000 per minute per IP block",
        "tags": ["api", "security", "performance"],
        "project": "api-service",
        "importance": 8
    },
    {
        "content": "Database migrations with Alembic - never manual SQL in production, always version controlled",
        "tags": ["database", "devops", "best-practices"],
        "project": "demo-app",
        "importance": 9
    },
    {
        "content": "CORS enabled for localhost:3000 (dev), demo.example.com (staging), and app.example.com (prod)",
        "tags": ["api", "security", "deployment"],
        "project": "api-service",
        "importance": 7
    },
    {
        "content": "Error handling: try/except with structured logging using Python logging module, JSON format for cloud",
        "tags": ["best-practices", "logging", "python"],
        "project": "demo-app",
        "importance": 7
    },
    {
        "content": "Docker compose for local development environment - PostgreSQL, Redis, API, Frontend all in sync",
        "tags": ["devops", "docker", "development"],
        "project": "demo-app",
        "importance": 8
    },
    {
        "content": "Git workflow: feature branch → PR with tests → code review → CI passes → merge to main",
        "tags": ["git", "devops", "best-practices"],
        "project": "demo-app",
        "importance": 8
    },
    {
        "content": "Testing: pytest for backend with 80% coverage minimum, Jest + React Testing Library for frontend",
        "tags": ["testing", "quality", "best-practices"],
        "project": "demo-app",
        "importance": 9
    },
    {
        "content": "Code review checklist: tests passing, documentation updated, security review, performance benchmarks",
        "tags": ["best-practices", "quality", "devops"],
        "project": "demo-app",
        "importance": 7
    },
    {
        "content": "Deployment pipeline: GitHub Actions → Docker build → Push to ECR → Deploy to AWS ECS with blue-green",
        "tags": ["deployment", "devops", "aws", "ci-cd"],
        "project": "demo-app",
        "importance": 9
    },
    {
        "content": "Monitoring: CloudWatch for application logs, Datadog for metrics and APM, PagerDuty for alerts",
        "tags": ["monitoring", "devops", "observability"],
        "project": "demo-app",
        "importance": 8
    },
    {
        "content": "Redis for session management - 30 minute TTL for active sessions, automatic cleanup",
        "tags": ["redis", "architecture", "caching"],
        "project": "api-service",
        "importance": 7
    },
    {
        "content": "Environment variables managed with AWS Secrets Manager - never commit secrets to git",
        "tags": ["security", "devops", "aws"],
        "project": "demo-app",
        "importance": 10
    },
    {
        "content": "API versioning: /api/v1/ prefix for all endpoints, maintain backward compatibility for 6 months",
        "tags": ["api", "architecture", "best-practices"],
        "project": "api-service",
        "importance": 8
    },
    {
        "content": "Frontend state management with Zustand - lighter than Redux, better TypeScript support",
        "tags": ["react", "frontend", "architecture"],
        "project": "frontend",
        "importance": 6
    },
    {
        "content": "Database connection pooling: min 5, max 20 connections per instance to avoid overwhelming PostgreSQL",
        "tags": ["database", "performance", "postgresql"],
        "project": "api-service",
        "importance": 8
    },
    {
        "content": "WebSocket connections for real-time updates - use Socket.io with Redis adapter for multi-instance support",
        "tags": ["api", "realtime", "architecture"],
        "project": "api-service",
        "importance": 7
    },
    {
        "content": "Input validation with Pydantic models - automatic schema validation and OpenAPI docs generation",
        "tags": ["api", "security", "validation"],
        "project": "api-service",
        "importance": 9
    },
    {
        "content": "Celery for background tasks - Redis as broker, PostgreSQL as result backend, 3 worker processes",
        "tags": ["architecture", "async", "python"],
        "project": "api-service",
        "importance": 7
    },
    {
        "content": "Frontend bundling with Vite - faster than Webpack, HMR in milliseconds, tree-shaking by default",
        "tags": ["frontend", "performance", "build"],
        "project": "frontend",
        "importance": 6
    },
    {
        "content": "SQL query optimization: add indexes on foreign keys, use EXPLAIN ANALYZE for slow queries over 100ms",
        "tags": ["database", "performance", "postgresql"],
        "project": "demo-app",
        "importance": 8
    },
    {
        "content": "Security headers: Content-Security-Policy, X-Frame-Options, HSTS - all enforced in production",
        "tags": ["security", "api", "best-practices"],
        "project": "api-service",
        "importance": 9
    },
    {
        "content": "Automated dependency updates with Dependabot - weekly PRs for security patches, monthly for features",
        "tags": ["devops", "security", "automation"],
        "project": "demo-app",
        "importance": 7
    },
    {
        "content": "API documentation auto-generated with FastAPI's built-in OpenAPI - available at /docs endpoint",
        "tags": ["api", "documentation", "best-practices"],
        "project": "api-service",
        "importance": 6
    },
    {
        "content": "Load testing with Locust before major releases - target 1000 concurrent users, 95th percentile under 500ms",
        "tags": ["testing", "performance", "quality"],
        "project": "demo-app",
        "importance": 8
    },
    {
        "content": "Backup strategy: PostgreSQL daily backups to S3, 30 day retention, monthly snapshots kept for 1 year",
        "tags": ["database", "devops", "disaster-recovery"],
        "project": "demo-app",
        "importance": 10
    }
]

def run_command(cmd):
    """Execute shell command and return success status."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out: {cmd}")
        return False
    except Exception as e:
        print(f"❌ Error executing command: {e}")
        return False

def main():
    print("=" * 60)
    print("SuperLocalMemory V2 - Demo Data Generator")
    print("=" * 60)
    print()

    # Find slm binary
    slm_path = Path.home() / ".claude-memory" / "bin" / "slm"
    if not slm_path.exists():
        print(f"❌ SLM binary not found at {slm_path}")
        sys.exit(1)

    # Create demo profile
    print("Step 1: Creating demo-visual profile...")
    profiles_script = Path.home() / ".claude-memory" / "src" / "memory-profiles.py"
    if not profiles_script.exists():
        # Try repo location
        profiles_script = Path("/Users/v.pratap.bhardwaj/Documents/AGENTIC_Official/SuperLocalMemoryV2-repo/src/memory-profiles.py")

    if run_command(f'python3 "{profiles_script}" create demo-visual --description "Synthetic demo data for dashboard screenshots"'):
        print("✅ Profile created")
    else:
        print("ℹ️  Profile might already exist, continuing...")

    # Switch to demo profile
    print("\nStep 2: Switching to demo-visual profile...")
    if run_command(f'python3 "{profiles_script}" switch demo-visual'):
        print("✅ Switched to demo-visual profile")
    else:
        print("❌ Failed to switch profile")
        sys.exit(1)

    # Clear any existing data in demo profile
    print("\nStep 3: Clearing existing demo data (if any)...")
    time.sleep(1)  # Give profile switch time to complete

    # Add synthetic memories
    print("\nStep 4: Adding synthetic memories...")
    success_count = 0
    fail_count = 0

    for i, memory in enumerate(DEMO_MEMORIES, 1):
        tags_str = ",".join(memory["tags"])
        cmd = f'"{slm_path}" remember "{memory["content"]}" --tags {tags_str} --project {memory["project"]} --importance {memory["importance"]}'

        print(f"  [{i}/{len(DEMO_MEMORIES)}] Adding: {memory['content'][:60]}...")

        if run_command(cmd):
            success_count += 1
            time.sleep(0.1)  # Small delay to avoid overwhelming the system
        else:
            fail_count += 1

    print(f"\n✅ Added {success_count} memories successfully")
    if fail_count > 0:
        print(f"❌ Failed to add {fail_count} memories")

    # Build knowledge graph
    print("\nStep 5: Building knowledge graph...")
    if run_command(f'"{slm_path}" build-graph'):
        print("✅ Knowledge graph built")
    else:
        print("⚠️  Knowledge graph build had issues, but continuing...")

    # Show status
    print("\nStep 6: Verifying demo data...")
    run_command(f'"{slm_path}" status')

    print("\n" + "=" * 60)
    print("✅ Demo data generation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart ui_server.py if it's running")
    print("2. Navigate to http://localhost:8765")
    print("3. Run the screenshot capture script")
    print("\nTo switch back to your main profile:")
    print(f'  python3 "{profiles_script}" switch default')
    print()

if __name__ == "__main__":
    main()
