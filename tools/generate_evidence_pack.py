from __future__ import annotations

import datetime as _dt
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_git(args: list[str]) -> str:
    try:
        out = subprocess.check_output(["git", *args], cwd=str(REPO_ROOT), stderr=subprocess.STDOUT)
        return out.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_info() -> dict[str, str]:
    commit_full = _run_git(["rev-parse", "HEAD"])
    commit_short = commit_full[:12] if commit_full else ""
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    remote = _run_git(["remote", "get-url", "origin"])
    describe = _run_git(["describe", "--tags", "--always", "--dirty"])
    commit_date = _run_git(["show", "-s", "--format=%cI", "HEAD"])
    dirty = "true" if _run_git(["status", "--porcelain"]) else "false"
    return {
        "commit": commit_full or "unknown",
        "commit_short": commit_short or "unknown",
        "branch": branch or "unknown",
        "remote": remote or "",
        "describe": describe or "",
        "commit_date": commit_date or "",
        "dirty": dirty,
    }


def _env_info() -> dict[str, str]:
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "ci": "true" if os.getenv("CI") else "false",
        "github_run_id": os.getenv("GITHUB_RUN_ID", ""),
        "github_workflow": os.getenv("GITHUB_WORKFLOW", ""),
        "github_sha": os.getenv("GITHUB_SHA", ""),
    }


def _safe_copy(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def _zip_dir(src_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in src_dir.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(src_dir)
            zf.write(p, rel.as_posix())


def _collect_results(pack_dir: Path) -> None:
    out_root = REPO_ROOT / "qa" / "out"
    results_dir = pack_dir / "results"

    # Preferir `qa/out/*` (padrão "audit-ready"), mas também suportar saídas
    # padrão de ferramentas (caso o dev rode localmente).
    candidates: list[tuple[Path, Path]] = [
        # Saídas padronizadas (recomendado)
        (out_root / "test-reports", results_dir / "test-reports"),
        (out_root / "pytest", results_dir / "pytest"),
        (out_root / "vitest", results_dir / "vitest"),
        (out_root / "playwright", results_dir / "playwright"),
        (out_root / "playwright-report", results_dir / "playwright-report"),
        (out_root / "e2e", results_dir / "e2e"),
        # Padrões do Playwright (quando rodado no frontend diretamente)
        (REPO_ROOT / "src" / "frontend" / "test-results", results_dir / "playwright-test-results"),
        (Path(os.getenv("LOCALAPPDATA", "")) / "sisRUA" / "qa" / "out" / "geometry_compliance.xml", results_dir / "geometry_compliance.xml"),
        (Path.home() / "AppData" / "Local" / "sisRUA" / "qa" / "out" / "geometry_compliance.xml", results_dir / "geometry_compliance.xml"),
        (REPO_ROOT / "src" / "backend" / "backend" / "gis_core" / "topology_report.json", results_dir / "topology_integrity_report.json"),
    ]

    for src, dst in candidates:
        _safe_copy(src, dst)

    # Coletar outros artefatos que possam existir em `qa/out/`, sem recursão
    # para dentro do evidence pack atual (evita "copiar a si mesmo").
    if out_root.exists():
        for child in out_root.iterdir():
            name = child.name
            if name.startswith("evidence_"):
                continue
            if name.endswith(".zip") and name.startswith("evidence_"):
                continue
            # já copiados acima
            if name in {"test-reports", "pytest", "vitest", "playwright", "playwright-report", "e2e"}:
                continue
            _safe_copy(child, results_dir / name)


def _write_manifest(pack_dir: Path, version: str, generated_utc: str, git: dict[str, str]) -> None:
    manifest = pack_dir / "MANIFEST.txt"
    files: list[tuple[str, int, str]] = []

    for p in sorted(pack_dir.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(pack_dir).as_posix()
        size = p.stat().st_size
        sha256 = _sha256_file(p)
        files.append((rel, size, sha256))

    total_bytes = sum(sz for _, sz, _ in files)

    env = _env_info()
    lines: list[str] = []
    lines += [
        "product=sisRUA",
        f"version={version}",
        f"generated_utc={generated_utc}",
        f"git_commit={git.get('commit','')}",
        f"git_commit_short={git.get('commit_short','')}",
        f"git_branch={git.get('branch','')}",
        f"git_dirty={git.get('dirty','')}",
        f"git_commit_date={git.get('commit_date','')}",
        f"git_describe={git.get('describe','')}",
        f"git_remote_origin={git.get('remote','')}",
        f"file_count={len(files)}",
        f"total_bytes={total_bytes}",
        "",
        "[environment]",
    ]
    for k in sorted(env.keys()):
        v = env[k]
        if v:
            lines.append(f"{k}={v}")

    lines += ["", "[files]"]
    lines += [f"{rel}\t{size}\tsha256={sha}" for rel, size, sha in files]
    lines.append("")

    manifest.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    version = (REPO_ROOT / "VERSION.txt").read_text(encoding="utf-8", errors="replace").strip() if (REPO_ROOT / "VERSION.txt").exists() else "0.0.0"
    git = _git_info()
    commit = (git.get("commit_short") or "unknown")[:12]
    date = _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    out_root = REPO_ROOT / "qa" / "out"
    pack_dir = out_root / f"evidence_{version}_{date}_{commit}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    # QA docs + rastreabilidade
    _safe_copy(REPO_ROOT / "qa" / "requirements.md", pack_dir / "qa" / "requirements.md")
    _safe_copy(REPO_ROOT / "qa" / "traceability.csv", pack_dir / "qa" / "traceability.csv")
    _safe_copy(REPO_ROOT / "qa" / "test-plan.md", pack_dir / "qa" / "test-plan.md")
    _safe_copy(REPO_ROOT / "qa" / "manual", pack_dir / "qa" / "manual")

    # Legal/compliance
    _safe_copy(REPO_ROOT / "PRIVACY.md", pack_dir / "legal" / "PRIVACY.md")
    _safe_copy(REPO_ROOT / "EULA.md", pack_dir / "legal" / "EULA.md")
    _safe_copy(REPO_ROOT / "THIRD_PARTY_NOTICES.md", pack_dir / "legal" / "THIRD_PARTY_NOTICES.md")

    # Docs úteis
    _safe_copy(REPO_ROOT / "docs" / "PRODUCAO.md", pack_dir / "docs" / "PRODUCAO.md")
    _safe_copy(REPO_ROOT / "docs" / "TESTES_MANUAIS_AUTOCAD.md", pack_dir / "docs" / "TESTES_MANUAIS_AUTOCAD.md")
    _safe_copy(REPO_ROOT / "docs" / "TROUBLESHOOTING.md", pack_dir / "docs" / "TROUBLESHOOTING.md")
    _safe_copy(REPO_ROOT / "docs" / "RELEASE.md", pack_dir / "docs" / "RELEASE.md")
    _safe_copy(REPO_ROOT / "docs" / "compliance" / "ISO_27001_Alignment.md", pack_dir / "legal" / "ISO_27001_Alignment.md")
    _safe_copy(REPO_ROOT / "docs" / "compliance" / "ISO_9001_Alignment.md", pack_dir / "legal" / "ISO_9001_Alignment.md")
    _safe_copy(REPO_ROOT / "src" / "backend" / "backend" / "gis_core" / "IP_MOAT.md", pack_dir / "docs" / "IP_PROTECTION_REPORT.md")

    # Resultados (se já foram gerados)
    _collect_results(pack_dir)

    # Manifesto com metadados + hashes (audit-friendly)
    _write_manifest(pack_dir, version=version, generated_utc=date, git=git)

    zip_path = out_root / f"evidence_{version}_{date}_{commit}.zip"
    _zip_dir(pack_dir, zip_path)

    print(f"OK: Evidence pack gerado: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

