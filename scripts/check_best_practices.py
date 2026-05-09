"""
Lightweight API best-practices report for codebase.bat step [7/10].
Optional config: .api-checker-config.json (reserved for future rules).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _load_checker_config() -> dict[str, object]:
    path = _BACKEND / ".api-checker-config.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _score_app() -> tuple[float, list[str]]:
    issues: list[str] = []
    try:
        from app.main import app

        routes = [
            r
            for r in app.routes
            if getattr(r, "methods", None) and getattr(r, "path", None)
        ]
        n = len(routes)
        if n < 1:
            issues.append("no HTTP routes found")
        score = min(100.0, 40.0 + min(60.0, n * 0.25))
    except Exception as exc:
        issues.append(f"app inspection failed: {exc}")
        score = 0.0
    return score, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="API best-practices checklist")
    parser.add_argument(
        "--output",
        required=True,
        help="JSON report path (e.g. reports/check_report_bat.json)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "both"),
        default="both",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum score (0–100); exit non-zero if below unless --no-fail",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        dest="no_fail",
        help="Always exit 0 (still writes report)",
    )
    args = parser.parse_args()

    _load_checker_config()
    score, issues = _score_app()

    below = args.threshold is not None and score < args.threshold
    failed = bool(issues) or below

    report = {
        "score": score,
        "threshold": args.threshold,
        "issues": issues,
        "passed": not failed,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.format in ("text", "both"):
        print(f"Best-practices score: {score:.1f}/100")
        for msg in issues:
            print(f"  - {msg}")
        if below and not issues:
            print(
                f"  - score below threshold " f"({score:.1f} < {args.threshold})",
                file=sys.stderr,
            )

    if failed and args.no_fail:
        return 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
