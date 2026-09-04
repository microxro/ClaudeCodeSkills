#!/usr/bin/env python3
"""
build_graph.py — merge extraction fragments into a persistent graph.

Takes the raw fragments extract.py produced (plus, optionally, a file of
semantic fragments Claude itself proposed by reading docs/comments) and:

  1. Merges/dedupes nodes.
  2. Resolves raw import/call/inherits targets against the real symbol
     table, and assigns confidence per the resolution outcome (see
     `assign_confidence` below — this is the whole point of the exercise:
     an edge's confidence should reflect how it was actually established,
     never just default to "looks right").
  3. Computes degree centrality ("god nodes") and communities (label
     propagation, a lightweight stdlib-only stand-in for the Leiden
     algorithm the original Graphify project uses — same idea, much
     simpler implementation, and that difference is worth knowing about
     rather than pretending otherwise).
  4. Writes graph.json (the persistent, queryable graph), GRAPH_REPORT.md
     (a human-readable summary), and graph.html (a self-contained
     visualization — no CDN dependency, so it works offline).
  5. Supports incremental updates: given an existing graph.json, only the
     files whose content hash changed get re-extracted and re-merged.

Usage:
    python3 build_graph.py <repo_root> --out-dir .graph [--update]
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))


def run_extract(root, out_dir, files=None):
    extract_py = os.path.join(HERE, "extract.py")
    cmd = [sys.executable, extract_py, root]
    if files:
        cmd += ["--files"] + files
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"extract.py failed (exit {result.returncode})")
    return json.loads(result.stdout)["fragments"]


def merge_nodes(fragments, semantic_fragments=None):
    nodes = {}
    raw_edges = []
    errors = []
    file_hashes = {}
    for frag in fragments:
        if frag.get("hash") is not None and frag.get("file_id"):
            file_hashes[frag["file_id"]] = frag["hash"]
        for n in frag.get("nodes", []):
            nodes[n["id"]] = n  # last write wins; identical facts re-extract identically
        raw_edges.extend(frag.get("edges", []))
        errors.extend(frag.get("errors", []))

    semantic_edges = []
    if semantic_fragments:
        for frag in semantic_fragments:
            for n in frag.get("nodes", []):
                nodes.setdefault(n["id"], n)
            for e in frag.get("edges", []):
                e.setdefault("method", "semantic")
                semantic_edges.append(e)

    return nodes, raw_edges, semantic_edges, errors, file_hashes


def build_symbol_index(nodes):
    """simple_name -> [node_id, ...] for function/method/class nodes."""
    idx = defaultdict(list)
    for nid, n in nodes.items():
        if n["type"] in ("function", "method", "class"):
            simple = n["label"]
            idx[simple].append(nid)
    return idx


def resolve_import_target(raw_target, source_file, all_file_ids, language):
    """Best-effort: does this import string point at a real file in the repo?"""
    if language == "python":
        candidates = _python_import_candidates(raw_target, source_file)
    else:
        candidates = _js_import_candidates(raw_target, source_file)
    for c in candidates:
        if c in all_file_ids:
            return c
    return None


def _python_import_candidates(raw_target, source_file):
    out = []
    level = len(raw_target) - len(raw_target.lstrip("."))
    mod = raw_target[level:]
    parts = mod.split(".") if mod else []
    if level > 0:
        base_dir = os.path.dirname(source_file)
        for _ in range(level - 1):
            base_dir = os.path.dirname(base_dir)
        path_no_ext = "/".join([base_dir] + parts) if parts else base_dir
    else:
        path_no_ext = "/".join(parts)
    path_no_ext = path_no_ext.strip("/")
    if path_no_ext:
        out.append(path_no_ext + ".py")
        out.append(path_no_ext + "/__init__.py")
    return out


def _js_import_candidates(raw_target, source_file):
    out = []
    exts = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]
    if raw_target.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(source_file), raw_target)).replace(os.sep, "/")
        for ext in exts:
            out.append(base + ext)
        for ext in exts:
            out.append(base + "/index" + ext)
        out.append(base)
    return out


def assign_confidence_and_resolve(raw_edges, nodes, symbol_index, all_file_ids):
    resolved = []
    ambiguous = []
    for e in raw_edges:
        rel = e["relation"]
        method = e.get("method", "regex")
        if rel == "imports":
            raw_target = e.get("raw_target", e["target"])
            src_file = e["source"]
            language = nodes.get(src_file, {}).get("language", "python" if method == "ast" else "javascript")
            target_file = resolve_import_target(raw_target, src_file, all_file_ids, language)
            out = dict(e)
            out["confidence"] = "EXTRACTED"
            out["score"] = 1.0
            if target_file:
                out["target"] = target_file
                out["target_kind"] = "internal"
            else:
                out["target"] = raw_target
                out["target_kind"] = "external"
                nodes.setdefault(raw_target, {"id": raw_target, "type": "external", "label": raw_target})
            resolved.append(out)

        elif rel == "defines":
            out = dict(e)
            if method == "ast":
                out["confidence"] = "EXTRACTED"
                out["score"] = 1.0
            else:
                out["confidence"] = "INFERRED"
                out["score"] = 0.85
            resolved.append(out)

        elif rel in ("calls", "uses", "inherits"):
            raw_target = e.get("raw_target", e["target"])
            candidates = symbol_index.get(raw_target, [])
            # A call shouldn't resolve to itself.
            candidates = [c for c in candidates if c != e["source"]]
            out = dict(e)
            if len(candidates) == 1:
                target = candidates[0]
                out["target"] = target
                same_file = nodes.get(target, {}).get("path") == nodes.get(e["source"], {}).get("path", e["source"])
                base = 0.9 if method == "ast" else 0.75
                if same_file:
                    base = min(0.95, base + 0.05)
                out["confidence"] = "INFERRED"
                out["score"] = base
                resolved.append(out)
            elif len(candidates) == 0:
                ext_id = "unresolved:" + raw_target
                nodes.setdefault(ext_id, {"id": ext_id, "type": "external_symbol", "label": raw_target})
                out["target"] = ext_id
                out["confidence"] = "AMBIGUOUS"
                out["score"] = None
                out["reason"] = "no matching definition found in this graph"
                ambiguous.append(out)
            else:
                ext_id = "ambiguous:" + raw_target
                nodes.setdefault(ext_id, {"id": ext_id, "type": "external_symbol", "label": raw_target})
                out["target"] = ext_id
                out["confidence"] = "AMBIGUOUS"
                out["score"] = None
                out["candidates"] = candidates
                out["reason"] = f"{len(candidates)} definitions share this name"
                ambiguous.append(out)
        else:
            out = dict(e)
            out.setdefault("confidence", "INFERRED")
            out.setdefault("score", 0.7)
            resolved.append(out)

    return resolved, ambiguous


def compute_degree(nodes, edges):
    degree = Counter()
    for e in edges:
        if e.get("confidence") == "AMBIGUOUS":
            continue
        degree[e["source"]] += 1
        degree[e["target"]] += 1
    return degree


def label_propagation(node_ids, edges, seed=42, max_iter=20):
    adj = defaultdict(set)
    node_set = set(node_ids)
    for e in edges:
        if e.get("confidence") == "AMBIGUOUS":
            continue
        s, t = e["source"], e["target"]
        if s in node_set and t in node_set and s != t:
            adj[s].add(t)
            adj[t].add(s)

    labels = {n: n for n in node_ids}
    order = list(node_ids)
    rnd = random.Random(seed)
    for _ in range(max_iter):
        rnd.shuffle(order)
        changed = False
        for n in order:
            neighbors = adj.get(n)
            if not neighbors:
                continue
            counts = Counter(labels[nb] for nb in neighbors)
            top_count = counts.most_common(1)[0][1]
            candidates = sorted(lab for lab, c in counts.items() if c == top_count)
            if labels[n] not in candidates:
                labels[n] = rnd.choice(candidates)
                changed = True
        if not changed:
            break

    communities = defaultdict(list)
    for n, lab in labels.items():
        communities[lab].append(n)
    return communities


HTML_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<title>graph.html — repo knowledge graph</title>
<style>
  html,body{margin:0;height:100%;background:#0b0e14;color:#e6e6e6;font:13px -apple-system,Segoe UI,sans-serif;overflow:hidden}
  #tip{position:fixed;pointer-events:none;background:#1c2230;border:1px solid #3a4256;padding:6px 9px;
       border-radius:6px;font-size:12px;max-width:340px;display:none;z-index:5}
  #legend{position:fixed;top:10px;left:10px;background:#12151ccc;border:1px solid #2a3040;border-radius:8px;
          padding:10px 12px;line-height:1.7}
  #legend b{display:block;margin-bottom:4px}
  .sw{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
  #hint{position:fixed;bottom:10px;left:10px;color:#7a8296;font-size:11px}
</style></head><body>
<div id="legend"><b>graph.html</b>__LEGEND__</div>
<div id="hint">scroll to zoom · drag to pan · drag a node to move it · click a node to focus its neighbors</div>
<div id="tip"></div>
<canvas id="c"></canvas>
<script>
const DATA = __DATA__;
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
function resize(){canvas.width=innerWidth;canvas.height=innerHeight;}
resize(); addEventListener('resize', resize);

const COLORS = {file:'#5b7fff', class:'#ff9d5c', function:'#5cd6a9', method:'#5cd6a9',
  doc:'#c9a2ff', external:'#555b6e', external_symbol:'#3a3f4d'};
function colorFor(n){ if(n.community) return n.community.color; return COLORS[n.type]||'#8892a6'; }

const nodes = DATA.nodes.map(n => ({...n, x: (Math.random()-0.5)*800, y:(Math.random()-0.5)*800, vx:0, vy:0}));
const byId = Object.fromEntries(nodes.map(n=>[n.id,n]));
const edges = DATA.edges.filter(e=>byId[e.source]&&byId[e.target]);

let view = {x:0,y:0,scale:0.6};
let dragging=null, panStart=null, focus=null, hover=null;

function tick(){
  const rep = 1800;
  for(let i=0;i<nodes.length;i++){
    for(let j=i+1;j<nodes.length;j++){
      const a=nodes[i], b=nodes[j];
      let dx=a.x-b.x, dy=a.y-b.y; let d2=dx*dx+dy*dy+0.01;
      if(d2>90000) continue;
      const f = rep/d2;
      const d = Math.sqrt(d2);
      dx/=d; dy/=d;
      a.vx+=dx*f; a.vy+=dy*f; b.vx-=dx*f; b.vy-=dy*f;
    }
  }
  for(const e of edges){
    const a=byId[e.source], b=byId[e.target];
    let dx=b.x-a.x, dy=b.y-a.y; const d=Math.sqrt(dx*dx+dy*dy)+0.01;
    const target = e.confidence==='EXTRACTED'?70:110;
    const f=(d-target)*0.004;
    dx/=d; dy/=d;
    a.vx+=dx*f; a.vy+=dy*f; b.vx-=dx*f; b.vy-=dy*f;
  }
  for(const n of nodes){
    n.vx += -n.x*0.0012; n.vy += -n.y*0.0012;
    n.vx*=0.82; n.vy*=0.82;
    if(n!==dragging){ n.x+=n.vx; n.y+=n.vy; }
  }
}

function draw(){
  ctx.save();
  ctx.setTransform(1,0,0,1,0,0);
  ctx.fillStyle='#0b0e14'; ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.translate(canvas.width/2+view.x, canvas.height/2+view.y);
  ctx.scale(view.scale, view.scale);

  const neighborSet = focus ? new Set([focus.id, ...edges.filter(e=>e.source===focus.id||e.target===focus.id)
    .map(e=>e.source===focus.id?e.target:e.source)]) : null;

  for(const e of edges){
    const a=byId[e.source], b=byId[e.target];
    const dim = neighborSet && !(neighborSet.has(a.id)&&neighborSet.has(b.id));
    ctx.strokeStyle = e.confidence==='EXTRACTED' ? (dim?'#2a3142':'#5b7fff88')
                     : e.confidence==='AMBIGUOUS' ? (dim?'#2a2020':'#ff5c5c55')
                     : (dim?'#282a20':'#c9c05c55');
    ctx.lineWidth = e.confidence==='EXTRACTED'?1.1:0.7;
    ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
  }
  for(const n of nodes){
    const r = 3 + Math.sqrt(n.degree||1)*1.6;
    const dim = neighborSet && !neighborSet.has(n.id);
    ctx.globalAlpha = dim?0.15:1;
    ctx.beginPath(); ctx.arc(n.x,n.y,r,0,7); ctx.fillStyle=colorFor(n); ctx.fill();
    if(view.scale>0.9 && !dim){
      ctx.fillStyle='#c8cede'; ctx.font='11px sans-serif';
      ctx.fillText(n.label, n.x+r+3, n.y+3);
    }
    ctx.globalAlpha=1;
  }
  ctx.restore();
}

function loop(){ tick(); draw(); requestAnimationFrame(loop); }
loop();

function toWorld(mx,my){
  return {x:(mx-canvas.width/2-view.x)/view.scale, y:(my-canvas.height/2-view.y)/view.scale};
}
function nodeAt(mx,my){
  const w = toWorld(mx,my);
  let best=null, bd=1e9;
  for(const n of nodes){
    const r = 3 + Math.sqrt(n.degree||1)*1.6 + 3;
    const d=(n.x-w.x)**2+(n.y-w.y)**2;
    if(d<r*r && d<bd){bd=d; best=n;}
  }
  return best;
}
canvas.addEventListener('mousedown', e=>{
  const n = nodeAt(e.offsetX, e.offsetY);
  if(n){ dragging=n; } else { panStart={x:e.clientX-view.x, y:e.clientY-view.y}; }
});
addEventListener('mousemove', e=>{
  if(dragging){
    const w = toWorld(e.offsetX, e.offsetY);
    dragging.x=w.x; dragging.y=w.y; dragging.vx=0; dragging.vy=0;
  } else if(panStart){
    view.x = e.clientX-panStart.x; view.y = e.clientY-panStart.y;
  } else {
    const n = nodeAt(e.offsetX, e.offsetY);
    hover = n;
    const tip = document.getElementById('tip');
    if(n){
      tip.style.display='block'; tip.style.left=(e.clientX+14)+'px'; tip.style.top=(e.clientY+10)+'px';
      tip.innerHTML = '<b>'+n.label+'</b><br>'+n.type+(n.path?' · '+n.path:'')+(n.line?':'+n.line:'')+
        '<br>degree: '+(n.degree||0);
    } else { tip.style.display='none'; }
  }
});
addEventListener('mouseup', ()=>{ dragging=null; panStart=null; });
canvas.addEventListener('click', e=>{
  if(panStart) return;
  const n = nodeAt(e.offsetX, e.offsetY);
  focus = (focus && n && focus.id===n.id) ? null : n;
});
canvas.addEventListener('wheel', e=>{
  e.preventDefault();
  const factor = e.deltaY<0?1.1:0.9;
  view.scale = Math.max(0.05, Math.min(6, view.scale*factor));
}, {passive:false});
</script>
</body></html>"""


def render_html(nodes, edges, degree, communities, out_path):
    community_colors = {}
    palette = ['#5b7fff', '#ff9d5c', '#5cd6a9', '#c9a2ff', '#ff5c8a', '#c9c05c',
               '#5cc9ff', '#ff8c5c', '#8aff5c', '#ff5c5c']
    for i, (label, members) in enumerate(sorted(communities.items(), key=lambda kv: -len(kv[1]))):
        color = palette[i % len(palette)]
        for m in members:
            community_colors[m] = {"label": str(label), "color": color}

    slim_nodes = []
    for nid, n in nodes.items():
        d = degree.get(nid, 0)
        entry = {"id": nid, "type": n.get("type", "file"), "label": n.get("label", nid),
                  "path": n.get("path"), "line": n.get("line"), "degree": d}
        if nid in community_colors:
            entry["community"] = community_colors[nid]
        slim_nodes.append(entry)
    slim_edges = [{"source": e["source"], "target": e["target"], "relation": e["relation"],
                    "confidence": e.get("confidence")} for e in edges]

    data = {"nodes": slim_nodes, "edges": slim_edges}
    legend = "".join(
        f'<div><span class="sw" style="background:{c}"></span>{t}</div>'
        for t, c in [("file", "#5b7fff"), ("class", "#ff9d5c"), ("function/method", "#5cd6a9"),
                     ("doc", "#c9a2ff"), ("external", "#555b6e")]
    )
    # A docstring/label containing a literal "</script>" would otherwise
    # close the embedding <script> tag early and corrupt the page.
    safe_json = json.dumps(data).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DATA__", safe_json).replace("__LEGEND__", legend)
    with open(out_path, "w") as f:
        f.write(html)


def render_report(nodes, edges, ambiguous, degree, communities, errors, out_path, meta):
    lines = []
    lines.append("# GRAPH_REPORT.md\n")
    lines.append(f"Generated: {meta['generated_at']}  \n")
    lines.append(f"Repo root: `{meta['root']}`\n")

    lang_counts = Counter(n.get("language") for n in nodes.values() if n.get("language"))
    type_counts = Counter(n["type"] for n in nodes.values())
    conf_counts = Counter(e.get("confidence") for e in edges)

    lines.append("\n## Overview\n")
    lines.append(f"- {len(nodes)} nodes, {len(edges)} resolved edges, {len(ambiguous)} ambiguous edges kept for review\n")
    lines.append("- Nodes by type: " + ", ".join(f"{t}={c}" for t, c in type_counts.most_common()) + "\n")
    if lang_counts:
        lines.append("- Files by language: " + ", ".join(f"{l}={c}" for l, c in lang_counts.most_common()) + "\n")
    lines.append("- Edges by confidence: " + ", ".join(f"{k}={v}" for k, v in conf_counts.most_common()) + "\n")

    lines.append("\n## God nodes (highest connectivity)\n")
    lines.append("These are the hubs — central services, shared utilities, or places where a lot of the "
                  "repo's structure actually flows through. Worth extra care when changing.\n\n")
    top = degree.most_common(15)
    for nid, d in top:
        n = nodes.get(nid, {})
        lines.append(f"- **{n.get('label', nid)}** ({n.get('type', '?')}"
                      f"{', ' + n['path'] if n.get('path') else ''}) — degree {d}\n")

    lines.append("\n## Communities (structural clusters)\n")
    lines.append("Found by label propagation over non-ambiguous edges — a lightweight stand-in for "
                  "Leiden clustering, grouping nodes that are more connected to each other than to the "
                  "rest of the graph.\n\n")
    sized = [(lab, members) for lab, members in communities.items() if len(members) >= 3]
    sized.sort(key=lambda kv: -len(kv[1]))
    for lab, members in sized[:20]:
        sample = ", ".join(nodes.get(m, {}).get("label", m) for m in members[:8])
        more = f" (+{len(members) - 8} more)" if len(members) > 8 else ""
        lines.append(f"- **{len(members)} nodes**: {sample}{more}\n")

    if ambiguous:
        lines.append("\n## Ambiguous relationships (kept, not dropped — worth a look)\n")
        for e in ambiguous[:40]:
            src = nodes.get(e["source"], {}).get("label", e["source"])
            src_path = nodes.get(e["source"], {}).get("path", "")
            loc = f"{src_path}:{e['line']}" if src_path and e.get("line") else (src_path or "")
            lines.append(f"- `{src}` --{e['relation']}--> `{e.get('raw_target', e['target'])}` "
                          f"({loc}) — {e.get('reason', 'unresolved')}\n")
        if len(ambiguous) > 40:
            lines.append(f"- ...and {len(ambiguous) - 40} more (see graph.json for the full list)\n")

    if errors:
        lines.append("\n## Extraction errors (files skipped or partially parsed)\n")
        for err in errors[:30]:
            lines.append(f"- {err}\n")

    lines.append("\n## Questions this graph can answer well\n")
    if top:
        g1 = nodes.get(top[0][0], {}).get("label", "the top god node")
        lines.append(f"- What depends on `{g1}`, and what would break if it changed?\n")
    if sized:
        lines.append(f"- What's inside the largest structural cluster, and does it map to one subsystem?\n")
    lines.append("- What's the path between two specific files or symbols? (`query.py path A B`)\n")
    lines.append("- What does a specific symbol connect to? (`query.py explain NAME`)\n")

    with open(out_path, "w") as f:
        f.writelines(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--out-dir", default=".graph")
    ap.add_argument("--update", action="store_true",
                     help="Incrementally update an existing graph.json instead of rebuilding from scratch")
    ap.add_argument("--semantic", default=None,
                     help="Path to a JSON file of Claude-authored semantic fragments to merge in")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    out_dir = os.path.join(root, args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    graph_json_path = os.path.join(out_dir, "graph.json")

    changed_files = None
    existing = None
    if args.update and os.path.isfile(graph_json_path):
        with open(graph_json_path) as f:
            existing = json.load(f)
        old_hashes = existing.get("file_hashes", {})
        current = run_extract(root, out_dir)  # cheap: just walks + hashes to compare
        cur_hash_by_file = {f["file_id"]: f.get("hash") for f in current}
        changed_files = [fid for fid, h in cur_hash_by_file.items() if old_hashes.get(fid) != h]
        removed_files = [fid for fid in old_hashes if fid not in cur_hash_by_file]
        fragments = [f for f in current if f["file_id"] in changed_files] if changed_files else []
        print(f"Incremental update: {len(changed_files)} changed, {len(removed_files)} removed, "
              f"{len(cur_hash_by_file) - len(changed_files)} unchanged", file=sys.stderr)
    else:
        fragments = run_extract(root, out_dir)
        removed_files = []

    semantic_fragments = None
    if args.semantic and os.path.isfile(args.semantic):
        with open(args.semantic) as f:
            semantic_fragments = json.load(f)
            if isinstance(semantic_fragments, dict):
                semantic_fragments = [semantic_fragments]

    nodes, raw_edges, semantic_edges, errors, file_hashes = merge_nodes(fragments, semantic_fragments)

    if existing:
        # Carry forward nodes/edges from unchanged files.
        changed_set = set(changed_files or [])
        removed_set = set(removed_files)
        for nid, n in existing.get("nodes", {}).items():
            fpath = n.get("path", nid)
            if fpath not in changed_set and fpath not in removed_set:
                nodes.setdefault(nid, n)
        kept_edges = [e for e in existing.get("edges", [])
                      if e["source"].split("::")[0] not in changed_set
                      and e["source"].split("::")[0] not in removed_set]
        raw_edges = kept_edges + raw_edges
        file_hashes = {**existing.get("file_hashes", {}), **file_hashes}
        for fid in removed_set:
            file_hashes.pop(fid, None)

    all_file_ids = {nid for nid, n in nodes.items() if n["type"] == "file"}
    symbol_index = build_symbol_index(nodes)
    resolved, ambiguous = assign_confidence_and_resolve(raw_edges, nodes, symbol_index, all_file_ids)

    for e in semantic_edges:
        e.setdefault("confidence", "INFERRED")
        nodes.setdefault(e["source"], {"id": e["source"], "type": "concept", "label": e["source"]})
        nodes.setdefault(e["target"], {"id": e["target"], "type": "concept", "label": e["target"]})
    all_edges = resolved + semantic_edges

    degree = compute_degree(nodes, all_edges)
    communities = label_propagation(list(nodes.keys()), all_edges)

    meta = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "root": root}
    graph = {
        "meta": meta,
        "nodes": nodes,
        "edges": all_edges,
        "ambiguous_edges": ambiguous,
        "file_hashes": file_hashes,
        "degree": dict(degree),
    }
    with open(graph_json_path, "w") as f:
        json.dump(graph, f, indent=1)

    render_report(nodes, all_edges, ambiguous, degree, communities, errors,
                  os.path.join(out_dir, "GRAPH_REPORT.md"), meta)
    render_html(nodes, all_edges, degree, communities, os.path.join(out_dir, "graph.html"))

    print(f"Wrote {graph_json_path}")
    print(f"  {len(nodes)} nodes, {len(all_edges)} edges ({len(ambiguous)} ambiguous), "
          f"{len(communities)} raw label groups")


if __name__ == "__main__":
    main()
