"""Reproducible process-crash experiment; no services or third-party packages.

Run: python crash_lab.py --jobs 20 --output evidence/crash-results.json
Workers call os._exit(73), leaving SQLite to recover uncommitted writes.
The virtual lease clock avoids sleeps; the process exits and database writes
are real. This is not a power-loss or distributed-system test.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

from queue_engine import Queue

STAGES = ('before_effect', 'before_commit', 'after_commit', 'after_ack')


def worker(database, mode, stage, now):
    queue = Queue(database, clock=lambda: now)
    job = queue.claim(lease=1)
    if not job:
        raise RuntimeError('Experiment worker found no job')
    if stage == 'before_effect':
        os._exit(73)

    def fault(point):
        if point == stage:
            os._exit(73)

    if mode == 'protected':
        queue.apply_local_report(job['id'], job['token'], _fault=fault)
    else:
        # Control condition: same queue, same report table, no dedup receipt.
        # It intentionally commits the side effect separately from acknowledgment.
        queue.db.execute('BEGIN IMMEDIATE')
        queue.db.execute(
            'INSERT INTO reports(job_id,report_json) VALUES(?,?)',
            (job['id'], json.dumps({'input': json.loads(job['payload'])})),
        )
        fault('before_commit')
        queue.db.execute('COMMIT')
        fault('after_commit')
    queue.finish(job['id'], job['token'])
    if stage == 'after_ack':
        os._exit(73)
    queue.close()


def experiment(jobs=20):
    if type(jobs) is not int or not 1 <= jobs <= 500:
        raise ValueError('jobs must be from 1 to 500')
    evidence = []
    script = str(Path(__file__).resolve())
    with tempfile.TemporaryDirectory(prefix='queue-crash-lab-') as folder:
        for mode in ('unprotected', 'protected'):
            for stage in STAGES:
                database = str(Path(folder) / (mode + '-' + stage + '.db'))
                queue = Queue(database, clock=lambda: 0)
                # Each worker takes one job. Retried jobs are recovered only
                # after all initial crashes have happened, at virtual time 2.
                for index in range(jobs):
                    queue.enqueue(f'report-{index:04}', {'region': index}, 3)
                queue.close()
                crashes = []
                for _ in range(jobs):
                    process = subprocess.run(
                        [sys.executable, script, '--worker', database, mode, stage, '0'],
                        capture_output=True, text=True, timeout=15,
                    )
                    if process.returncode != 73:
                        raise RuntimeError(f'Worker did not reach crash point: {process.stderr}')
                    crashes.append(process.returncode)
                recovered = Queue(database, clock=lambda: 2)
                while True:
                    job = recovered.claim(lease=30)
                    if not job:
                        break
                    if mode == 'protected':
                        recovered.apply_local_report(job['id'], job['token'])
                    else:
                        recovered.db.execute(
                            'INSERT INTO reports(job_id,report_json) VALUES(?,?)',
                            (job['id'], json.dumps({'input': json.loads(job['payload'])})),
                        )
                    recovered.finish(job['id'], job['token'])
                rows = recovered.jobs()
                reports = recovered.reports()
                counts = Counter(row['job_id'] for row in reports)
                details = [
                    {'key': row['key'], 'attempts': row['attempts'],
                     'status': row['status'], 'effects': counts[row['id']]}
                    for row in sorted(rows, key=lambda row: row['key'])
                ]
                evidence.append({
                    'mode': mode, 'crash_point': stage, 'submitted': jobs,
                    'process_crashes': len(crashes),
                    'completed': sum(row['status'] == 'done' for row in rows),
                    'business_effects': len(reports),
                    'duplicate_effects': sum(max(0, n - 1) for n in counts.values()),
                    'missing_effects': sum(counts[row['id']] == 0 for row in rows),
                    'database_integrity': recovered.db.execute('PRAGMA integrity_check').fetchone()[0],
                    'jobs': details,
                })
                recovered.close()
    return {
        'schema_version': 1,
        'experiment': 'Local report side effects under process termination',
        'python': platform.python_version(), 'platform': platform.system(),
        'jobs_per_scenario': jobs, 'scenarios': evidence,
        'source_sha256': {
            filename: hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest()
            for filename in ('queue_engine.py', 'crash_lab.py')
        },
        'scope': 'Single SQLite database; real child process exits; virtual lease time; synthetic reports. Not a power-loss, external API, throughput, or globally exactly-once guarantee.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    # Internal worker arguments are parsed separately to keep the public CLI simple.
    if len(sys.argv) > 1 and sys.argv[1] == '--worker':
        worker(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]))
    else:
        parser.add_argument('--jobs', type=int, default=20)
        parser.add_argument('--output', default='evidence/crash-results.json')
        args = parser.parse_args()
        report = experiment(args.jobs)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('Mode          Crash point      Done   Effects   Duplicates   Missing')
        for scenario in report['scenarios']:
            print(f"{scenario['mode']:13} {scenario['crash_point']:16} {scenario['completed']:4} {scenario['business_effects']:9} {scenario['duplicate_effects']:12} {scenario['missing_effects']:9}")
        print('Evidence:', path)
