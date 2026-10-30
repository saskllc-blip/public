"""Runtime state the app writes (vault uploads, logs, keys) must stay out of git."""
import os
import shutil
import subprocess

import pytest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATHS = ["uploads/lab_results/x.pdf", "logs/tool_logs.json",
         "data/medical_records.json", ".env", "tools/__pycache__/x.pyc"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
@pytest.mark.parametrize("path", PATHS)
def test_runtime_paths_are_ignored(path):
    r = subprocess.run(["git", "check-ignore", "-q", path], cwd=APP_DIR)
    if r.returncode == 128:
        pytest.skip("not a git checkout")
    assert r.returncode == 0, f"{path} is not git-ignored"
