"""PostToolUse hook: run pytest after Claude edits a file in source_code/src/ or source_code/tests/.

Exit 0 = tests passed or nothing to run. Exit 2 = tests failed; the output on
stderr is sent back to Claude so it fixes the failure before moving on.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def project_python() -> str:
    for candidate in (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    rel = file_path.replace("\\", "/")
    if not rel.endswith(".py") or not ("source_code/src/" in rel or "source_code/tests/" in rel):
        return 0
    if not any((ROOT / "source_code" / "tests").glob("test_*.py")):
        return 0

    try:
        result = subprocess.run(
            [project_python(), "-m", "pytest", "-q", "-x", "--no-header", "-m", "not slow"],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        print("pytest timed out after 180 s — consider marking slow tests with @pytest.mark.slow", file=sys.stderr)
        return 2
    except FileNotFoundError:
        return 0

    if "No module named pytest" in result.stderr:
        return 0
    if result.returncode not in (0, 5):  # 5 = no tests collected
        tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-40:])
        print(f"pytest failed after editing {rel}:\n{tail}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
