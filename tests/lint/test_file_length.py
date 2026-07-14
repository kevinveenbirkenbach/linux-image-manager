"""Architecture guard: keep modules small (KISS/SRP)."""

from pathlib import Path

MAX_LINES = 250
REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKED_GLOBS = ("main.py", "lim/**/*.py", "tests/**/*.py")


def test_source_files_stay_below_max_lines():
    offenders = {
        str(path.relative_to(REPO_ROOT)): length
        for pattern in CHECKED_GLOBS
        for path in sorted(REPO_ROOT.glob(pattern))
        if (length := len(path.read_text().splitlines())) > MAX_LINES
    }
    assert not offenders, (
        f"Files exceeding {MAX_LINES} lines (split them, see KISS/SRP): {offenders}"
    )
