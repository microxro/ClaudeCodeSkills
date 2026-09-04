#!/usr/bin/env python3
"""
query.py — read graph.json and answer structural questions.

Subcommands:
  stats                          overview counts, god nodes, community sizes
  search TEXT                    find node ids whose label/path contains TEXT
  neighbors NODE                 immediate neighbors of a node, grouped by relation
  explain NODE                   neighbors + docstring/context, a fuller view than `neighbors`
  path NODE_A NODE_B              shortest path between two nodes (BFS, undirected)

NODE arguments accept either an exact node id or a search string; if a search
string matches more than one node, all candidates are listed instead of
guessing which one you meant.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict, deque


def load_graph(root, out_dir=".graph"):
    path = os.path.join(root, out_dir, "graph.json")
    if not os.path.isfile(path):
        sys.exit(f"No graph found at {path} — run build_graph.py first.")
    with open(path) as f:
        return json.load(f)


def resolve_node(graph, query):
    """Exact id, then exact label, then substring — in that preference order,
    so a plain name like "app.js" or "resolveByRecency" resolves cleanly
    instead of getting lost among every node whose id merely contains it."""
    nodes = graph["nodes"]
    if query in nodes:
        return [query]
    q = query.lower()
    exact_label = [nid for nid, n in nodes.items() if (n.get("label", "") or "").lower() == q]
    if len(exact_label) == 1:
        return exact_label
    if exact_label:
        return exact_label
    return [nid for nid, n in nodes.items()
            if q in (n.get("label", "") or "").lower() or q in nid.lower()]


def cmd_stats(graph, args):
    nodes, edges = graph["nodes"], graph["edges"]
    type_counts = Counter(n["type"] for n in nodes.values())
    conf_counts = Counter(e.get("confidence") for e in edges)
    print(f"{len(nodes)} nodes, {len(edges)} edges, {len(graph.get('ambiguous_edges', []))} ambiguous kept aside")
    print("by type:  " + ", ".join(f"{t}={c}" for t, c in type_counts.most_common()))
    print("by conf:  " + ", ".join(f"{k}={v}" for k, v in conf_counts.most_common()))
    print("\ntop god nodes:")
    degree = Counter(graph.get("degree", {}))
    for nid, d in degree.most_common(12):
        n = nodes.get(nid, {})
        print(f"  {d:>4}  {n.get('label', nid)}  ({n.get('type', '?')}{', ' + n['path'] if n.get('path') else ''})")


def cmd_search(graph, args):
    matches = resolve_node(graph, args.text)
    if not matches:
        print("no matches"); return
    for nid in matches[:40]:
        n = graph["nodes"].get(nid, {})
        print(f"  {nid}   ({n.get('type', '?')})")
    if len(matches) > 40:
        print(f"  ...and {len(matches) - 40} more")


def _neighbors(graph, nid):
    out = defaultdict(list)
    for e in graph["edges"]:
        if e["source"] == nid:
            out[("out", e["relation"], e.get("confidence"))].append(e["target"])
        elif e["target"] == nid:
            out[("in", e["relation"], e.get("confidence"))].append(e["source"])
    return out


def cmd_neighbors(graph, args):
    matches = resolve_node(graph, args.node)
    if len(matches) == 0:
        print("no matches"); return
    if len(matches) > 1:
        print(f"{len(matches)} nodes match '{args.node}' — be more specific:")
        for nid in matches[:20]:
            print(f"  {nid}")
        return
    nid = matches[0]
    n = graph["nodes"].get(nid, {})
    print(f"{n.get('label', nid)}  ({n.get('type')}{', ' + n['path'] if n.get('path') else ''})")
    grouped = _neighbors(graph, nid)
    if not grouped:
        print("  (no edges)")
    for (direction, relation, conf), targets in sorted(grouped.items()):
        arrow = "<-" if direction == "in" else "->"
        label = f"  {arrow} {relation} [{conf}]"
        names = [graph["nodes"].get(t, {}).get("label", t) for t in targets[:10]]
        more = f" (+{len(targets) - 10} more)" if len(targets) > 10 else ""
        print(f"{label}: {', '.join(names)}{more}")


def cmd_explain(graph, args):
    matches = resolve_node(graph, args.node)
    if len(matches) != 1:
        cmd_neighbors(graph, args)
        return
    nid = matches[0]
    n = graph["nodes"].get(nid, {})
    print(f"# {n.get('label', nid)}")
    print(f"type: {n.get('type')}")
    if n.get("path"):
        print(f"location: {n['path']}" + (f":{n['line']}" if n.get("line") else ""))
    if n.get("docstring"):
        print(f"\ndocstring:\n  {n['docstring'][:400]}")
    degree = graph.get("degree", {}).get(nid, 0)
    print(f"\ndegree (structural importance): {degree}")
    print()
    cmd_neighbors(graph, args)


def cmd_path(graph, args):
    a_matches = resolve_node(graph, args.a)
    b_matches = resolve_node(graph, args.b)
    if len(a_matches) != 1 or len(b_matches) != 1:
        if len(a_matches) != 1:
            print(f"'{args.a}' is ambiguous or not found: {a_matches[:10]}")
        if len(b_matches) != 1:
            print(f"'{args.b}' is ambiguous or not found: {b_matches[:10]}")
        return
    a, b = a_matches[0], b_matches[0]

    adj = defaultdict(list)
    for e in graph["edges"]:
        adj[e["source"]].append((e["target"], e["relation"], e.get("confidence")))
        adj[e["target"]].append((e["source"], e["relation"], e.get("confidence")))

    prev = {a: None}
    q = deque([a])
    while q:
        cur = q.popleft()
        if cur == b:
            break
        for nxt, relation, conf in adj.get(cur, []):
            if nxt not in prev:
                prev[nxt] = (cur, relation, conf)
                q.append(nxt)

    if b not in prev:
        print(f"no path found between {a} and {b} (within {len(prev)} reachable nodes from {a})")
        return

    path = []
    cur = b
    while cur != a:
        p, relation, conf = prev[cur]
        path.append((p, relation, conf, cur))
        cur = p
    path.reverse()

    print(f"{graph['nodes'].get(a, {}).get('label', a)}")
    for p, relation, conf, cur in path:
        label = graph["nodes"].get(cur, {}).get("label", cur)
        print(f"  --{relation} [{conf}]--> {label}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--out-dir", default=".graph")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stats")
    p = sub.add_parser("search"); p.add_argument("text")
    p = sub.add_parser("neighbors"); p.add_argument("node")
    p = sub.add_parser("explain"); p.add_argument("node")
    p = sub.add_parser("path"); p.add_argument("a"); p.add_argument("b")
    args = ap.parse_args()

    graph = load_graph(os.path.abspath(args.root), args.out_dir)
    {"stats": cmd_stats, "search": cmd_search, "neighbors": cmd_neighbors,
     "explain": cmd_explain, "path": cmd_path}[args.cmd](graph, args)


if __name__ == "__main__":
    main()
