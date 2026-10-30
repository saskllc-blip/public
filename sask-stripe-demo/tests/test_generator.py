"""Generator determinism, idempotency, and dataset size bands."""
from __future__ import annotations

import hashlib
import json

import generate_data as gen
import history


def test_same_seed_gives_identical_dataset() -> None:
    first = gen.render_files(gen.generate())
    second = gen.render_files(gen.generate())
    assert first == second
    digest = lambda files: hashlib.sha256(  # noqa: E731
        json.dumps(files, sort_keys=True).encode()
    ).hexdigest()
    assert digest(first) == digest(second)


def test_different_seed_changes_dataset() -> None:
    assert gen.generate(gen.SEED + 1) != gen.generate(gen.SEED)


def test_committed_files_match_generator_byte_for_byte() -> None:
    files = gen.render_files(gen.generate())
    for name, text in files.items():
        committed = (history.DATA_DIR / name).read_text(encoding="utf-8")
        assert committed == text, f"{name} drifted — rerun data/generate_data.py"


def test_rerun_into_new_dir_is_idempotent(tmp_path) -> None:
    first = gen.write(tmp_path)
    snapshot = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    second = gen.write(tmp_path)
    assert first == second
    assert snapshot == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_manifest_records_seed_anchor_and_hashes() -> None:
    manifest = history.load_dataset().manifest
    assert manifest["generated"] == "synthetic-fictional-only"
    assert manifest["seed"] == gen.SEED
    assert manifest["anchor"] == "2026-10-25T23:59:59Z"
    assert manifest["window_start"] == "2026-07-28T00:00:00Z"
    assert manifest["window_days"] == 90
    for name, sha in manifest["files"].items():
        data = (history.DATA_DIR / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == sha


def test_counts_in_specified_bands() -> None:
    counts = history.load_dataset().manifest["counts"]
    assert 10 <= counts["products"] <= 14
    assert 108 <= counts["customers"] <= 132
    assert 270 <= counts["orders"] <= 330
    assert 405 <= counts["payment_attempts"] <= 495
    assert 1080 <= counts["webhook_events"] <= 1320
    orders = counts["orders"]
    assert 0.04 <= counts["refunds"] / orders <= 0.06
    assert 0.005 <= counts["disputes"] / orders <= 0.015
