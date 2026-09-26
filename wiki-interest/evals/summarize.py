"""Print tool calls, final answer, cost and time from a Claude Code stream-json transcript.

Usage: python3 evals/summarize.py <transcript.jsonl>
"""
import json
import sys

calls = 0
for line in open(sys.argv[1], encoding="utf-8"):
    e = json.loads(line)
    if e["type"] == "system" and e.get("subtype") == "init":
        print(f"session: {e.get('session_id')}  model: {e.get('model')}")
    elif e["type"] == "assistant":
        for c in e["message"]["content"]:
            if c["type"] == "tool_use":
                calls += 1
                arg = c["input"].get("command") or c["input"].get("file_path") or c["input"].get("skill") or c["input"]
                print(f"TOOL {calls}: {c['name']}: {str(arg)[:220]}")
    elif e["type"] == "user" and isinstance(e["message"]["content"], list):
        for c in e["message"]["content"]:
            if c.get("type") == "tool_result":
                body = c["content"] if isinstance(c["content"], str) else " ".join(x.get("text", "") for x in c["content"])
                print("   -> " + body[:160].replace("\n", " | "))
    elif e["type"] == "result":
        print(f"\nturns: {e.get('num_turns')}  tool calls: {calls}  cost: ${e.get('total_cost_usd', 0):.3f}  "
              f"time: {e.get('duration_ms', 0) / 1000:.0f}s")
        print("\nFINAL ANSWER:\n" + (e.get("result") or ""))
