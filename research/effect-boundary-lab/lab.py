"""Effect Boundary Lab: loopback HTTP, independent durable stores, real worker exits.
Python 3.10+, standard library only. Never use this simulator for real transactions.
"""
import argparse
import csv
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

POLICIES = ("naive", "local_receipt", "keyed", "guarded")
SCENARIOS = ("clean", "before_send", "after_effect", "before_receipt_commit",
             "after_receipt", "expired_after_effect", "expiry_before_send", "changed_retry")
WORKLOADS = ("payment", "stock", "notification")
TTL = 10
CRASH = 73

def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()

@contextmanager
def connect(path):
    con = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        with con:
            yield con
    finally:
        con.close()

def init_provider(path):
    with connect(path) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS effects(id INTEGER PRIMARY KEY, op TEXT NOT NULL,
          hash TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS receipts(key TEXT PRIMARY KEY, hash TEXT NOT NULL,
          effect INTEGER NOT NULL, created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY, key TEXT, now INTEGER,
          status INTEGER NOT NULL);
        """)

def apply_effect(path, key, payload, now):
    """Provider atomically commits effect + expiring receipt, checks payload binding."""
    digest = fingerprint(payload)
    with connect(path) as c:
        c.execute("BEGIN IMMEDIATE")
        c.execute("DELETE FROM receipts WHERE ? - created >= ?", (now, TTL))
        old = c.execute("SELECT hash,effect FROM receipts WHERE key=?", (key,)).fetchone()
        if key and old:
            code, result = ((200, {"effect": old[1], "replayed": True}) if old[0] == digest
                            else (409, {"error": "payload_conflict"}))
        else:
            effect = c.execute("INSERT INTO effects(op,hash,payload) VALUES (?,?,?)",
                               (payload["op"], digest, json.dumps(payload, sort_keys=True))).lastrowid
            if key:
                c.execute("INSERT INTO receipts VALUES (?,?,?,?)", (key, digest, effect, now))
            code, result = 200, {"effect": effect, "replayed": False}
        c.execute("INSERT INTO requests(key,now,status) VALUES (?,?,?)", (key, now, code))
        c.commit()
    return code, result

class Provider(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        if self.path != "/effect":
            return self.reply(404, {"error": "not_found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 8192:
                return self.reply(400, {"error": "invalid_size"})
            body = json.loads(self.rfile.read(size))
            payload, now, key = body["payload"], body["now"], body.get("key")
            if (not isinstance(payload, dict) or payload.get("op") not in WORKLOADS
                or type(payload.get("value")) is not int or not 1 <= payload["value"] <= 10000
                or type(now) is not int or now < 0
                or (key is not None and (not isinstance(key, str) or not 1 <= len(key) <= 128))):
                raise ValueError("invalid input")
            code, data = apply_effect(self.server.db, key, payload, now)
            self.reply(code, data)
        except (ValueError, TypeError, KeyError):
            self.reply(400, {"error": "invalid_input"})
        except sqlite3.Error:
            self.reply(500, {"error": "storage_error"})

    def reply(self, code, data):
        blob = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

class Service:
    def __init__(self, db):
        init_provider(db)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        self.server.daemon_threads = True
        self.server.db = str(db)
        self.url = "http://127.0.0.1:%d/effect" % self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def post(url, key, payload, now):
    req = Request(url, data=json.dumps({"key": key, "payload": payload, "now": now}).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def checkpoint(actual, target):
    if actual == target:
        os._exit(CRASH)


def execute(local, url, policy, payload, now=0, crash="none"):
    """Single logical operation per isolated trial. No oracle access by worker."""
    digest = fingerprint(payload)
    with connect(local) as c:
        c.execute("CREATE TABLE IF NOT EXISTS intent(id INTEGER PRIMARY KEY, hash TEXT, started INTEGER, effect INTEGER)")
        old = c.execute("SELECT hash,started,effect FROM intent WHERE id=1").fetchone()
        if old:
            if policy == "guarded" and old[0] != digest:
                return {"status": "conflict", "hash": digest}
            if policy in ("local_receipt", "guarded") and old[2] is not None:
                return {"status": "confirmed", "hash": digest, "effect": old[2], "local": True}
            if policy == "guarded" and now - old[1] >= TTL:
                return {"status": "quarantined", "hash": digest}
        else:
            c.execute("INSERT INTO intent VALUES (1,?,?,NULL)", (digest, now))
        checkpoint("before_send", crash)
        code, result = post(url, "logical-operation-1" if policy in ("keyed", "guarded") else None,
                            payload, now)
        if code != 200:
            return {"status": "conflict" if code == 409 else "error", "hash": digest}
        checkpoint("after_effect", crash)
        c.execute("BEGIN IMMEDIATE")
        c.execute("UPDATE intent SET effect=? WHERE id=1", (result["effect"],))
        checkpoint("before_receipt_commit", crash)
        c.commit()
        checkpoint("after_receipt", crash)
        return {"status": "confirmed", "hash": digest, "effect": result["effect"], "local": False}


def worker(local, url, policy, payload, now, crash):
    started = time.perf_counter()
    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "worker", "--local", str(local),
                           "--url", url, "--policy", policy, "--payload", json.dumps(payload),
                           "--now", str(now), "--crash", crash], capture_output=True, text=True, timeout=15)
    elapsed = time.perf_counter() - started
    expected = CRASH if crash != "none" else 0
    if proc.returncode != expected:
        raise RuntimeError("worker exit %s expected %s: %s" % (proc.returncode, expected, proc.stderr))
    return (json.loads(proc.stdout) if proc.returncode == 0 else {"status": "crashed"}), elapsed


def run_trial(directory, service, policy, scenario, workload, seed):
    trial = "%s-%s-%s-%s" % (workload, seed, scenario, policy)
    local = directory / (trial + ".db")
    # Provider database is shared for server lifetime but cleared between sequential trials.
    with connect(service.server.db) as c:
        c.execute("DELETE FROM effects")
        c.execute("DELETE FROM receipts")
        c.execute("DELETE FROM requests")
    value = random.Random(seed).randint(1, 999)
    payload = {"op": workload, "value": value}
    crash = {"clean": "none", "expired_after_effect": "after_effect",
             "expiry_before_send": "before_send", "changed_retry": "after_receipt"}.get(scenario, scenario)
    initial, elapsed = worker(local, service.url, policy, payload, 0, crash)
    retry = dict(payload)
    if scenario == "changed_retry":
        retry["value"] += 1
    retry_now = 20 if scenario in ("expired_after_effect", "expiry_before_send") else 1
    recovered, duration = worker(local, service.url, policy, retry, retry_now, "none")
    with connect(service.server.db) as c:
        effects = [{"id": r[0], "hash": r[1], "payload": json.loads(r[2])}
                   for r in c.execute("SELECT id,hash,payload FROM effects ORDER BY id")]
        requests = c.execute("SELECT count(*) FROM requests").fetchone()[0]
        provider_ok = c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with connect(local) as c:
        local_ok = c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    false_ack = recovered["status"] == "confirmed" and not any(
        e["id"] == recovered["effect"] and e["hash"] == recovered["hash"] for e in effects)
    return {"trial": trial, "policy": policy, "scenario": scenario, "workload": workload,
            "seed": seed, "original": payload, "retry": retry, "first_status": initial["status"],
            "recovery": recovered, "effects": effects, "effect_count": len(effects),
            "duplicates": max(0, len(effects)-1), "missing": int(not effects),
            "wrong_payload": sum(e["hash"] != fingerprint(payload) for e in effects),
            "false_confirmation": int(false_ack), "requests": requests,
            "process_exits": int(crash != "none"), "integrity_ok": provider_ok and local_ok,
            "wall_seconds": round(elapsed + duration, 6)}


def summarize(rows):
    result = []
    for scenario in SCENARIOS:
        for policy in POLICIES:
            subset = [r for r in rows if r["scenario"] == scenario and r["policy"] == policy]
            if not subset:
                continue
            record = {"scenario": scenario, "policy": policy, "trials": len(subset)}
            for field in ("effect_count", "duplicates", "missing", "wrong_payload", "false_confirmation",
                          "requests", "process_exits"):
                record[field] = sum(r[field] for r in subset)
            for status in ("confirmed", "quarantined", "conflict", "error"):
                record[status] = sum(r["recovery"]["status"] == status for r in subset)
            result.append(record)
    return result


def audit(rows):
    """Fail on experiment/invariant errors; known baseline failures are outcomes."""
    if not rows or len({r["trial"] for r in rows}) != len(rows):
        raise AssertionError("empty or duplicate trials")
    for r in rows:
        if not r["integrity_ok"]:
            raise AssertionError("database integrity failed")
        if r["policy"] == "guarded" and any(r[k] for k in ("duplicates", "wrong_payload", "false_confirmation")):
            raise AssertionError("guarded safety violation")
        if r["policy"] == "guarded" and r["missing"] and r["recovery"]["status"] != "quarantined":
            raise AssertionError("silent loss")
    return True


def run(seeds, output):
    if not 1 <= seeds <= 1000:
        raise ValueError("seeds must be 1..1000")
    rows = []
    with tempfile.TemporaryDirectory(prefix="effect-boundary-") as tmp:
        directory = Path(tmp)
        with Service(directory / "provider.db") as service:
            for workload in WORKLOADS:
                for seed in range(seeds):
                    for scenario in SCENARIOS:
                        for policy in POLICIES:
                            rows.append(run_trial(directory, service, policy, scenario, workload, seed))
                print("completed " + workload, file=sys.stderr, flush=True)
    audit(rows)
    report = {"schema": 1, "study": "Effect Boundary Lab", "seeds": seeds,
              "design": {"policies": list(POLICIES), "scenarios": list(SCENARIOS),
                         "workloads": list(WORKLOADS), "receipt_ttl": TTL, "expired_retry_time": 20,
                         "clock": "virtual integer; not wall-clock timing", "order": "fixed factorial"},
              "environment": {"python": sys.version, "platform": platform.platform(),
                              "sqlite": sqlite3.sqlite_version},
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "trials": rows, "summary": summarize(rows)}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(report["summary"][0]))
        writer.writeheader()
        writer.writerows(report["summary"])
    print(json.dumps({"trials": len(rows), "process_exits": sum(r["process_exits"] for r in rows),
                      "output": str(output), "audit": "passed"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    experiment = sub.add_parser("run")
    experiment.add_argument("--seeds", type=int, default=12)
    experiment.add_argument("--output", default="evidence/results.json")
    child = sub.add_parser("worker")
    child.add_argument("--local", required=True)
    child.add_argument("--url", required=True)
    child.add_argument("--policy", choices=POLICIES, required=True)
    child.add_argument("--payload", required=True)
    child.add_argument("--now", type=int, required=True)
    child.add_argument("--crash", default="none")
    args = parser.parse_args()
    if args.command == "run":
        run(args.seeds, args.output)
    else:
        print(json.dumps(execute(args.local, args.url, args.policy, json.loads(args.payload), args.now, args.crash)))

if __name__ == "__main__":
    main()
