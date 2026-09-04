#!/usr/bin/env python3
"""
extract.py — deterministic-where-possible structural extraction.

Walks a repo (or a given file list) and emits graph fragments: nodes and
edges, each edge tagged with how it was found. Confidence is assigned later
in build_graph.py, once cross-file symbol resolution has happened — this
script's job is just to record raw, honest facts about what it saw.

Python files get real AST parsing (the ast module is stdlib, always
available, and gives exact facts). Every other language gets regex-based
extraction, which is a heuristic, not a parse — this script tags every edge
with "method": "ast" or "method": "regex" so nothing downstream pretends a
regex guess is as solid as a real parse.

Usage:
    python3 extract.py <repo_root> [--files a.py b.js ...] > fragments.json
    python3 extract.py <repo_root> --out fragments.json
"""
import argparse
import ast
import hashlib
import json
import os
import re
import sys

DEFAULT_IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", ".graph", "target", ".pytest_cache", ".mypy_cache", "vendor",
    "coverage", ".turbo", ".cache",
}

CODE_EXT_LANGUAGE = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".rb": "ruby", ".java": "java", ".rs": "rust",
    ".php": "php", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".kt": "kotlin", ".swift": "swift", ".lua": "lua",
    ".sh": "shell", ".bash": "shell",
}
DOC_EXT_TYPE = {
    ".md": "doc", ".mdx": "doc", ".txt": "doc", ".rst": "doc",
}

# Calls to these never resolve to anything in a user's repo, so recording
# them just produces "ambiguous: no matching definition" noise that buries
# the ambiguous edges actually worth a human's attention. Skipped at the
# source rather than filtered later so fragments/graph.json stay clean too.
PY_BUILTINS = frozenset("""
    abs aiter all anext any ascii bin bool breakpoint bytearray bytes
    callable chr classmethod compile complex delattr dict dir divmod
    enumerate eval exec filter float format frozenset getattr globals
    hasattr hash help hex id input int isinstance issubclass iter len
    list locals map max memoryview min next object oct open ord pow
    print property range repr reversed round set setattr slice sorted
    staticmethod str sum super tuple type vars zip
    self cls
    Exception ValueError TypeError KeyError IndexError AttributeError
    RuntimeError StopIteration StopAsyncIteration OSError IOError
    FileNotFoundError NotImplementedError PermissionError TimeoutError
    ImportError ModuleNotFoundError ZeroDivisionError AssertionError
    ConnectionError NameError UnicodeDecodeError UnicodeEncodeError
""".split())

JS_GLOBALS = frozenset("""
    Object Array String Number Boolean Symbol BigInt Date RegExp Error
    TypeError RangeError SyntaxError Map Set WeakMap WeakSet Promise
    Proxy Reflect JSON Math console parseInt parseFloat isNaN isFinite
    encodeURIComponent decodeURIComponent encodeURI decodeURI
    setTimeout setInterval clearTimeout clearInterval fetch structuredClone
    require module exports process globalThis window document navigator
    localStorage sessionStorage self Function Array_isArray btoa atob
""".split())


def rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def file_hash(path):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            h.update(f.read())
    except OSError:
        return None
    return h.hexdigest()


def load_ignore_patterns(root):
    patterns = []
    for name in (".gitignore", ".graphignore"):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            with open(p, "r", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
    return patterns


def is_ignored(relpath, patterns):
    # Lightweight, not a full .gitignore implementation: matches a pattern
    # against the whole relative path or its basename, handling a trailing
    # slash (directory-only) and a leading slash (root-anchored) simply.
    import fnmatch
    base = os.path.basename(relpath)
    for pat in patterns:
        p = pat.rstrip("/")
        anchored = p.startswith("/")
        p = p.lstrip("/")
        if fnmatch.fnmatch(relpath, p) or fnmatch.fnmatch(base, p):
            return True
        if not anchored and fnmatch.fnmatch(relpath, "*/" + p):
            return True
    return False


def discover_files(root, explicit_files=None):
    if explicit_files:
        return [os.path.join(root, f) if not os.path.isabs(f) else f for f in explicit_files]
    patterns = load_ignore_patterns(root)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".")
                       or d in (".graphignore",)]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            r = rel(full, root)
            if is_ignored(r, patterns):
                continue
            ext = os.path.splitext(fn)[1]
            if ext in CODE_EXT_LANGUAGE or ext in DOC_EXT_TYPE:
                out.append(full)
    return out


def node(node_id, ntype, label, **meta):
    d = {"id": node_id, "type": ntype, "label": label}
    d.update({k: v for k, v in meta.items() if v is not None})
    return d


def edge(source, target, relation, method, **meta):
    d = {"source": source, "target": target, "relation": relation, "method": method}
    d.update({k: v for k, v in meta.items() if v is not None})
    return d


# ---------------------------------------------------------------- python --

class PyVisitor(ast.NodeVisitor):
    def __init__(self, file_id, language):
        self.file_id = file_id
        self.language = language
        self.nodes = []
        self.edges = []
        self._scope_stack = [file_id]
        self._scope_kind_stack = ["file"]

    def _qualify(self, name):
        return self._scope_stack[-1] + "." + name if len(self._scope_stack) > 1 else self.file_id + "::" + name

    def visit_Import(self, n):
        for alias in n.names:
            self.edges.append(edge(self.file_id, alias.name, "imports", "ast",
                                    kind="import", line=n.lineno, raw_target=alias.name))
        self.generic_visit(n)

    def visit_ImportFrom(self, n):
        mod = ("." * (n.level or 0)) + (n.module or "")
        for alias in n.names:
            self.edges.append(edge(self.file_id, mod, "imports", "ast",
                                    kind="import_from", line=n.lineno,
                                    raw_target=mod, imported_name=alias.name))
        self.generic_visit(n)

    def visit_ClassDef(self, n):
        cid = self._qualify(n.name) if self._scope_stack[-1] != self.file_id else self.file_id + "::" + n.name
        self.nodes.append(node(cid, "class", n.name, path=self.file_id, line=n.lineno,
                                language=self.language, docstring=ast.get_docstring(n)))
        for base in n.bases:
            bname = self._base_name(base)
            if bname:
                self.edges.append(edge(cid, bname, "inherits", "ast", line=n.lineno, raw_target=bname))
        self._scope_stack.append(cid)
        self._scope_kind_stack.append("class")
        self.generic_visit(n)
        self._scope_kind_stack.pop()
        self._scope_stack.pop()

    def _base_name(self, node_expr):
        if isinstance(node_expr, ast.Name):
            return node_expr.id
        if isinstance(node_expr, ast.Attribute):
            return node_expr.attr
        return None

    def _def(self, n, kind):
        parent = self._scope_stack[-1]
        parent_kind = self._scope_kind_stack[-1]
        is_method = parent_kind == "class"
        # A nested/closure function still gets its own real node (a call to
        # it can then actually resolve) — it's just labeled "function", not
        # "method", since it isn't attached to a class.
        fid = parent + "." + n.name if len(self._scope_stack) > 1 else self.file_id + "::" + n.name
        self.nodes.append(node(fid, "method" if is_method else "function", n.name,
                                path=self.file_id, line=n.lineno, language=self.language,
                                docstring=ast.get_docstring(n)))
        self.edges.append(edge(parent, fid, "defines", "ast", line=n.lineno))
        self._scope_stack.append(fid)
        self._scope_kind_stack.append("function")
        for call_name, line in self._find_calls(n):
            if call_name in PY_BUILTINS:
                continue
            self.edges.append(edge(fid, call_name, "calls", "ast", line=line, raw_target=call_name))
        self.generic_visit(n)  # recurse so nested def/class statements get their own node too
        self._scope_kind_stack.pop()
        self._scope_stack.pop()

    def visit_FunctionDef(self, n):
        self._def(n, "function")

    def visit_AsyncFunctionDef(self, n):
        self._def(n, "function")

    def _find_calls(self, funcnode):
        # Only bare-name calls (foo()) and self.foo() calls get recorded.
        # x.foo() / module.foo() for an arbitrary receiver can't be resolved
        # by name alone without real type inference — attempting it just
        # produces a flood of "no matching definition" noise for ordinary
        # stdlib/third-party method calls (list.append, path.write_text,
        # str.startswith...). self.foo() is the one attribute-call shape
        # worth keeping: within a class, it's almost always a same-class
        # method, so name resolution has real signal there.
        #
        # Stops at a nested FunctionDef/AsyncFunctionDef/ClassDef boundary —
        # those get walked (and their own calls found) separately, via the
        # visitor's own recursion, so a nested function's calls are
        # attributed to it, not smeared onto the outer function.
        out = []

        def walk(n):
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if isinstance(child, ast.Call):
                    f = child.func
                    if isinstance(f, ast.Name):
                        out.append((f.id, child.lineno))
                    elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self":
                        out.append((f.attr, child.lineno))
                walk(child)

        walk(funcnode)
        return out


def extract_python(path, file_id):
    nodes = [node(file_id, "file", os.path.basename(file_id), path=file_id, language="python")]
    edges = []
    errors = []
    try:
        with open(path, "r", errors="ignore") as f:
            src = f.read()
        tree = ast.parse(src, filename=file_id)
    except SyntaxError as e:
        errors.append(f"{file_id}: syntax error: {e}")
        return {"nodes": nodes, "edges": edges, "errors": errors}
    v = PyVisitor(file_id, "python")
    v.visit(tree)
    nodes.extend(v.nodes)
    edges.extend(v.edges)
    return {"nodes": nodes, "edges": edges, "errors": errors}


# --------------------------------------------------------- regex (JS/TS) --

JS_IMPORT_RE = re.compile(
    r"""^\s*import\s+(?:[\w${}\s,*]+\s+from\s+)?['"]([^'"]+)['"]|"""
    r"""^\s*(?:const|let|var)\s+[\w{}\s,:]+=\s*require\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)
JS_EXPORT_FUNC_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s+(\w+)", re.MULTILINE)
JS_FUNC_RE = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s*\*?\s+(\w+)", re.MULTILINE)
JS_CLASS_RE = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?", re.MULTILINE)
JS_CONST_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(?[\w\s,{}]*\)?\s*=>", re.MULTILINE)
JS_CALL_RE = re.compile(r"(?<![\w.])([A-Za-z_$][\w$]*)\s*\(")

JS_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "function", "return", "typeof",
    "new", "await", "async", "class", "constructor", "super", "yield",
    "console", "require", "import", "export", "in", "of", "instanceof",
    "delete", "void", "throw", "try", "else", "do", "with",
}


def extract_js_like(path, file_id, language):
    nodes = [node(file_id, "file", os.path.basename(file_id), path=file_id, language=language)]
    edges = []
    try:
        with open(path, "r", errors="ignore") as f:
            src = f.read()
    except OSError as e:
        return {"nodes": nodes, "edges": edges, "errors": [f"{file_id}: {e}"]}

    for m in JS_IMPORT_RE.finditer(src):
        target = m.group(1) or m.group(2)
        if target:
            line = src.count("\n", 0, m.start()) + 1
            edges.append(edge(file_id, target, "imports", "regex", line=line, raw_target=target))

    top_level_funcs = []
    for pat, kind in ((JS_FUNC_RE, "function"), (JS_CONST_ARROW_RE, "function")):
        for m in pat.finditer(src):
            name = m.group(1)
            line = src.count("\n", 0, m.start()) + 1
            fid = file_id + "::" + name
            if fid not in [n["id"] for n in nodes]:
                nodes.append(node(fid, "function", name, path=file_id, line=line, language=language))
                edges.append(edge(file_id, fid, "defines", "regex", line=line))
            top_level_funcs.append((name, fid))

    for m in JS_CLASS_RE.finditer(src):
        name, base = m.group(1), m.group(2)
        line = src.count("\n", 0, m.start()) + 1
        cid = file_id + "::" + name
        nodes.append(node(cid, "class", name, path=file_id, line=line, language=language))
        edges.append(edge(file_id, cid, "defines", "regex", line=line))
        if base:
            edges.append(edge(cid, base, "inherits", "regex", line=line, raw_target=base))

    # Calls: attributed to the file as a whole (regex extraction can't reliably
    # scope a call to the enclosing function the way a real AST walk can), so
    # these are file-level "uses" facts rather than function-level "calls".
    seen_calls = set()
    for m in JS_CALL_RE.finditer(src):
        name = m.group(1)
        if name in JS_KEYWORDS or name in JS_GLOBALS or len(name) < 2:
            continue
        if name in seen_calls:
            continue
        seen_calls.add(name)
        line = src.count("\n", 0, m.start()) + 1
        edges.append(edge(file_id, name, "uses", "regex", line=line, raw_target=name))

    return {"nodes": nodes, "edges": edges, "errors": []}


def extract_doc(path, file_id, doctype):
    return {"nodes": [node(file_id, doctype, os.path.basename(file_id), path=file_id)],
            "edges": [], "errors": []}


def extract_generic_code(path, file_id, language):
    # No language-specific patterns yet: register the file node so it's part
    # of the graph and can be linked to from docs, but don't guess at
    # definitions/calls with patterns tuned for a different language.
    return {"nodes": [node(file_id, "file", os.path.basename(file_id), path=file_id, language=language)],
            "edges": [], "errors": []}


def extract_file(path, root):
    file_id = rel(path, root)
    ext = os.path.splitext(path)[1]
    if ext == ".py":
        result = extract_python(path, file_id)
    elif ext in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
        result = extract_js_like(path, file_id, CODE_EXT_LANGUAGE[ext])
    elif ext in DOC_EXT_TYPE:
        result = extract_doc(path, file_id, DOC_EXT_TYPE[ext])
    elif ext in CODE_EXT_LANGUAGE:
        result = extract_generic_code(path, file_id, CODE_EXT_LANGUAGE[ext])
    else:
        result = {"nodes": [], "edges": [], "errors": []}
    result["hash"] = file_hash(path)
    result["file_id"] = file_id
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--files", nargs="*", default=None,
                     help="Only extract these repo-relative files (for incremental updates)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    files = discover_files(root, args.files)

    fragments = []
    for f in files:
        if not os.path.isfile(f):
            continue
        fragments.append(extract_file(f, root))

    out = {"fragments": fragments}
    text = json.dumps(out, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
