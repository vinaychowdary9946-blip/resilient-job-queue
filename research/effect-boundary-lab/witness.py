"""Produce equal durable client states with different remote outcomes."""
import hashlib
import json
from pathlib import Path
import tempfile
import lab


def produce():
    histories = []
    with tempfile.TemporaryDirectory(prefix="ambiguity-witness-") as tmp:
        root = Path(tmp)
        for crash in ("before_send", "after_effect"):
            local = root / (crash + "-local.db")
            with lab.Service(root / (crash + "-provider.db")) as service:
                payload = {"op": "payment", "value": 100}
                first, _ = lab.worker(local, service.url, "guarded", payload, 0, crash)
                with lab.connect(local) as c:
                    state = list(c.execute("SELECT hash,started,effect FROM intent WHERE id=1").fetchone())
                with lab.connect(service.server.db) as c:
                    effects = c.execute("SELECT count(*) FROM effects").fetchone()[0]
                recovery, _ = lab.worker(local, service.url, "guarded", payload, 20, "none")
                histories.append({"crash": crash, "worker_observation": first,
                                  "durable_client_state": state, "remote_effect_count": effects,
                                  "recovery": recovery})
    assert histories[0]["durable_client_state"] == histories[1]["durable_client_state"]
    assert [h["remote_effect_count"] for h in histories] == [0, 1]
    assert all(h["recovery"]["status"] == "quarantined" for h in histories)
    return {"study": "Durable-state ambiguity witness", "histories": histories,
            "equal_client_state": True, "different_remote_outcomes": True,
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), Path(lab.__file__))}}


if __name__ == "__main__":
    result = produce()
    path = Path("evidence/ambiguity-witness.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("equal_client_state", "different_remote_outcomes")}))
