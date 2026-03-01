import json
import sys
from pathlib import Path


PARETO_FILES = {
    "backend/application/geojson.py": 100.0,
    "backend/domain/osm.py": 100.0,
    "backend/shared/auth.py": 100.0,
    "backend/infrastructure/api.py": 100.0,
}

DEFAULT_MIN = 80.0


def pct(covered: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return (covered / total) * 100.0


def normpath(path: str) -> str:
    return path.replace("\\", "/")


def main() -> int:
    cov_path = Path(__file__).resolve().parent.parent / "coverage.json"
    if not cov_path.exists():
        print(f"coverage_gate: missing {cov_path}. Run pytest first.")
        return 2

    data = json.loads(cov_path.read_text(encoding="utf-8"))
    files = data.get("files") or {}

    failures = []

    # Normalize keys to be OS-agnostic
    norm_files = {normpath(relpath): entry for relpath, entry in files.items()}

    # 1) Critical files must be 100%
    for critical_relpath, required in PARETO_FILES.items():
        entry = norm_files.get(critical_relpath)
        if not entry:
            failures.append((critical_relpath, 0.0, required, 0, 0))
            continue

        summary = entry.get("summary") or {}
        covered = int(summary.get("covered_lines", 0))
        num = int(summary.get("num_statements", 0))
        file_pct = pct(covered, num)
        if file_pct + 1e-9 < required:
            failures.append((critical_relpath, file_pct, required, covered, num))

    # 2) Rest must be >=80% aggregated
    covered_total = 0
    stmts_total = 0
    for relpath, entry in norm_files.items():
        if relpath in PARETO_FILES:
            continue

        summary = entry.get("summary") or {}
        covered = int(summary.get("covered_lines", 0))
        num = int(summary.get("num_statements", 0))
        covered_total += covered
        stmts_total += num

    rest_pct = pct(covered_total, stmts_total)
    if rest_pct + 1e-9 < DEFAULT_MIN:
        failures.append(("<rest_of_codebase>", rest_pct, DEFAULT_MIN, covered_total, stmts_total))

    if failures:
        print("coverage_gate: FAILED")
        for relpath, file_pct, required, covered, num in sorted(failures):
            print(f"- {relpath}: {file_pct:.2f}% (required {required:.2f}%) [{covered}/{num}]")
        return 1

    print("coverage_gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
