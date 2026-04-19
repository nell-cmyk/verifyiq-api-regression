"""JSON + Markdown writer for a single regression run."""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.reporting.collector import CaseRecord, Collector


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _case_dict(case: CaseRecord) -> dict[str, Any]:
    d = asdict(case)
    d["start_ts"] = _iso(case.start_ts)
    d["end_ts"] = _iso(case.end_ts)
    duration_ms: float | None = None
    if case.end_ts is not None:
        duration_ms = round((case.end_ts - case.start_ts) * 1000.0, 2)
    d["duration_ms"] = duration_ms
    # Convert sent_at/received_at in requests/responses
    for r in d.get("requests", []):
        r["sent_at"] = _iso(r.get("sent_at"))
    for r in d.get("responses", []):
        r["received_at"] = _iso(r.get("received_at"))
    return d


def _totals(cases: list[CaseRecord]) -> dict[str, int]:
    totals = {"collected": len(cases), "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "error": 0}
    for c in cases:
        if c.outcome:
            totals["executed"] += 1
        if c.outcome == "PASSED":
            totals["passed"] += 1
        elif c.outcome == "FAILED":
            totals["failed"] += 1
        elif c.outcome == "SKIPPED":
            totals["skipped"] += 1
        elif c.outcome == "ERROR":
            totals["error"] += 1
    return totals


def _group_counts(cases: list[CaseRecord], attr: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for c in cases:
        if attr == "endpoint":
            key = c.endpoint or "(unknown)"
        elif attr == "file_type":
            key = (c.file_type or {}).get("request") or (c.file_type or {}).get("registry") or "(none)"
        else:
            key = "(none)"
        bucket = out.setdefault(key, {"passed": 0, "failed": 0, "skipped": 0, "error": 0})
        if c.outcome == "PASSED":
            bucket["passed"] += 1
        elif c.outcome == "FAILED":
            bucket["failed"] += 1
        elif c.outcome == "SKIPPED":
            bucket["skipped"] += 1
        elif c.outcome == "ERROR":
            bucket["error"] += 1
    return out


def write_run(
    collector: Collector,
    *,
    tier: str,
    base_url: str,
    out_dir: Path,
) -> dict[str, Path]:
    cases = collector.cases()
    now = time.time()
    run_meta: dict[str, Any] = {
        "timestamp": _iso(collector.run_started_at),
        "finished": _iso(now),
        "tier": tier,
        "base_url": base_url,
        "duration_s": round(now - collector.run_started_at, 2),
        "totals": _totals(cases),
        "by_endpoint": _group_counts(cases, "endpoint"),
        "by_file_type": _group_counts(cases, "file_type"),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"
    md_path = out_dir / "report.md"

    payload = {"run": run_meta, "cases": [_case_dict(c) for c in cases]}
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_render_markdown(run_meta, cases), encoding="utf-8")

    # Best-effort "latest" pointer (text file — Windows-safe).
    try:
        (out_dir.parent / "LATEST.txt").write_text(out_dir.name + "\n", encoding="utf-8")
    except Exception:
        pass

    return {"json": json_path, "md": md_path}


def _fmt_outcome(o: str) -> str:
    return o or "(no outcome)"


def _render_markdown(run: dict[str, Any], cases: list[CaseRecord]) -> str:
    totals = run["totals"]
    lines: list[str] = []
    lines.append(f"# Regression Report — `{run['tier']}`")
    lines.append("")
    lines.append(f"- Run started: {run['timestamp']}")
    lines.append(f"- Duration: {run['duration_s']}s")
    lines.append(f"- Base URL: `{run['base_url']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        f"- Collected: **{totals['collected']}** | Executed: **{totals['executed']}** | "
        f"Passed: **{totals['passed']}** | Failed: **{totals['failed']}** | "
        f"Skipped: **{totals['skipped']}** | Error: **{totals['error']}**"
    )
    lines.append("")

    if run["by_file_type"]:
        lines.append("### By fileType")
        lines.append("")
        lines.append("| fileType | passed | failed | skipped | error |")
        lines.append("|---|---:|---:|---:|---:|")
        for k in sorted(run["by_file_type"]):
            b = run["by_file_type"][k]
            lines.append(f"| `{k}` | {b['passed']} | {b['failed']} | {b['skipped']} | {b['error']} |")
        lines.append("")

    failed = [c for c in cases if c.outcome in {"FAILED", "ERROR"}]
    if failed:
        lines.append("## Failures")
        lines.append("")
        for c in failed:
            lines.append(f"- `{c.nodeid}` — {_fmt_outcome(c.outcome)}")
        lines.append("")

    lines.append("## Cases")
    lines.append("")
    for c in cases:
        lines.append(f"### `{c.nodeid}` — {_fmt_outcome(c.outcome)}")
        lines.append("")
        duration_ms: float | None = None
        if c.end_ts is not None:
            duration_ms = round((c.end_ts - c.start_ts) * 1000.0, 2)
        lines.append(f"- Module: `{c.module}`")
        lines.append(f"- Test: `{c.test}`")
        if c.endpoint:
            lines.append(f"- Endpoint: `{c.endpoint}`")
        if c.file_type:
            lines.append(f"- fileType: `{c.file_type}`")
        if c.fixture:
            lines.append(f"- Fixture: `{c.fixture}`")
        lines.append(f"- Start: {_iso(c.start_ts)}")
        if c.end_ts is not None:
            lines.append(f"- End: {_iso(c.end_ts)}")
        if duration_ms is not None:
            lines.append(f"- Duration (ms): {duration_ms}")
        lines.append("")

        for i, req in enumerate(c.requests, 1):
            lines.append(f"<details><summary>Request #{i} — {req.method} {req.path}</summary>")
            lines.append("")
            lines.append("```")
            lines.append(f"{req.method} {req.url}")
            for k, v in req.headers.items():
                lines.append(f"{k}: {v}")
            lines.append("")
            if req.body is not None:
                try:
                    import json as _j
                    lines.append(_j.dumps(req.body, indent=2, default=str))
                except Exception:
                    lines.append(str(req.body))
            elif req.body_text:
                lines.append(req.body_text + ("\n[truncated]" if req.body_truncated else ""))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        for i, resp in enumerate(c.responses, 1):
            lines.append(
                f"<details><summary>Response #{i} — status {resp.status} "
                f"({round(resp.elapsed_ms or 0, 1)} ms)</summary>"
            )
            lines.append("")
            lines.append("```")
            lines.append(f"HTTP {resp.status}")
            for k, v in resp.headers.items():
                lines.append(f"{k}: {v}")
            lines.append("")
            if resp.body is not None:
                try:
                    import json as _j
                    lines.append(_j.dumps(resp.body, indent=2, default=str))
                except Exception:
                    lines.append(str(resp.body))
            elif resp.body_text:
                lines.append(resp.body_text + ("\n[truncated]" if resp.body_truncated else ""))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        if c.longrepr:
            lines.append("<details><summary>Failure details</summary>")
            lines.append("")
            lines.append("```")
            lines.append(c.longrepr)
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")

    return "\n".join(lines) + "\n"


def run_output_dir(repo_root: Path, started_at: float) -> Path:
    stamp = datetime.fromtimestamp(started_at, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = os.getenv("REGRESSION_REPORT_DIR", "").strip()
    if base:
        return Path(base) / stamp
    return repo_root / "reports" / "regression" / stamp
