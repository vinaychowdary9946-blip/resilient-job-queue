"""Durable, leased job queue. Python 3.10+, standard library only."""
import json
import random
import sqlite3
import time
import uuid


class Queue:
    def __init__(self, path='queue.db', clock=time.time):
        self.clock = clock
        self.db = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
        status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL, available REAL NOT NULL,
        token TEXT, expires REAL, error TEXT);
        CREATE INDEX IF NOT EXISTS ready ON jobs(status, available);''')

    def close(self):
        self.db.close()

    def enqueue(self, key, payload, max_attempts=3):
        if not isinstance(key, str) or not key.strip() or type(max_attempts) is not int or not 1 <= max_attempts <= 20:
            raise ValueError('A nonempty key and max_attempts from 1 to 20 are required')
        data = json.dumps(payload, sort_keys=True, allow_nan=False)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT * FROM jobs WHERE key=?', (key,)).fetchone()
            if old:
                if old['payload'] != data or old['max_attempts'] != max_attempts:
                    raise ValueError('Idempotency key reused with different request')
                result = dict(old)
            else:
                ident = str(uuid.uuid4())
                self.db.execute('INSERT INTO jobs(id,key,payload,status,max_attempts,available) VALUES(?,?,?,\'pending\',?,?)', (ident, key, data, max_attempts, self.clock()))
                result = dict(self.db.execute('SELECT * FROM jobs WHERE id=?', (ident,)).fetchone())
            self.db.execute('COMMIT')
            return result
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def claim(self, lease=30):
        if not isinstance(lease, (int, float)) or not 0 < lease <= 3600:
            raise ValueError('Lease must be in (0, 3600] seconds')
        now = self.clock()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute("UPDATE jobs SET status=CASE WHEN attempts>=max_attempts THEN 'dead' ELSE 'pending' END, token=NULL, expires=NULL WHERE status='running' AND expires<=?", (now,))
            row = self.db.execute("SELECT * FROM jobs WHERE status='pending' AND available<=? ORDER BY available,id LIMIT 1", (now,)).fetchone()
            result = None
            if row:
                token = str(uuid.uuid4())
                self.db.execute("UPDATE jobs SET status='running',attempts=attempts+1,token=?,expires=? WHERE id=?", (token, now+lease, row['id']))
                result = dict(self.db.execute('SELECT * FROM jobs WHERE id=?', (row['id'],)).fetchone())
            self.db.execute('COMMIT')
            return result
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def finish(self, ident, token, error=None):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute("SELECT * FROM jobs WHERE id=? AND token=? AND status='running' AND expires>?", (ident, token, self.clock())).fetchone()
            if not row:
                raise ValueError('Lease expired or token is stale')
            state = 'done' if error is None else ('dead' if row['attempts'] >= row['max_attempts'] else 'pending')
            delay = random.uniform(0, min(60, 2 ** row['attempts'])) if error else 0
            self.db.execute('UPDATE jobs SET status=?,available=?,token=NULL,expires=NULL,error=? WHERE id=?', (state, self.clock()+delay, str(error)[:1000] if error else None, ident))
            self.db.execute('COMMIT')
            return state
        except Exception:
            self.db.execute('ROLLBACK')
            raise

    def jobs(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM jobs ORDER BY available,id')]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='queue.db')
    parser.add_argument('action', choices=['enqueue', 'work', 'list'])
    parser.add_argument('--key', default='sample-report')
    parser.add_argument('--payload', default='{"report":"daily-sales"}')
    args = parser.parse_args()
    q = Queue(args.db)
    try:
        if args.action == 'enqueue':
            print(json.dumps(q.enqueue(args.key, json.loads(args.payload)), indent=2))
        elif args.action == 'work':
            job = q.claim()
            if job:
                # Deliberately safe sample handler: no external side effects.
                print('Processed:', json.loads(job['payload']))
                q.finish(job['id'], job['token'])
            else:
                print('No available jobs')
        else:
            print(json.dumps(q.jobs(), indent=2))
    finally:
        q.close()
