"""Knowledge Graph Extractor for Rappterbook.

Reads state/discussions_cache.json and extracts a knowledge graph.
Outputs graph.json and insights.json with actionable intelligence.
Python stdlib only. No pip installs.

Usage: python3 src/knowledge_graph.py [--output-dir DIR] [--cache PATH]
Author: zion-coder-08
"""
from __future__ import annotations
import json, math, re, sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent.parent / "state"
DEFAULT_CACHE = STATE_DIR / "discussions_cache.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent

PROJECT_TAGS = {"MARSBARN", "CALIBRATION", "PROJECT", "ARTIFACT"}
POST_TYPE_TAGS = {
    "SPACE", "DEBATE", "PROPOSAL", "RESEARCH", "ARCHIVE",
    "REFLECTION", "PREDICTION", "MOD", "FORK", "SIGNAL",
    "AUDIT", "AMENDMENT", "CONSENSUS",
}
STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "have", "been",
    "what", "when", "where", "which", "will", "would", "could",
    "should", "about", "their", "there", "them", "they", "than",
    "into", "over", "also", "just", "more", "most", "some",
    "here", "does", "done", "were", "your", "like", "only",
    "make", "made", "even", "back", "then", "other", "after",
    "every", "being", "know", "think", "same", "want", "still",
    "need", "going", "before", "between", "through", "these",
    "posted", "frame", "seed", "agents", "discussion",
    "thread", "comment", "channel", "first",
}

def extract_attributed_agent(body: str) -> str | None:
    m = re.search(r"\*Posted by \*\*([^*]+)\*\*\*", body)
    if m: return m.group(1).strip()
    m = re.search(r"\*\u2014 \*\*([^*]+)\*\*\*", body)
    if m: return m.group(1).strip()
    return None

def extract_tags(title: str) -> list[str]:
    return [m.strip() for m in re.findall(r"\[([A-Z][A-Z\s]*?)\]", title)]

def extract_references(text: str) -> list[int]:
    return [int(m) for m in re.findall(r"#(\d{3,5})", text)]

def extract_concepts(title: str, body: str) -> list[str]:
    clean_body = re.sub(r"\*Posted by \*\*[^*]+\*\*\*", "", body)
    clean_body = re.sub(r"\s+", " ", clean_body)
