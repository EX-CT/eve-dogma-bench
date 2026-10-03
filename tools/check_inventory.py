#!/usr/bin/env python3
"""docs/20 §5.1 inventory -> tests gate.

Reads the docs/19 inventory YAML (eve-fit-docs docs/19-pyfa-feature-inventory.yaml), the per-item test lists
(an item's own `tests:` field and/or a mapping file, default inventory/tests.yaml next to this tool's repo) and the
suite registry (inventory/suites.yaml), and fails (exit 1) when:
  1. an item is `have` in a checked column but has no test of a suite belonging to that column;
  2. a cited test does not exist (a file case missing, a Rust test fn not found, an unknown test id);
  3. with --release: an item is `missing` or `partial` in a checked column without `deferred: <ruling>`
     (on the item, or as `deferred:` in the mapping file entry);
  4. an item is `have` in a checked column but its only tests there are `strength: weak` ("weak-only", reported
     separately and not counted as "with tests").
References whose suite needs a --root that was not given are "unverified": reported, and fatal only with --strict.

  python3 tools/check_inventory.py --inventory ../eve-fit-docs/docs/19-pyfa-feature-inventory.yaml \
      [--tests inventory/tests.yaml] [--columns f] [--root unit=../eve-dogma] [--root mcp=../eve-fit-mcp] \
      [--release] [--strict] [--json out.json]

Mapping file format (inventory/tests.yaml):
  items:
    ENG-CORE-002: [bench:esf_stacking_per*, bench:e_fz_cloak_wcs_penalty_group_ninazu]
    ENG-OFF-006: {tests: [ext:mining_*], deferred: "user 2026-10-03: P0-3"}
    ENG-NAV-001: [bench:esf_mwd*, {ref: "mcp:mcp.integration.what-if", strength: partial, why: velocity only}]
    FMT-ESI-001: {tests: [...], unsupported: [mcp], why: "..."}
A ref is "suite:name" or {ref: "suite:name", strength: weak|partial, why: "..."}; no strength = full. partial counts
as covered (and is counted as "partial only" when an item has nothing stronger); weak does not.
`unsupported: [column]` records that the column does not support the item (a mapping-file ruling; a conflict with a
docs/19 `have` is a problem). An item's `tests:` in docs/19 may be a list of refs or a {column: [refs]} mapping; both
sources are merged.

Suite kinds (inventory/suites.yaml): files, jsonl, rust-test, id (stable test ids parsed from the suite's sources:
`id_prefix`, files matching `glob`; an id is `<prefix><slug>` directly followed by ':' at the start of a string
literal; JS template parts `${v}` are expanded from `for (const v of NAME)` over a literal `const NAME = [...]`;
optional `ids_json` is cross-checked, differences are warnings), and string (deprecated: substring of a test title).
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def load_yaml(p):
    with open(p) as f:
        return yaml.safe_load(f)


def parse_ref(ref):
    ref = ref.strip()
    m = re.match(r'^([A-Za-z0-9_.-]+):(.*)$', ref)
    if not m:
        return None, ref
    name = m.group(2).strip()
    if len(name) >= 2 and name[0] == name[-1] and name[0] in "\"'":
        name = name[1:-1]
    return m.group(1), name


class Resolver:
    def __init__(self, suites, roots, bench_repo):
        self.suites, self.roots, self.repo = suites, roots, bench_repo
        self.cache = {}
        self.warnings = []

    def _git_files(self, ref, d):
        try:
            out = subprocess.run(["git", "-C", self.repo, "ls-tree", "--name-only", ref, d.rstrip("/") + "/"],
                                 capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError:
            br = ref.split("/", 1)[1] if ref.startswith("origin/") else ref
            subprocess.run(["git", "-C", self.repo, "fetch", "-q", "origin", f"{br}:refs/remotes/origin/{br}"],
                           capture_output=True)
            r = subprocess.run(["git", "-C", self.repo, "ls-tree", "--name-only", ref, d.rstrip("/") + "/"],
                               capture_output=True, text=True)
            if r.returncode:
                return None
            out = r.stdout
        return [os.path.basename(x) for x in out.split()]

    def names(self, suite):
        if suite in self.cache:
            return self.cache[suite]
        s = self.suites[suite]
        files = None
        if suite in self.roots:
            p = os.path.join(self.roots[suite], s["dir"])
            files = os.listdir(p) if os.path.isdir(p) else None
        elif s.get("git_ref"):
            files = self._git_files(s["git_ref"], s["dir"])
        else:
            p = os.path.join(self.repo, s["dir"])
            files = os.listdir(p) if os.path.isdir(p) else []
        if files is not None:
            ext = s.get("ext", "")
            files = {f[:len(f) - len(ext)] if ext and f.endswith(ext) else f for f in files if not ext or f.endswith(ext)}
        self.cache[suite] = files
        return files

    def jsonl_keys(self, suite):
        if suite in self.cache:
            return self.cache[suite]
        s = self.suites[suite]
        txt = None
        if suite in self.roots:
            p = os.path.join(self.roots[suite], s["file"])
            txt = open(p).read() if os.path.exists(p) else None
        elif s.get("git_ref"):
            self._git_files(s["git_ref"], os.path.dirname(s["file"]))  # fetches the ref when absent
            r = subprocess.run(["git", "-C", self.repo, "show", f"{s['git_ref']}:{s['file']}"], capture_output=True, text=True)
            txt = r.stdout if r.returncode == 0 else None
        else:
            p = os.path.join(self.repo, s["file"])
            txt = open(p).read() if os.path.exists(p) else ""
        keys = None
        if txt is not None:
            keys = set()
            for line in txt.splitlines():
                if line.strip():
                    v = json.loads(line).get(s["key"])
                    if v is not None:
                        keys.add(str(v))
        self.cache[suite] = keys
        return keys

    def _walk(self, root, pat):
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in (".git", "node_modules", "target", "dist")]
            for f in fn:
                if fnmatch.fnmatch(f, pat):
                    yield os.path.join(dp, f)

    def ids(self, suite):
        key = ("ids", suite)
        if key in self.cache:
            return self.cache[key]
        s = self.suites[suite]
        root = self.roots.get(suite)
        if not root:
            self.cache[key] = None
            return None
        rx = re.compile("[\"'`](" + re.escape(s["id_prefix"]) + r")((?:[a-z0-9.-]|\$\{\w+\})+):")
        ids = set()
        for p in self._walk(root, s.get("glob", "*")):
            txt = open(p, errors="ignore").read()
            for m in rx.finditer(txt):
                vals = [m.group(2)]
                for v in sorted(set(re.findall(r"\$\{(\w+)\}", m.group(2)))):
                    lm = re.search(r"for\s*\(\s*const\s+" + v + r"\s+of\s+(\w+)\s*\)", txt)
                    am = lm and re.search(r"const\s+" + lm.group(1) + r"\s*=\s*\[(.*?)\];", txt, re.S)
                    if not am:
                        raise SystemExit(f"{p}: cannot expand ${{{v}}} in id {m.group(1)}{m.group(2)}")
                    opts = re.findall(r"'([a-z0-9-]+)'", am.group(1))
                    vals = [x.replace("${" + v + "}", o) for x in vals for o in opts]
                ids.update(m.group(1) + x for x in vals)
        if s.get("ids_json") and os.path.exists(os.path.join(root, s["ids_json"])):
            doc = {t["id"] for t in json.load(open(os.path.join(root, s["ids_json"])))["tests"]}
            for x in sorted(doc ^ ids):
                self.warnings.append(f"{suite}: id {x} only in {'sources' if x in ids else s['ids_json']}")
        self.cache[key] = ids
        return ids

    def exists(self, suite, name):
        """True / False / None (unverifiable: root missing)."""
        s = self.suites[suite]
        k = s["kind"]
        if k == "jsonl":
            names = self.jsonl_keys(suite)
            if names is None:
                return None
            return any(fnmatch.fnmatchcase(n, name) for n in names)
        if k == "files":
            names = self.names(suite)
            if names is None:
                return None
            return any(fnmatch.fnmatchcase(n, name) for n in names) if any(c in name for c in "*?[") else name in names
        root = self.roots.get(suite)
        if not root:
            return None
        if k == "rust-test":
            parts = name.split("::")
            fn = parts[-1]
            base = root
            for cand in (parts[0], parts[0].replace("-", "_"), parts[0].replace("_", "-")):
                for sub in (cand, os.path.join("crates", cand)):
                    if len(parts) > 1 and os.path.isdir(os.path.join(root, sub)):
                        base = os.path.join(root, sub)
            rx = re.compile(r'\bfn\s+' + re.escape(fn) + r'\s*\(')
            return any(rx.search(open(p, errors="ignore").read()) for p in self._walk(base, "*.rs"))
        if k == "id":
            ids = self.ids(suite)
            return None if ids is None else name in ids
        if k == "string":
            pat = s.get("glob", "*")
            return any(name in open(p, errors="ignore").read() for p in self._walk(root, pat))
        raise SystemExit(f"unknown suite kind {k}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--tests", default=os.path.join(REPO, "inventory", "tests.yaml"))
    ap.add_argument("--suites", default=os.path.join(REPO, "inventory", "suites.yaml"))
    ap.add_argument("--bench-repo", default=REPO, help="git repo holding the suite branches (default: this repo)")
    ap.add_argument("--columns", default="f,mcp,web")
    ap.add_argument("--root", action="append", default=[], metavar="SUITE=PATH")
    ap.add_argument("--release", action="store_true", help="also require deferred: on missing/partial items")
    ap.add_argument("--strict", action="store_true", help="unverifiable references are failures")
    ap.add_argument("--json")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args()

    inv = load_yaml(a.inventory)
    suites = load_yaml(a.suites)["suites"]
    mapping = load_yaml(a.tests).get("items", {}) if a.tests and os.path.exists(a.tests) else {}
    roots = dict(r.split("=", 1) for r in a.root)
    for k in roots:
        if k not in suites:
            raise SystemExit(f"--root {k}: unknown suite (known: {', '.join(suites)})")
    cols = [c for c in a.columns.split(",") if c]
    res = Resolver(suites, roots, a.bench_repo)

    ids = {it["id"] for it in inv["items"]}
    problems, unverified, report = [], [], {"uncovered_have": {c: [] for c in cols}, "covered_have": {c: 0 for c in cols},
                                            "have": {c: 0 for c in cols}, "undeferred": {c: [] for c in cols},
                                            "weak_only": {c: [] for c in cols}, "partial_only": {c: [] for c in cols},
                                            "unsupported": {c: [] for c in cols}}
    for k in mapping:
        if k not in ids:
            problems.append(("unknown-item", k, "mapping entry for an id not in the inventory"))
    for it in inv["items"]:
        iid = it["id"]
        refs = []
        t = it.get("tests") or []
        refs += [r for v in t.values() for r in v] if isinstance(t, dict) else list(t)
        m = mapping.get(iid)
        deferred = it.get("deferred")
        unsupported = set()
        if isinstance(m, dict):
            refs += m.get("tests", [])
            deferred = deferred or m.get("deferred")
            unsupported = set(m.get("unsupported", []))
        elif m:
            refs += list(m)
        bycol = {}
        for r in refs:
            strength = "full"
            if isinstance(r, dict):
                strength = r.get("strength", "full")
                if strength not in ("full", "partial", "weak"):
                    problems.append(("bad-ref", iid, f"{r}: strength must be weak|partial"))
                r = r["ref"]
            suite, name = parse_ref(r)
            if suite not in suites:
                problems.append(("bad-ref", iid, f"{r}: unknown suite"))
                continue
            ok = res.exists(suite, name)
            if ok is False:
                problems.append(("unknown-id" if suites[suite]["kind"] == "id" else "missing-test", iid, r))
                continue
            if ok is None:
                unverified.append((iid, r))
            if suites[suite]["kind"] == "string":
                res.warnings.append(f"{iid}: {r}: kind string is deprecated, use a stable test id")
            bycol.setdefault(suites[suite]["column"], []).append(strength)
        for c in cols:
            st = it.get(c)
            if c in unsupported:
                report["unsupported"][c].append(iid)
                if st == "have":
                    problems.append(("unsupported-have", iid, f"column {c}: docs/19 says have, mapping says unsupported"))
                continue
            sts = set(bycol.get(c, []))
            if st == "have":
                report["have"][c] += 1
                if sts - {"weak"}:
                    report["covered_have"][c] += 1
                    if "full" not in sts:
                        report["partial_only"][c].append(iid)
                elif sts:
                    report["weak_only"][c].append(iid)
                    problems.append(("weak-only-have", iid, f"column {c}: only weak tests"))
                else:
                    report["uncovered_have"][c].append(iid)
                    problems.append(("uncovered-have", iid, f"column {c}: no test"))
            elif a.release and st in ("missing", "partial") and not deferred:
                report["undeferred"][c].append(iid)
                problems.append(("undeferred", iid, f"column {c}: {st} without deferred:"))
    if a.strict:
        problems += [("unverified", i, r) for i, r in unverified]
    names = {it["id"]: it["name"] for it in inv["items"]}
    if not a.quiet:
        for kind, iid, msg in problems:
            print(f"FAIL {kind:15s} {iid:14s} {msg}" + (f"  ({names[iid]})" if kind == "uncovered-have" else ""))
        for w in res.warnings:
            print(f"warn {w}")
        for iid, r in unverified if not a.strict else []:
            print(f"warn unverified      {iid:14s} {r} (no --root for its suite)")
    for c in cols:
        print(f"column {c}: have {report['have'][c]}, with tests {report['covered_have'][c]}, "
              f"(partial only {len(report['partial_only'][c])}), weak only {len(report['weak_only'][c])}, "
              f"uncovered {len(report['uncovered_have'][c])}" +
              (f", unsupported {len(report['unsupported'][c])}" if report['unsupported'][c] else "") +
              (f", missing/partial without deferral {len(report['undeferred'][c])}" if a.release else ""))
    nmiss = sum(1 for p in problems if p[0] == "missing-test")
    nunk = sum(1 for p in problems if p[0] == "unknown-id")
    print(f"missing tests {nmiss}, unknown ids {nunk}, unverified refs {len(unverified)}, problems {len(problems)}")
    if a.json:
        report["problems"] = problems
        report["unverified"] = unverified
        json.dump(report, open(a.json, "w"), indent=1)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
