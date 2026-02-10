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
Pattern Learner - Identity Profile Extraction (Layer 4)

Learns user preferences, coding style, and terminology patterns from memories.
Uses local TF-IDF, frequency analysis, and heuristics - NO EXTERNAL APIs.

Based on architecture: docs/architecture/05-pattern-learner.md
"""

import sqlite3
import json
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Counter as CounterType
from collections import Counter

logger = logging.getLogger(__name__)

# Local NLP tools (no external APIs)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

MEMORY_DIR = Path.home() / ".claude-memory"
DB_PATH = MEMORY_DIR / "memory.db"


class FrequencyAnalyzer:
    """Analyzes technology and tool preferences via frequency counting."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

        # Predefined technology categories
        self.tech_categories = {
            'frontend_framework': ['react', 'nextjs', 'next.js', 'vue', 'angular', 'svelte', 'solid'],
            'backend_framework': ['express', 'fastapi', 'django', 'flask', 'nestjs', 'spring', 'rails'],
            'database': ['postgres', 'postgresql', 'mysql', 'mongodb', 'redis', 'dynamodb', 'sqlite'],
            'state_management': ['redux', 'context', 'zustand', 'mobx', 'recoil', 'jotai'],
            'styling': ['tailwind', 'css modules', 'styled-components', 'emotion', 'sass', 'less'],
            'language': ['python', 'javascript', 'typescript', 'go', 'rust', 'java', 'c++'],
            'deployment': ['docker', 'kubernetes', 'vercel', 'netlify', 'aws', 'gcp', 'azure'],
            'testing': ['jest', 'pytest', 'vitest', 'mocha', 'cypress', 'playwright'],
        }

    def analyze_preferences(self, memory_ids: List[int]) -> Dict[str, Dict[str, Any]]:
        """Analyze technology preferences across memories."""
        patterns = {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for category, keywords in self.tech_categories.items():
            keyword_counts = Counter()
            evidence_memories = {}  # {keyword: [memory_ids]}

            for memory_id in memory_ids:
                cursor.execute('SELECT content FROM memories WHERE id = ?', (memory_id,))
                row = cursor.fetchone()

                if not row:
                    continue

                content = row[0].lower()

                for keyword in keywords:
                    # Count occurrences with word boundaries
                    pattern = r'\b' + re.escape(keyword.replace('.', r'\.')) + r'\b'
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    count = len(matches)

                    if count > 0:
                        keyword_counts[keyword] += count

                        if keyword not in evidence_memories:
                            evidence_memories[keyword] = []
                        evidence_memories[keyword].append(memory_id)

            # Determine preference (most mentioned)
            if keyword_counts:
                top_keyword = keyword_counts.most_common(1)[0][0]
                total_mentions = sum(keyword_counts.values())
                top_count = keyword_counts[top_keyword]

                # Calculate confidence (% of mentions)
                confidence = top_count / total_mentions if total_mentions > 0 else 0

                # Only create pattern if confidence > 0.6 and at least 3 mentions
                if confidence > 0.6 and top_count >= 3:
                    value = self._format_preference(top_keyword, keyword_counts)
                    evidence_list = list(set(evidence_memories.get(top_keyword, [])))

                    patterns[category] = {
                        'pattern_type': 'preference',
                        'key': category,
                        'value': value,
                        'confidence': round(confidence, 2),
                        'evidence_count': len(evidence_list),
                        'memory_ids': evidence_list,
                        'category': self._categorize_pattern(category)
                    }

        conn.close()
        return patterns

    def _format_preference(self, top_keyword: str, all_counts: Counter) -> str:
        """Format preference value (e.g., 'Next.js over React')."""
        # Normalize keyword for display
        display_map = {
            'nextjs': 'Next.js',
            'next.js': 'Next.js',
            'postgres': 'PostgreSQL',
            'postgresql': 'PostgreSQL',
            'fastapi': 'FastAPI',
            'nestjs': 'NestJS',
            'mongodb': 'MongoDB',
            'redis': 'Redis',
            'dynamodb': 'DynamoDB',
            'tailwind': 'Tailwind CSS',
        }

        top_display = display_map.get(top_keyword.lower(), top_keyword.title())

        if len(all_counts) > 1:
            second = all_counts.most_common(2)[1]
            second_keyword = second[0]
            second_display = display_map.get(second_keyword.lower(), second_keyword.title())

            # Only show comparison if second choice has significant mentions
            if second[1] / all_counts[top_keyword] > 0.3:
                return f"{top_display} over {second_display}"

        return top_display

    def _categorize_pattern(self, tech_category: str) -> str:
        """Map tech category to high-level category."""
        category_map = {
            'frontend_framework': 'frontend',
            'state_management': 'frontend',
            'styling': 'frontend',
            'backend_framework': 'backend',
            'database': 'backend',
            'language': 'general',
            'deployment': 'devops',
            'testing': 'general',
        }
        return category_map.get(tech_category, 'general')


class ContextAnalyzer:
    """Analyzes coding style patterns from context."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

        # Style pattern detection rules
        self.style_indicators = {
            'optimization_priority': {
                'performance': ['optimize', 'faster', 'performance', 'speed', 'latency', 'efficient', 'cache'],
                'readability': ['readable', 'clean', 'maintainable', 'clear', 'simple', 'understandable']
            },
            'error_handling': {
                'explicit': ['error boundary', 'explicit', 'throw', 'handle error', 'try catch', 'error handling'],
                'permissive': ['ignore', 'suppress', 'skip error', 'optional']
            },
            'testing_approach': {
                'comprehensive': ['test coverage', 'unit test', 'integration test', 'e2e test', 'test suite'],
                'minimal': ['manual test', 'skip test', 'no tests']
            },
            'code_organization': {
                'modular': ['separate', 'module', 'component', 'split', 'refactor', 'extract'],
                'monolithic': ['single file', 'one place', 'combined']
            }
        }

    def analyze_style(self, memory_ids: List[int]) -> Dict[str, Dict[str, Any]]:
        """Detect stylistic patterns from context."""
        patterns = {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for pattern_key, indicators in self.style_indicators.items():
            indicator_counts = Counter()
            evidence_memories = {}  # {style_type: [memory_ids]}

            for memory_id in memory_ids:
                cursor.execute('SELECT content FROM memories WHERE id = ?', (memory_id,))
                row = cursor.fetchone()

                if not row:
                    continue

                content = row[0].lower()

                for style_type, keywords in indicators.items():
                    for keyword in keywords:
                        if keyword in content:
                            indicator_counts[style_type] += 1

                            if style_type not in evidence_memories:
                                evidence_memories[style_type] = []
                            evidence_memories[style_type].append(memory_id)

            # Determine dominant style
            if indicator_counts:
                top_style = indicator_counts.most_common(1)[0][0]
                total = sum(indicator_counts.values())
                top_count = indicator_counts[top_style]
                confidence = top_count / total if total > 0 else 0

                # Only create pattern if confidence > 0.65 and at least 3 mentions
                if confidence > 0.65 and top_count >= 3:
                    value = self._format_style_value(pattern_key, top_style, indicator_counts)
                    evidence_list = list(set(evidence_memories.get(top_style, [])))

                    patterns[pattern_key] = {
                        'pattern_type': 'style',
                        'key': pattern_key,
                        'value': value,
                        'confidence': round(confidence, 2),
                        'evidence_count': len(evidence_list),
                        'memory_ids': evidence_list,
                        'category': 'general'
                    }

        conn.close()
        return patterns

    def _format_style_value(self, pattern_key: str, top_style: str, all_counts: Counter) -> str:
        """Format style value as comparison or preference."""
        style_formats = {
            'optimization_priority': {
                'performance': 'Performance over readability',
                'readability': 'Readability over performance'
            },
            'error_handling': {
                'explicit': 'Explicit error boundaries',
                'permissive': 'Permissive error handling'
            },
            'testing_approach': {
                'comprehensive': 'Comprehensive testing',
                'minimal': 'Minimal testing'
            },
            'code_organization': {
                'modular': 'Modular organization',
                'monolithic': 'Monolithic organization'
            }
        }

        if pattern_key in style_formats and top_style in style_formats[pattern_key]:
            return style_formats[pattern_key][top_style]

        return top_style.replace('_', ' ').title()


class TerminologyLearner:
    """Learns user-specific definitions of common terms."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

        # Common ambiguous terms to learn
        self.ambiguous_terms = [
            'optimize', 'refactor', 'clean', 'simple',
            'mvp', 'prototype', 'scale', 'production-ready',
            'fix', 'improve', 'update', 'enhance'
        ]

    def learn_terminology(self, memory_ids: List[int]) -> Dict[str, Dict[str, Any]]:
        """Learn user-specific term definitions."""
        patterns = {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for term in self.ambiguous_terms:
            contexts = []

            # Find all contexts where term appears
            for memory_id in memory_ids:
                cursor.execute('SELECT content FROM memories WHERE id = ?', (memory_id,))
                row = cursor.fetchone()

                if not row:
                    continue

                content = row[0]

                # Find term in content (case-insensitive)
                pattern = r'\b' + re.escape(term) + r'\b'
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    term_idx = match.start()

                    # Extract 100-char window around term
                    start = max(0, term_idx - 100)
                    end = min(len(content), term_idx + len(term) + 100)
                    context_window = content[start:end]

                    contexts.append({
                        'memory_id': memory_id,
                        'context': context_window
                    })

            # Analyze contexts to extract meaning (need at least 3 examples)
            if len(contexts) >= 3:
                definition = self._extract_definition(term, contexts)

                if definition:
                    evidence_list = list(set([ctx['memory_id'] for ctx in contexts]))

                    # Confidence increases with more examples, capped at 0.95
                    confidence = min(0.95, 0.6 + (len(contexts) * 0.05))

                    patterns[term] = {
                        'pattern_type': 'terminology',
                        'key': term,
                        'value': definition,
                        'confidence': round(confidence, 2),
                        'evidence_count': len(evidence_list),
                        'memory_ids': evidence_list,
                        'category': 'general'
                    }

        conn.close()
        return patterns

    def _extract_definition(self, term: str, contexts: List[Dict]) -> Optional[str]:
        """Extract definition from contexts using pattern matching."""
        # Collect words near the term across all contexts
        nearby_words = []

        for ctx in contexts:
            words = re.findall(r'\b\w+\b', ctx['context'].lower())
            nearby_words.extend(words)

        # Count word frequencies
        word_counts = Counter(nearby_words)

        # Remove the term itself and common stopwords
        stopwords = {'the', 'a', 'an', 'is', 'to', 'for', 'of', 'in', 'on', 'at',
                     'and', 'or', 'but', 'with', 'from', 'by', 'this', 'that'}
        word_counts = Counter({w: c for w, c in word_counts.items()
                              if w not in stopwords and w != term.lower()})

        # Get top co-occurring words
        top_words = [w for w, _ in word_counts.most_common(8)]

        # Apply heuristic rules based on term and context
        if term == 'optimize':
            if any(w in top_words for w in ['performance', 'speed', 'faster', 'latency']):
                return "Performance optimization (speed/latency)"
            elif any(w in top_words for w in ['code', 'clean', 'refactor']):
                return "Code quality optimization"

        elif term == 'refactor':
            if any(w in top_words for w in ['architecture', 'structure', 'design']):
                return "Architecture change, not just renaming"
            elif any(w in top_words for w in ['clean', 'organize', 'simplify']):
                return "Code organization improvement"

        elif term == 'mvp':
            if any(w in top_words for w in ['core', 'basic', 'essential', 'minimal']):
                return "Core features only, no polish"

        elif term == 'production-ready':
            if any(w in top_words for w in ['test', 'error', 'monitoring', 'deploy']):
                return "Fully tested and monitored for deployment"

        # Generic definition if specific pattern not matched
        if len(top_words) >= 3:
            return f"Commonly used with: {', '.join(top_words[:3])}"

        return None


class ConfidenceScorer:
    """Calculates and tracks pattern confidence scores."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def calculate_confidence(
        self,
        pattern_type: str,
        key: str,
        value: str,
        evidence_memory_ids: List[int],
        total_memories: int
    ) -> float:
        """
        Calculate confidence using Beta-Binomial Bayesian posterior.

        Based on MACLA (arXiv:2512.18950, Forouzandeh et al., Dec 2025):
          posterior_mean = (alpha + evidence) / (alpha + beta + evidence + competition)

        Adaptation: MACLA's Beta-Binomial uses pairwise interaction counts.
        Our corpus has sparse signals (most memories are irrelevant to any
        single pattern). We use log-scaled competition instead of raw total
        to avoid over-dilution: competition = log2(total_memories).

        Pattern-specific priors (alpha, beta):
        - preference (1, 4): prior mean 0.20, ~8 items to reach 0.5
        - style (1, 5): prior mean 0.17, subtler signals need more evidence
        - terminology (2, 3): prior mean 0.40, direct usage signal
        """
        if total_memories == 0 or not evidence_memory_ids:
            return 0.0

        import math
        evidence_count = len(evidence_memory_ids)

        # Pattern-specific Beta priors (alpha, beta)
        PRIORS = {
            'preference': (1.0, 4.0),
            'style':      (1.0, 5.0),
            'terminology': (2.0, 3.0),
        }
        alpha, beta = PRIORS.get(pattern_type, (1.0, 4.0))

        # Log-scaled competition: grows slowly with corpus size
        # 10 memories -> 3.3, 60 -> 5.9, 500 -> 9.0, 5000 -> 12.3
        competition = math.log2(max(2, total_memories))

        # MACLA-inspired Beta posterior with log competition
        posterior_mean = (alpha + evidence_count) / (alpha + beta + evidence_count + competition)

        # Recency adjustment (mild: 1.0 to 1.15)
        recency_bonus = self._calculate_recency_bonus(evidence_memory_ids)
        recency_factor = 1.0 + min(0.15, 0.075 * (recency_bonus - 1.0) / 0.2) if recency_bonus > 1.0 else 1.0

        # Temporal spread adjustment (0.9 to 1.1)
        distribution_factor = self._calculate_distribution_factor(evidence_memory_ids)

        # Final confidence
        confidence = posterior_mean * recency_factor * distribution_factor

        return min(0.95, round(confidence, 3))

    def _calculate_recency_bonus(self, memory_ids: List[int]) -> float:
        """Give bonus to patterns with recent evidence."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get timestamps
        placeholders = ','.join('?' * len(memory_ids))
        cursor.execute(f'''
            SELECT created_at FROM memories
            WHERE id IN ({placeholders})
            ORDER BY created_at DESC
        ''', memory_ids)

        timestamps = cursor.fetchall()
        conn.close()

        if not timestamps:
            return 1.0

        # Check if any memories are from last 30 days
        recent_count = 0
        cutoff = datetime.now() - timedelta(days=30)

        for ts_tuple in timestamps:
            ts_str = ts_tuple[0]
            try:
                ts = datetime.fromisoformat(ts_str.replace(' ', 'T'))
                if ts > cutoff:
                    recent_count += 1
            except (ValueError, AttributeError):
                pass

        # Bonus if >50% are recent
        if len(timestamps) > 0 and recent_count / len(timestamps) > 0.5:
            return 1.2
        else:
            return 1.0

    def _calculate_distribution_factor(self, memory_ids: List[int]) -> float:
        """Better confidence if memories are distributed over time, not just one session."""
        if len(memory_ids) < 3:
            return 0.8  # Penalize low sample size

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(memory_ids))
        cursor.execute(f'''
            SELECT created_at FROM memories
            WHERE id IN ({placeholders})
            ORDER BY created_at
        ''', memory_ids)

        timestamps = [row[0] for row in cursor.fetchall()]
        conn.close()

        if len(timestamps) < 2:
            return 0.8

        try:
            # Parse timestamps
            dates = []
            for ts_str in timestamps:
                try:
                    ts = datetime.fromisoformat(ts_str.replace(' ', 'T'))
                    dates.append(ts)
                except (ValueError, AttributeError):
                    pass

            if len(dates) < 2:
                return 0.8

            # Calculate time span
            time_span = (dates[-1] - dates[0]).days

            # If memories span multiple days, higher confidence
            if time_span > 7:
                return 1.1
            elif time_span > 1:
                return 1.0
            else:
                return 0.9  # All on same day = might be one-off

        except Exception:
            return 1.0


class PatternStore:
    """Handles pattern storage and retrieval."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """Initialize pattern tables if they don't exist, or recreate if schema is incomplete."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if existing tables have correct schema
        for table_name, required_cols in [
            ('identity_patterns', {'pattern_type', 'key', 'value', 'confidence'}),
            ('pattern_examples', {'pattern_id', 'memory_id'}),
        ]:
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if existing_cols and not required_cols.issubset(existing_cols):
                logger.warning(f"Dropping incomplete {table_name} table (missing: {required_cols - existing_cols})")
                cursor.execute(f'DROP TABLE IF EXISTS {table_name}')

        # Identity patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS identity_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                evidence_count INTEGER DEFAULT 1,
                memory_ids TEXT,
                category TEXT,
                profile TEXT DEFAULT 'default',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pattern_type, key, category, profile)
            )
        ''')

        # Add profile column if upgrading from older schema
        try:
            cursor.execute('ALTER TABLE identity_patterns ADD COLUMN profile TEXT DEFAULT "default"')
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Pattern examples table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id INTEGER NOT NULL,
                memory_id INTEGER NOT NULL,
                example_text TEXT,
                FOREIGN KEY (pattern_id) REFERENCES identity_patterns(id) ON DELETE CASCADE,
                FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_type ON identity_patterns(pattern_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_confidence ON identity_patterns(confidence)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_profile ON identity_patterns(profile)')

        conn.commit()
        conn.close()

    def save_pattern(self, pattern: Dict[str, Any]) -> int:
        """Save or update a pattern (scoped by profile)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        profile = pattern.get('profile', 'default')

        try:
            # Check if pattern exists for this profile
            cursor.execute('''
                SELECT id FROM identity_patterns
                WHERE pattern_type = ? AND key = ? AND category = ? AND profile = ?
            ''', (pattern['pattern_type'], pattern['key'], pattern['category'], profile))

            existing = cursor.fetchone()

            memory_ids_json = json.dumps(pattern['memory_ids'])

            if existing:
                # Update existing pattern
                pattern_id = existing[0]
                cursor.execute('''
                    UPDATE identity_patterns
                    SET value = ?, confidence = ?, evidence_count = ?,
                        memory_ids = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    pattern['value'],
                    pattern['confidence'],
                    pattern['evidence_count'],
                    memory_ids_json,
                    pattern_id
                ))
            else:
                # Insert new pattern
                cursor.execute('''
                    INSERT INTO identity_patterns
                    (pattern_type, key, value, confidence, evidence_count, memory_ids, category, profile)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern['pattern_type'],
                    pattern['key'],
                    pattern['value'],
                    pattern['confidence'],
                    pattern['evidence_count'],
                    memory_ids_json,
                    pattern['category'],
                    profile
                ))
                pattern_id = cursor.lastrowid

            # Save examples
            self._save_pattern_examples(cursor, pattern_id, pattern['memory_ids'], pattern['key'])

            conn.commit()
            return pattern_id

        finally:
            conn.close()

    def _save_pattern_examples(self, cursor, pattern_id: int, memory_ids: List[int], key: str):
        """Save representative examples for pattern."""
        # Clear old examples
        cursor.execute('DELETE FROM pattern_examples WHERE pattern_id = ?', (pattern_id,))

        # Save top 3 examples
        for memory_id in memory_ids[:3]:
            cursor.execute('SELECT content FROM memories WHERE id = ?', (memory_id,))
            row = cursor.fetchone()

            if row:
                content = row[0]
                excerpt = self._extract_relevant_excerpt(content, key)

                cursor.execute('''
                    INSERT INTO pattern_examples (pattern_id, memory_id, example_text)
                    VALUES (?, ?, ?)
                ''', (pattern_id, memory_id, excerpt))

    def _extract_relevant_excerpt(self, content: str, key: str) -> str:
        """Extract 150-char excerpt showing pattern."""
        # Find first mention of key term
        key_lower = key.lower().replace('_', ' ')
        idx = content.lower().find(key_lower)

        if idx >= 0:
            start = max(0, idx - 50)
            end = min(len(content), idx + 100)
            excerpt = content[start:end]
            return excerpt if len(excerpt) <= 150 else excerpt[:150] + '...'

        # Fallback: first 150 chars
        return content[:150] + ('...' if len(content) > 150 else '')

    def get_patterns(self, min_confidence: float = 0.7, pattern_type: Optional[str] = None,
                     profile: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get patterns above confidence threshold, optionally filtered by profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query with optional filters
        conditions = ['confidence >= ?']
        params = [min_confidence]

        if pattern_type:
            conditions.append('pattern_type = ?')
            params.append(pattern_type)

        if profile:
            conditions.append('profile = ?')
            params.append(profile)

        where_clause = ' AND '.join(conditions)
        cursor.execute(f'''
            SELECT id, pattern_type, key, value, confidence, evidence_count,
                   updated_at, created_at, category
            FROM identity_patterns
            WHERE {where_clause}
            ORDER BY confidence DESC, evidence_count DESC
        ''', params)

        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'id': row[0],
                'pattern_type': row[1],
                'key': row[2],
                'value': row[3],
                'confidence': row[4],
                'evidence_count': row[5],
                'frequency': row[5],
                'last_seen': row[6],
                'created_at': row[7],
                'category': row[8]
            })

        conn.close()
        return patterns


class PatternLearner:
    """Main pattern learning orchestrator."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.frequency_analyzer = FrequencyAnalyzer(db_path)
        self.context_analyzer = ContextAnalyzer(db_path)
        self.terminology_learner = TerminologyLearner(db_path)
        self.confidence_scorer = ConfidenceScorer(db_path)
        self.pattern_store = PatternStore(db_path)

    def _get_active_profile(self) -> str:
        """Get the currently active profile name from config."""
        config_file = MEMORY_DIR / "profiles.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return config.get('active_profile', 'default')
            except (json.JSONDecodeError, IOError):
                pass
        return 'default'

    def weekly_pattern_update(self) -> Dict[str, int]:
        """Full pattern analysis of all memories for active profile. Run this weekly."""
        active_profile = self._get_active_profile()
        print(f"Starting weekly pattern update for profile: {active_profile}...")

        # Get memory IDs for active profile only
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM memories WHERE profile = ? ORDER BY created_at',
                       (active_profile,))
        all_memory_ids = [row[0] for row in cursor.fetchall()]
        total_memories = len(all_memory_ids)
        conn.close()

        if total_memories == 0:
            print(f"No memories found for profile '{active_profile}'. Add memories first.")
            return {'preferences': 0, 'styles': 0, 'terminology': 0}

        print(f"Analyzing {total_memories} memories for profile '{active_profile}'...")

        # Run all analyzers
        preferences = self.frequency_analyzer.analyze_preferences(all_memory_ids)
        print(f"  Found {len(preferences)} preference patterns")

        styles = self.context_analyzer.analyze_style(all_memory_ids)
        print(f"  Found {len(styles)} style patterns")

        terms = self.terminology_learner.learn_terminology(all_memory_ids)
        print(f"  Found {len(terms)} terminology patterns")

        # Recalculate confidence scores and save all patterns (tagged with profile)
        counts = {'preferences': 0, 'styles': 0, 'terminology': 0}

        for pattern in preferences.values():
            confidence = self.confidence_scorer.calculate_confidence(
                pattern['pattern_type'],
                pattern['key'],
                pattern['value'],
                pattern['memory_ids'],
                total_memories
            )
            pattern['confidence'] = round(confidence, 2)
            pattern['profile'] = active_profile
            self.pattern_store.save_pattern(pattern)
            counts['preferences'] += 1

        for pattern in styles.values():
            confidence = self.confidence_scorer.calculate_confidence(
                pattern['pattern_type'],
                pattern['key'],
                pattern['value'],
                pattern['memory_ids'],
                total_memories
            )
            pattern['confidence'] = round(confidence, 2)
            pattern['profile'] = active_profile
            self.pattern_store.save_pattern(pattern)
            counts['styles'] += 1

        for pattern in terms.values():
            confidence = self.confidence_scorer.calculate_confidence(
                pattern['pattern_type'],
                pattern['key'],
                pattern['value'],
                pattern['memory_ids'],
                total_memories
            )
            pattern['confidence'] = round(confidence, 2)
            pattern['profile'] = active_profile
            self.pattern_store.save_pattern(pattern)
            counts['terminology'] += 1

        print(f"\nPattern update complete:")
        print(f"  {counts['preferences']} preferences")
        print(f"  {counts['styles']} styles")
        print(f"  {counts['terminology']} terminology")

        return counts

    def on_new_memory(self, memory_id: int):
        """Incremental update when new memory is added."""
        active_profile = self._get_active_profile()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM memories WHERE profile = ?',
                       (active_profile,))
        total = cursor.fetchone()[0]
        conn.close()

        # Only do incremental updates if we have many memories (>50)
        if total > 50:
            # TODO: Implement true incremental update
            print(f"New memory #{memory_id} added. Run weekly_pattern_update() to update patterns.")
        else:
            # For small memory counts, just do full update
            self.weekly_pattern_update()

    def get_patterns(self, min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """Query patterns above confidence threshold for active profile."""
        active_profile = self._get_active_profile()
        return self.pattern_store.get_patterns(min_confidence, profile=active_profile)

    def get_identity_context(self, min_confidence: float = 0.7) -> str:
        """Format patterns for Claude context injection."""
        patterns = self.get_patterns(min_confidence)

        if not patterns:
            return "## Working with User - Learned Patterns\n\nNo patterns learned yet. Add more memories to build your profile."

        # Group by pattern type
        sections = {
            'preference': [],
            'style': [],
            'terminology': []
        }

        for p in patterns:
            sections[p['pattern_type']].append(
                f"- **{p['key'].replace('_', ' ').title()}:** {p['value']} "
                f"(confidence: {p['confidence']:.0%}, {p['evidence_count']} examples)"
            )

        output = "## Working with User - Learned Patterns\n\n"

        if sections['preference']:
            output += "**Technology Preferences:**\n" + '\n'.join(sections['preference']) + '\n\n'

        if sections['style']:
            output += "**Coding Style:**\n" + '\n'.join(sections['style']) + '\n\n'

        if sections['terminology']:
            output += "**Terminology:**\n" + '\n'.join(sections['terminology']) + '\n'

        return output


# CLI Interface
if __name__ == "__main__":
    import sys

    learner = PatternLearner()

    if len(sys.argv) < 2:
        print("Pattern Learner - Identity Profile Extraction")
        print("\nUsage:")
        print("  python pattern_learner.py update           # Full pattern update (weekly)")
        print("  python pattern_learner.py list [min_conf]  # List learned patterns (default: 0.7)")
        print("  python pattern_learner.py context [min]    # Get context for Claude")
        print("  python pattern_learner.py stats            # Pattern statistics")
        sys.exit(0)

    command = sys.argv[1]

    if command == "update":
        counts = learner.weekly_pattern_update()
        print(f"\nTotal patterns learned: {sum(counts.values())}")

    elif command == "list":
        min_conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
        patterns = learner.get_patterns(min_conf)

        if not patterns:
            print(f"No patterns found with confidence >= {min_conf:.0%}")
        else:
            print(f"\n{'Type':<15} {'Category':<12} {'Pattern':<30} {'Confidence':<12} {'Evidence':<10}")
            print("-" * 95)

            for p in patterns:
                pattern_display = f"{p['key'].replace('_', ' ').title()}: {p['value']}"
                if len(pattern_display) > 28:
                    pattern_display = pattern_display[:28] + "..."

                print(f"{p['pattern_type']:<15} {p['category']:<12} {pattern_display:<30} "
                      f"{p['confidence']:>6.0%}        {p['evidence_count']:<10}")

    elif command == "context":
        min_conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.7
        context = learner.get_identity_context(min_conf)
        print(context)

    elif command == "stats":
        patterns = learner.get_patterns(0.5)  # Include all patterns

        if not patterns:
            print("No patterns learned yet.")
        else:
            by_type = Counter([p['pattern_type'] for p in patterns])
            by_category = Counter([p['category'] for p in patterns])

            avg_confidence = sum(p['confidence'] for p in patterns) / len(patterns)
            high_conf = len([p for p in patterns if p['confidence'] >= 0.8])

            print(f"\nPattern Statistics:")
            print(f"  Total patterns: {len(patterns)}")
            print(f"  Average confidence: {avg_confidence:.0%}")
            print(f"  High confidence (>=80%): {high_conf}")
            print(f"\nBy Type:")
            for ptype, count in by_type.most_common():
                print(f"  {ptype}: {count}")
            print(f"\nBy Category:")
            for cat, count in by_category.most_common():
                print(f"  {cat}: {count}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
