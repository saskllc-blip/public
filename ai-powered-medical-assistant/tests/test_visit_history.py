"""
Visit-history dataset tests: generator determinism, counts, referential
integrity, and the continuity / timeline rules the dataset promises.
"""
import hashlib
import importlib.util
import json
import os
import random

import pytest

import config

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_spec = importlib.util.spec_from_file_location(
    "generate_visit_history", os.path.join(APP_DIR, "scripts", "generate_visit_history.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _json(path):
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ds():
    return _json(config.VISIT_HISTORY_FILE)


@pytest.fixture(scope="module")
def patients():
    return {p["patient_id"]: p for p in _json(config.PATIENTS_FILE)}


@pytest.fixture(scope="module")
def doctors():
    return {d["doctor_id"]: d for d in _json(config.DOCTORS_FILE)}


def _by_patient(ds):
    out = {}
    for v in ds["visits"]:
        out.setdefault(v["patient_id"], []).append(v)
    return {pid: sorted(vs, key=lambda v: v["date"]) for pid, vs in out.items()}


# ── Determinism / idempotence ─────────────────────────────────────────────────
def test_same_seed_gives_identical_dataset_hash():
    a = hashlib.sha256(gen.render(gen.build_dataset()).encode()).hexdigest()
    b = hashlib.sha256(gen.render(gen.build_dataset()).encode()).hexdigest()
    assert a == b


def test_committed_file_matches_a_fresh_build():
    with open(config.VISIT_HISTORY_FILE) as f:
        assert f.read() == gen.render(gen.build_dataset())
    assert gen.main(["--check"]) == 0


def test_rerun_is_idempotent(tmp_path):
    out = tmp_path / "vh.json"
    gen.main(["--out", str(out)])
    first = out.read_bytes()
    gen.main(["--out", str(out)])
    assert out.read_bytes() == first


def test_seed_actually_drives_the_output(monkeypatch):
    base = gen.render(gen.build_dataset())
    monkeypatch.setattr(gen, "SEED", gen.SEED + 1)
    assert gen.render(gen.build_dataset()) != base


def test_generator_never_touches_the_vault_file(tmp_path):
    vault = os.path.join(config.DATA_DIR, "medical_records.json")
    existed = os.path.exists(vault)
    before = open(vault, "rb").read() if existed else None
    gen.main(["--out", str(tmp_path / "vh.json")])
    assert os.path.exists(vault) == existed
    if existed:
        assert open(vault, "rb").read() == before


# ── Counts / distribution ─────────────────────────────────────────────────────
def test_total_visits_in_scaled_target_band(ds, patients):
    target = gen.TARGET_VISITS_PER_PATIENT * len(patients)
    assert 0.8 * target <= len(ds["visits"]) <= 1.2 * target


def test_majority_of_patients_have_3_to_8_visits(ds, patients):
    counts = {pid: len(vs) for pid, vs in _by_patient(ds).items()}
    in_band = sum(1 for pid in patients if 3 <= counts.get(pid, 0) <= 8)
    assert in_band > len(patients) / 2
    assert set(counts) == set(patients)          # every patient has history


def test_lab_coverage_about_40_percent(ds, patients):
    with_labs = {l["patient_id"] for l in ds["lab_results"]}
    assert len(with_labs) == round(gen.LAB_PATIENT_SHARE * len(patients))
    per_patient = {}
    for l in ds["lab_results"]:
        per_patient[l["patient_id"]] = per_patient.get(l["patient_id"], 0) + 1
    assert all(1 <= n <= 3 for n in per_patient.values())


# ── Referential integrity ─────────────────────────────────────────────────────
def test_visits_reference_real_patients_and_doctors(ds, patients, doctors):
    ids = [v["visit_id"] for v in ds["visits"]]
    assert len(ids) == len(set(ids))
    for v in ds["visits"]:
        assert v["patient_id"] in patients
        assert v["patient_name"] == patients[v["patient_id"]]["name"]
        d = doctors[v["doctor_id"]]
        assert (v["doctor_name"], v["specialization"]) == (d["name"], d["specialization"])
        assert v["status"] == "Completed"


def test_diagnoses_belong_to_the_patients_condition_set(ds, patients):
    for v in ds["visits"]:
        conds = {h["diagnosis"] for h in patients[v["patient_id"]]["medical_history"]}
        assert v["diagnosis"] in conds, v["visit_id"]


def test_labs_attach_to_real_visits_and_fit_the_condition(ds):
    visits = {v["visit_id"]: v for v in ds["visits"]}
    lab_ids = [l["lab_id"] for l in ds["lab_results"]]
    assert len(lab_ids) == len(set(lab_ids))
    for l in ds["lab_results"]:
        v = visits[l["visit_id"]]
        assert (l["patient_id"], l["date"], l["condition"]) == (v["patient_id"], v["date"], v["diagnosis"])
        panel_key = gen.CONDITIONS[gen.condition_key(v["diagnosis"])]["lab"]
        assert panel_key is not None
        expected_panel, _ = gen.build_lab_results(panel_key, "Controlled", random.Random(0), "")
        assert l["panel"] == expected_panel


# ── Continuity / timeline ─────────────────────────────────────────────────────
def test_medication_stream_replays_to_current_medications(ds, patients):
    from tools.visit_history_tool import replay_medications
    for pid, vs in _by_patient(ds).items():
        active = []
        for v in vs:
            for mc in v["medication_changes"]:
                if mc["action"] == "adjust":
                    assert mc["previous"] in active, (v["visit_id"], mc)
                    active.remove(mc["previous"])
                if mc["action"] in ("start", "adjust"):
                    assert mc["medication"] not in active
                    active.append(mc["medication"])
        assert sorted(active) == sorted(patients[pid]["current_medications"]), pid
        assert sorted(replay_medications(vs)["active"]) == sorted(active)


def test_no_medication_conflicts_with_an_allergy(ds, patients):
    nsaids = ["ibuprofen", "naproxen", "diclofenac", "aspirin", "nsaid"]
    for v in ds["visits"]:
        allergies = [a.lower() for a in patients[v["patient_id"]]["allergies"]]
        for mc in v["medication_changes"]:
            med = mc["medication"].lower()
            assert not any(a in med for a in allergies), (v["visit_id"], med)
            if "nsaids" in allergies:
                assert not any(n in med for n in nsaids), (v["visit_id"], med)


def test_history_is_strictly_past_and_within_three_years(ds, patients):
    from datetime import date
    appts = _json(config.APPOINTMENTS_FILE)
    for pid, vs in _by_patient(ds).items():
        last = patients[pid]["last_visit"]
        dates = [v["date"] for v in vs]
        assert len(dates) == len(set(dates))
        assert max(dates) == last                    # nothing post-dates last_visit
        span = (date.fromisoformat(last) - date.fromisoformat(min(dates))).days
        assert span <= gen.MAX_HISTORY_DAYS
        for a in appts:
            if a["patient_id"] == pid:
                assert max(dates) < a["date"]        # booking stays the future book


def test_medical_history_entries_are_reproduced_verbatim(ds, patients):
    for pid, p in patients.items():
        anchors = {v["date"]: v for v in ds["visits"]
                   if v["patient_id"] == pid and v["source"] != "generated"}
        assert len(anchors) == len(p["medical_history"])
        for h in p["medical_history"]:
            v = anchors[h["date"]]
            assert (v["diagnosis"], v["doctor_name"], v["treatment"], v["notes"]) == \
                   (h["diagnosis"], h["doctor"], h["treatment"], h["notes"])


def test_referral_is_followed_by_the_specialist_visit(ds):
    for pid, vs in _by_patient(ds).items():
        for i, v in enumerate(vs):
            if not v["referral"]:
                continue
            nxt = next(w for w in vs[i + 1:] if w["diagnosis"] == v["diagnosis"]
                       and w["visit_type"] not in ("Acute Visit", "Referral"))
            assert nxt["doctor_id"] == v["referral"]["to_doctor_id"]
            assert nxt["referred_from_visit_id"] == v["visit_id"]
            assert nxt["visit_type"] == "Specialist Consultation"
    referred = [v for v in ds["visits"] if v["referred_from_visit_id"]]
    ids = {v["visit_id"]: v for v in ds["visits"]}
    for v in referred:
        assert ids[v["referred_from_visit_id"]]["referral"]["to_doctor_id"] == v["doctor_id"]


def test_chronic_visits_dominate_and_acute_is_sparse(ds):
    for pid, vs in _by_patient(ds).items():
        acute = [v for v in vs if v["visit_type"] == "Acute Visit"]
        assert len(acute) <= 2
        # Every acute visit happens after that condition was first seen.
        for a in acute:
            first = min(v["date"] for v in vs if v["diagnosis"] == a["diagnosis"]
                        and v["visit_type"] != "Acute Visit")
            assert first < a["date"]


def test_lab_values_track_control_status():
    """Primary marker is worse when uncontrolled than when controlled."""
    markers = {"a1c": ("HbA1c", 1), "thyroid": ("TSH", 1), "cbc": ("Haemoglobin", -1),
               "inflammatory": ("ESR", 1), "renal": ("eGFR", -1), "lipid": ("LDL", 1),
               "bone": ("25-OH Vitamin D", -1), "spirometry": ("FEV1 % predicted", -1)}
    rng = random.Random(7)
    for panel, (test, sign) in markers.items():
        for _ in range(20):
            _, bad = gen.build_lab_results(panel, "Uncontrolled", rng, "")
            _, good = gen.build_lab_results(panel, "Controlled", rng, "")
            b = next(r["value"] for r in bad if r["test"] == test)
            g = next(r["value"] for r in good if r["test"] == test)
            assert sign * (b - g) > 0, (panel, b, g)


def test_lab_values_honour_numbers_quoted_in_anchor_notes(ds):
    visits = {v["visit_id"]: v for v in ds["visits"]}
    for l in ds["lab_results"]:
        v = visits[l["visit_id"]]
        if v["source"] == "generated":
            continue
        for r in l["results"]:
            if r["test"] in ("HbA1c", "TSH", "Haemoglobin", "ESR"):
                key = {"Haemoglobin": "Hemoglobin"}.get(r["test"], r["test"])
                if key in v["notes"]:
                    assert str(r["value"]) in v["notes"]


# ── Tool layer ────────────────────────────────────────────────────────────────
@pytest.fixture
def isolated_tool_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TOOL_LOGS_FILE", str(tmp_path / "tool_logs.json"))


def test_tool_returns_patient_history_newest_first(isolated_tool_logs, patients):
    from tools.visit_history_tool import get_patient_visits
    for pid, p in patients.items():
        r = get_patient_visits(pid)
        assert r["success"]
        dates = [v["date"] for v in r["visits"]]
        assert dates == sorted(dates, reverse=True)
        assert sorted(r["medications"]["active"]) == sorted(p["current_medications"])


def test_ehr_history_text_includes_visit_timeline(isolated_tool_logs):
    from tools.ehr_tool import get_medical_history
    r = get_medical_history("P001")
    assert r["success"] and r["visit_count"] > 0
    assert "Visit Timeline" in r["history_text"]


def test_missing_store_degrades_to_empty(isolated_tool_logs, tmp_path, monkeypatch):
    from tools.visit_history_tool import get_patient_visits
    monkeypatch.setattr(config, "VISIT_HISTORY_FILE", str(tmp_path / "absent.json"))
    r = get_patient_visits("P001")
    assert r["success"] and r["visits"] == []
