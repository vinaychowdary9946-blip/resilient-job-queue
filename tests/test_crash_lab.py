import unittest
from crash_lab import experiment


class ProcessCrashTests(unittest.TestCase):
    def test_real_process_crashes_and_recovery(self):
        result = experiment(jobs=2)
        for row in result['scenarios']:
            with self.subTest(mode=row['mode'], point=row['crash_point']):
                self.assertEqual(row['process_crashes'], 2)
                self.assertEqual(row['completed'], 2)
                self.assertEqual(row['missing_effects'], 0)
                self.assertEqual(row['database_integrity'], 'ok')
                expected = 2 if row['mode'] == 'unprotected' and row['crash_point'] == 'after_commit' else 0
                self.assertEqual(row['duplicate_effects'], expected)
                self.assertEqual(row['business_effects'], 2 + expected)
