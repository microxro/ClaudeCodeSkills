#!/usr/bin/env python3
"""
SessionStart hook for the /graph skill.

Runs once per session start. For a git repo large enough to be worth
graphing: makes sure a knowledge graph exists and is reasonably fresh
(kicking off a background build/update if not), and injects a short context
note telling the session to query it before broadly grepping/reading for
codebase-context-gathering, architecture, or code-review tasks.

No-ops fast and silently — no output, no delay — for: not a git repo, or a
repo with too few source files to be worth it (matches the /graph skill's
own "when to use" guidance, so this hook doesn't contradict what the skill
itself says is and isn't worth building a graph for).

Never blocks session startup: the build/update itself always runs detached
in the background, never awaited here.
"""
import json
import os
import subprocess
import sys

SOURCE_EXTS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rb",
    ".java", ".rs", ".php", ".c", ".h", ".cpp", ".hpp", ".cs", ".kt",
    ".swift", ".lua",
}
MIN_FILES = 15
SKILL_DIR = os.path.expanduser("~/.claude/skills/graph")
BUILD_SCRIPT = os.path.join(SKILL_DIR, "scripts", "build_graph.py")
QUERY_SCRIPT = os.path.join(SKILL_DIR, "scripts", "query.py")


def emit(context):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main():
    sys.stdin.read()  # drain, hook input JSON isn't needed here

    cwd = os.getcwd()
    check = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=cwd)
    if check.returncode != 0:
        return  # not a git repo — silent, fast no-op

    root_res = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if root_res.returncode != 0:
        return
    repo_root = root_res.stdout.strip()

    ls = run(["git", "ls-files"], cwd=repo_root)
    if ls.returncode != 0:
        return
    file_count = sum(1 for f in ls.stdout.splitlines()
                      if os.path.splitext(f)[1] in SOURCE_EXTS)
    if file_count < MIN_FILES:
        return  # too small to be worth graphing — matches the skill's own guidance

    if not os.path.isfile(BUILD_SCRIPT):
        return  # skill not installed on this machine

    graph_dir = os.path.join(repo_root, ".graph")
    graph_json = os.path.join(graph_dir, "graph.json")
    os.makedirs(graph_dir, exist_ok=True)

    graph_exists = os.path.isfile(graph_json)
    needs_build = not graph_exists
    if graph_exists:
        commit_ts_res = run(["git", "log", "-1", "--format=%ct"], cwd=repo_root)
        try:
            last_commit_ts = int(commit_ts_res.stdout.strip())
        except (ValueError, AttributeError):
            last_commit_ts = 0
        graph_ts = os.path.getmtime(graph_json)
        needs_build = last_commit_ts > graph_ts

    if needs_build:
        log_path = os.path.join(graph_dir, "build.log")
        cmd = [sys.executable, BUILD_SCRIPT, repo_root, "--out-dir", ".graph"]
        if graph_exists:
            cmd.append("--update")
        with open(log_path, "a") as log:
            subprocess.Popen(
                cmd, cwd=repo_root, stdout=log, stderr=log,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )

    if graph_exists:
        refreshing = " (a refresh just kicked off in the background since recent commits look newer than it)" if needs_build else ""
        emit(
            f"This repo has a knowledge graph at .graph/graph.json, built by the /graph "
            f"skill{refreshing}. For codebase-context-gathering, architecture questions, or "
            f"code review, query it first — `python3 {QUERY_SCRIPT} {repo_root} stats` (or "
            f"search/neighbors/explain/path) — before broadly grepping or reading files, to "
            f"save tokens versus rediscovering the repo's structure from scratch."
        )
    else:
        emit(
            f"No knowledge graph existed yet for this repo, so the /graph skill just kicked "
            f"one off in the background (.graph/graph.json, log at .graph/build.log). For a "
            f"codebase-context-gathering, architecture, or code-review task, check back "
            f"shortly with `python3 {QUERY_SCRIPT} {repo_root} stats` before falling back to "
            f"broad grep/read."
        )


if __name__ == "__main__":
    main()
