import concurrent.futures
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import lab
import verify

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "provider.db"
        lab.init_provider(self.db)
        self.payload = {"op": "payment", "value": 10}
    def tearDown(self):
        self.tmp.cleanup()
    def test_atomic_key_replay(self):
        first = lab.apply_effect(self.db, "x", self.payload, 0)
        again = lab.apply_effect(self.db, "x", self.payload, 1)
        self.assertEqual(first[1]["effect"], again[1]["effect"])
        self.assertTrue(again[1]["replayed"])
    def test_payload_binding(self):
        lab.apply_effect(self.db, "x", self.payload, 0)
        self.assertEqual(lab.apply_effect(self.db, "x", {**self.payload, "value": 11}, 1)[0], 409)
    def test_expiry_boundary(self):
        lab.apply_effect(self.db, "x", self.payload, 0)
        self.assertTrue(lab.apply_effect(self.db, "x", self.payload, 9)[1]["replayed"])
        self.assertFalse(lab.apply_effect(self.db, "x", self.payload, 10)[1]["replayed"])
    def test_canonical_hash(self):
        self.assertEqual(lab.fingerprint(self.payload), lab.fingerprint({"value": 10, "op": "payment"}))
    def test_distinct_intents_identical_payload(self):
        a = lab.apply_effect(self.db, "a", self.payload, 0)
        b = lab.apply_effect(self.db, "b", self.payload, 0)
        self.assertNotEqual(a[1]["effect"], b[1]["effect"])
    def test_parallel_destination_key(self):
        with lab.Service(self.db) as service:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: lab.post(service.url, "x", self.payload, 0), range(16)))
        self.assertTrue(all(r[0] == 200 for r in results))
        self.assertEqual(len({r[1]["effect"] for r in results}), 1)
    def test_malformed_http(self):
        with lab.Service(self.db) as service:
            req = Request(service.url, data=b"{", method="POST")
            with self.assertRaises(HTTPError) as error:
                urlopen(req, timeout=5)
            self.assertEqual(error.exception.code, 400)
    def test_bool_not_integer(self):
        with lab.Service(self.db) as service:
            code, _ = lab.post(service.url, "x", {"op": "stock", "value": True}, 0)
            self.assertEqual(code, 400)
    def test_unknown_route(self):
        with lab.Service(self.db) as service:
            self.assertEqual(lab.post(service.url + "/wrong", "x", self.payload, 0)[0], 404)
    def test_guard_conflict_after_confirmation(self):
        with lab.Service(self.db) as service:
            local = self.root / "client.db"
            lab.execute(local, service.url, "guarded", self.payload)
            result = lab.execute(local, service.url, "guarded", {**self.payload, "value": 11}, 1)
            self.assertEqual(result["status"], "conflict")
    def test_guard_completed_receipt_survives_horizon(self):
        with lab.Service(self.db) as service:
            local = self.root / "client.db"
            first = lab.execute(local, service.url, "guarded", self.payload)
            second = lab.execute(local, service.url, "guarded", self.payload, 20)
            self.assertEqual(first["effect"], second["effect"])
    def test_full_fault_matrix_real_processes(self):
        rows = []
        with lab.Service(self.db) as service:
            for scenario in lab.SCENARIOS:
                for policy in lab.POLICIES:
                    with self.subTest(scenario=scenario, policy=policy):
                        row = lab.run_trial(self.root, service, policy, scenario, "payment", 999)
                        rows.append(row)
                        expected = ({"naive": 2, "local_receipt": 2, "keyed": 2, "guarded": 1}
                                    if scenario == "expired_after_effect" else
                                    {"naive": 1, "local_receipt": 1, "keyed": 1, "guarded": 0}
                                    if scenario == "expiry_before_send" else
                                    {"naive": 1, "local_receipt": 1, "keyed": 1, "guarded": 1}
                                    if scenario == "before_send" else
                                    {"naive": 2, "local_receipt": 2, "keyed": 1, "guarded": 1}
                                    if scenario in ("after_effect", "before_receipt_commit") else
                                    {"naive": 2, "local_receipt": 1, "keyed": 1, "guarded": 1})
                        self.assertEqual(row["effect_count"], expected[policy])
                        self.assertEqual(row["false_confirmation"], int(scenario == "changed_retry" and policy == "local_receipt"))
        self.assertTrue(lab.audit(rows))
    def test_evidence_and_independent_verifier(self):
        evidence = Path(__file__).parent / "evidence/results.json"
        if not evidence.exists():
            self.skipTest("full evidence is produced by lab.py run")
        self.assertEqual(verify.verify(evidence)["groups"], 32)
    def test_paired_witness(self):
        import witness
        result = witness.produce()
        self.assertEqual(result['histories'][0]['durable_client_state'], result['histories'][1]['durable_client_state'])
        self.assertEqual([h['remote_effect_count'] for h in result['histories']], [0, 1])
    def test_verifier_rejects_tampering(self):
        evidence = Path(__file__).parent / "evidence/results.json"
        if not evidence.exists():
            self.skipTest("full evidence is produced by lab.py run")
        data = json.loads(evidence.read_text())
        data["trials"][0]["effect_count"] += 1
        path = self.root / "tampered.json"
        path.write_text(json.dumps(data))
        with self.assertRaises(AssertionError):
            verify.verify(path)

if __name__ == "__main__":
    unittest.main()
