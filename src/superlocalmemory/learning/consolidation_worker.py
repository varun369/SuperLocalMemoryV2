# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the Elastic License 2.0 - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Sleep-Time Consolidation Worker — background memory maintenance.

Runs periodically (every 6 hours or on-demand) to:
1. Decay confidence on unused facts (floor 0.1)
2. Deduplicate near-identical facts
3. Auto-retrain the adaptive ranker when signal threshold is met
4. Report consolidation stats

Inspired by: Letta's sleep-time compute, neuroscience memory consolidation.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class ConsolidationWorker:
    """Background memory maintenance worker.

    Call `run()` periodically or via dashboard button.
    All operations are safe — they improve quality without losing data.
    """

    def __init__(self, memory_db: str | Path, learning_db: str | Path) -> None:
        self._memory_db = str(memory_db)
        self._learning_db = str(learning_db)

    def run(self, profile_id: str, dry_run: bool = False) -> dict:
        """Run full consolidation cycle. Returns stats."""
        stats = {
            "decayed": 0,
            "deduped": 0,
            "retrained": False,
            "signal_count": 0,
            "ranker_phase": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Confidence decay on unused facts
        try:
            from superlocalmemory.learning.signals import LearningSignals
            decayed = LearningSignals.decay_confidence(
                self._memory_db, profile_id, rate=0.001,
            )
            stats["decayed"] = decayed
            if not dry_run:
                logger.info("Confidence decay: %d facts affected", decayed)
        except Exception as exc:
            logger.debug("Decay failed: %s", exc)

        # 2. Deduplication (mark near-identical facts)
        try:
            deduped = self._deduplicate(profile_id, dry_run)
            stats["deduped"] = deduped
        except Exception as exc:
            logger.debug("Dedup failed: %s", exc)

        # 3. Generate behavioral patterns from memories
        try:
            patterns = self._generate_patterns(profile_id, dry_run)
            stats["patterns_generated"] = patterns
        except Exception as exc:
            logger.debug("Pattern generation failed: %s", exc)

        # 4. Check if ranker should retrain
        try:
            from superlocalmemory.learning.feedback import FeedbackCollector
            collector = FeedbackCollector(Path(self._learning_db))
            signal_count = collector.get_feedback_count(profile_id)
            stats["signal_count"] = signal_count
            stats["ranker_phase"] = 1 if signal_count < 50 else (2 if signal_count < 200 else 3)

            # Auto-retrain at threshold crossings
            if signal_count >= 200 and not dry_run:
                retrained = self._retrain_ranker(profile_id, signal_count)
                stats["retrained"] = retrained
        except Exception as exc:
            logger.debug("Retrain check failed: %s", exc)

        return stats

    def _deduplicate(self, profile_id: str, dry_run: bool) -> int:
        """Find and mark near-duplicate facts.

        Uses content similarity (exact prefix match for now).
        Does NOT delete — marks with lower confidence.
        """
        try:
            conn = sqlite3.connect(self._memory_db, timeout=10)
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                "SELECT fact_id, content FROM atomic_facts "
                "WHERE profile_id = ? ORDER BY created_at",
                (profile_id,),
            ).fetchall()

            seen_prefixes: dict[str, str] = {}
            duplicates = []

            for r in rows:
                d = dict(r)
                prefix = d["content"][:100].strip().lower()
                if prefix in seen_prefixes:
                    duplicates.append(d["fact_id"])
                else:
                    seen_prefixes[prefix] = d["fact_id"]

            if duplicates and not dry_run:
                for fid in duplicates:
                    conn.execute(
                        "UPDATE atomic_facts SET confidence = MAX(0.1, confidence * 0.5) "
                        "WHERE fact_id = ?",
                        (fid,),
                    )
                conn.commit()

            conn.close()
            return len(duplicates)
        except Exception:
            return 0

    def _generate_patterns(self, profile_id: str, dry_run: bool) -> int:
        """Mine behavioral patterns from existing memories.

        Scans all facts to detect:
        - Tech preferences (language/framework mentions)
        - Topic clusters (frequently discussed subjects)
        - Temporal patterns (time-of-day activity)
        """
        try:
            from superlocalmemory.learning.behavioral import BehavioralPatternStore
            import re
            from collections import Counter

            conn = sqlite3.connect(self._memory_db, timeout=10)
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row

            facts = conn.execute(
                "SELECT content, created_at FROM atomic_facts "
                "WHERE profile_id = ? ORDER BY created_at DESC LIMIT 500",
                (profile_id,),
            ).fetchall()
            conn.close()

            if len(facts) < 10:
                return 0

            store = BehavioralPatternStore(self._learning_db)
            generated = 0

            # Tech preferences: detect technology mentions
            tech_keywords = {
                "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
                "react": "React", "vue": "Vue", "angular": "Angular",
                "postgresql": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite",
                "docker": "Docker", "kubernetes": "Kubernetes", "aws": "AWS",
                "azure": "Azure", "gcp": "GCP", "node": "Node.js",
                "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
                "rust": "Rust", "go": "Go", "java": "Java",
                "git": "Git", "npm": "npm", "pip": "pip",
                "langchain": "LangChain", "ollama": "Ollama", "pytorch": "PyTorch",
                "claude": "Claude", "openai": "OpenAI", "anthropic": "Anthropic",
            }

            tech_counts = Counter()
            for f in facts:
                content = dict(f)["content"].lower()
                for keyword, label in tech_keywords.items():
                    if keyword in content:
                        tech_counts[label] += 1

            for tech, count in tech_counts.most_common(15):
                if count >= 3 and not dry_run:
                    confidence = min(1.0, count / 20)
                    store.record_pattern(
                        profile_id=profile_id,
                        pattern_type="tech_preference",
                        data={"topic": tech, "pattern_key": tech, "value": tech,
                               "key": "tech", "evidence": count},
                        success_rate=confidence,
                        confidence=confidence,
                    )
                    generated += 1

            # Topic clusters: most discussed subjects
            word_counts = Counter()
            stopwords = frozenset({
                "the", "is", "a", "an", "in", "on", "at", "to", "for", "of",
                "and", "or", "not", "with", "that", "this", "was", "are", "be",
                "has", "had", "have", "from", "by", "it", "its", "as", "but",
            })
            for f in facts:
                words = re.findall(r'\b[a-zA-Z]{4,}\b', dict(f)["content"].lower())
                for w in words:
                    if w not in stopwords:
                        word_counts[w] += 1

            for topic, count in word_counts.most_common(10):
                if count >= 5 and not dry_run:
                    confidence = min(1.0, count / 30)
                    store.record_pattern(
                        profile_id=profile_id,
                        pattern_type="interest",
                        data={"topic": topic, "pattern_key": topic,
                               "count": count, "evidence": count},
                        success_rate=confidence,
                        confidence=confidence,
                    )
                    generated += 1

            # Temporal patterns: time-of-day activity
            hour_counts = Counter()
            for f in facts:
                created = dict(f).get("created_at", "")
                if "T" in created:
                    try:
                        hour = int(created.split("T")[1][:2])
                        period = "morning" if 6 <= hour < 12 else (
                            "afternoon" if 12 <= hour < 18 else (
                                "evening" if 18 <= hour < 22 else "night"))
                        hour_counts[period] += 1
                    except (ValueError, IndexError):
                        pass

            for period, count in hour_counts.most_common():
                if count >= 3 and not dry_run:
                    total = sum(hour_counts.values())
                    pct = round(count / total * 100)
                    store.record_pattern(
                        profile_id=profile_id,
                        pattern_type="temporal",
                        data={"topic": period, "pattern_key": period,
                               "value": f"{period} ({pct}%)", "evidence": count,
                               "key": period, "distribution": dict(hour_counts)},
                        success_rate=pct / 100,
                        confidence=min(1.0, count / 20),
                    )
                    generated += 1

            return generated
        except Exception as exc:
            logger.debug("Pattern generation error: %s", exc)
            return 0

    def _retrain_ranker(self, profile_id: str, signal_count: int) -> bool:
        """Retrain the adaptive ranker from accumulated feedback."""
        try:
            from superlocalmemory.learning.feedback import FeedbackCollector
            from superlocalmemory.learning.ranker import AdaptiveRanker

            collector = FeedbackCollector(Path(self._learning_db))
            feedback = collector.get_feedback(profile_id, limit=500)

            if len(feedback) < 200:
                return False

            # Build training data from feedback
            training_data = []
            for f in feedback:
                label = f.get("signal_value", 0.5)
                training_data.append({
                    "features": {"signal_value": label},
                    "label": label,
                })

            ranker = AdaptiveRanker(signal_count=signal_count)
            trained = ranker.train(training_data)

            if trained:
                logger.info("Ranker retrained with %d examples (Phase 3)", len(training_data))

            return trained
        except Exception as exc:
            logger.debug("Retrain failed: %s", exc)
            return False
