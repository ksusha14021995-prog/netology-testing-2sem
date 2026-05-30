"""Export mutmut cache to mut.json.

mutmut 2.5.1's built-in `results` / `junitxml` commands crash on a
Pony ORM compatibility issue (`QueryResultIterator object is not iterable`),
so we read the sqlite cache directly and produce a structured JSON report
matching the assignment format request.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".mutmut-cache"
OUT = ROOT / "mut.json"

STATUS_LABELS = {
    "ok_killed": "killed",
    "bad_survived": "survived",
    "bad_timeout": "timeout",
    "ok_suspicious": "suspicious",
    "skipped": "skipped",
}


def diff_for(mid: int) -> str:
    try:
        out = subprocess.run(
            [sys.executable, "-m", "mutmut", "show", str(mid)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
        return out.stdout.strip()
    except Exception as e:
        return f"(diff fetch failed: {e})"


def main() -> int:
    con = sqlite3.connect(CACHE)
    cur = con.cursor()

    counts: dict[str, int] = {}
    for raw_status, n in cur.execute(
        "SELECT status, COUNT(*) FROM Mutant GROUP BY status"
    ):
        counts[STATUS_LABELS.get(raw_status, raw_status)] = n

    total = sum(counts.values())
    killed = counts.get("killed", 0)
    survived = counts.get("survived", 0)
    suspicious = counts.get("suspicious", 0)
    timeout = counts.get("timeout", 0)

    denom = killed + survived
    score = round(100.0 * killed / denom, 2) if denom else 0.0

    rows = list(cur.execute(
        'SELECT id, "index", status, line FROM Mutant ORDER BY id'
    ))
    line_cache: dict[int, tuple[str, int]] = {}
    file_cache: dict[int, str] = {}
    mutants = []
    for mid, idx, raw_status, lid in rows:
        if lid not in line_cache:
            line_cache[lid] = cur.execute(
                "SELECT line, sourcefile FROM Line WHERE id=?", (lid,)
            ).fetchone()
        line_text, sfid = line_cache[lid]
        if sfid not in file_cache:
            file_cache[sfid] = cur.execute(
                "SELECT filename FROM SourceFile WHERE id=?", (sfid,)
            ).fetchone()[0]
        fname = file_cache[sfid]
        entry = {
            "id": mid,
            "mutation_index": idx,
            "status": STATUS_LABELS.get(raw_status, raw_status),
            "file": fname.replace("\\", "/"),
            "line": line_text.rstrip(),
        }
        if entry["status"] == "survived":
            entry["diff"] = diff_for(mid)
        mutants.append(entry)

    payload = {
        "tool": "mutmut",
        "tool_version": "2.5.1",
        "paths_to_mutate": ["billing"],
        "summary": {
            "total": total,
            "killed": killed,
            "survived": survived,
            "suspicious": suspicious,
            "timeout": timeout,
            "mutation_score_percent": score,
        },
        "mutants": mutants,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUT} — {total} mutants, score {score}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
