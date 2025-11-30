#!/usr/bin/env python3
"""
Rebuild the knowledge base index on demand.

Usage:
  python scripts/reindex_kb.py [--path ./knowledge_base]
"""

import argparse
from agents.research_agent import ResearchAgent


def main():
    parser = argparse.ArgumentParser(description="Rebuild KB index")
    parser.add_argument("--path", default="./knowledge_base", help="KB folder path")
    args = parser.parse_args()

    agent = ResearchAgent({}, knowledge_base_path=args.path)
    stats = agent.reload_index()
    print("KB reloaded:")
    print(f"  Path:      {stats['kb_path']}")
    print(f"  Documents: {stats['documents']}")
    print(f"  Terms:     {stats['terms']}")
    print(f"  Timestamp: {stats['timestamp']}")


if __name__ == "__main__":
    main()

