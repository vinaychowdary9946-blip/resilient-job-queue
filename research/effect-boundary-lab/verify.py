"""Independent recomputation of recorded evidence. No import of lab metrics."""
import hashlib
import itertools
import json
from pathlib import Path
import sys

def digest(p):
    return hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def verify(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["schema"] == 1
    assert hashlib.sha256(Path(__file__).with_name("lab.py").read_bytes()).hexdigest() == data["source_sha256"]
    rows = data["trials"]
    design = data["design"]
    expected = set(itertools.product(design["workloads"], range(data["seeds"]), design["scenarios"], design["policies"]))
    observed = {(r["workload"], r["seed"], r["scenario"], r["policy"]) for r in rows}
    assert observed == expected and len(rows) == len(expected), "incomplete or repeated factorial design"
    sums = {}
    for r in rows:
        effects, recovery = r["effects"], r["recovery"]
        assert all(e["hash"] == digest(e["payload"]) for e in effects)
        assert len({e["id"] for e in effects}) == len(effects)
        assert r["integrity_ok"]
        values = {"effect_count": len(effects), "duplicates": max(0, len(effects)-1),
                  "missing": int(not effects),
                  "wrong_payload": sum(e["hash"] != digest(r["original"]) for e in effects),
                  "false_confirmation": int(recovery["status"] == "confirmed" and not any(
                      e["id"] == recovery["effect"] and e["hash"] == digest(r["retry"]) for e in effects))}
        for key, value in values.items():
            assert r[key] == value, (r["trial"], key)
        key = (r["scenario"], r["policy"])
        group = sums.setdefault(key, {"trials": 0, **{k: 0 for k in values}, "requests": 0,
                                     "process_exits": 0, "confirmed": 0, "quarantined": 0,
                                     "conflict": 0, "error": 0})
        group["trials"] += 1
        for k, v in values.items():
            group[k] += v
        for k in ("requests", "process_exits"):
            group[k] += r[k]
        group[recovery["status"]] += 1
        if r["policy"] == "guarded":
            assert values["duplicates"] == values["wrong_payload"] == values["false_confirmation"] == 0
            assert recovery["status"] == ("conflict" if r["scenario"] == "changed_retry" else
                   "quarantined" if r["scenario"] in ("expired_after_effect", "expiry_before_send") else "confirmed")
    assert len(data["summary"]) == len(sums)
    for row in data["summary"]:
        assert {k: v for k, v in row.items() if k not in ("scenario", "policy")} == sums[(row["scenario"], row["policy"])]
    return {"verified_trials": len(rows), "groups": len(sums), "source_match": True}

if __name__ == "__main__":
    print(json.dumps(verify(sys.argv[1] if len(sys.argv) > 1 else "evidence/results.json")))
