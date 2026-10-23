import unittest, tempfile, os
from concurrent.futures import ThreadPoolExecutor
from queue_engine import Queue
class QueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.path=os.path.join(self.tmp.name,'q.db'); self.now=100; self.q=Queue(self.path,lambda:self.now)
 def tearDown(self): self.q.close(); self.tmp.cleanup()
 def test_idempotent(self):
  a=self.q.enqueue('a',{'x':1}); self.assertEqual(a['id'],self.q.enqueue('a',{'x':1})['id'])
  with self.assertRaises(ValueError): self.q.enqueue('a',{'x':2})
 def test_lease_and_stale_worker(self):
  self.q.enqueue('a',{}); first=self.q.claim(1); self.now=102; second=self.q.claim()
  with self.assertRaises(ValueError): self.q.finish(first['id'],first['token'])
  self.assertEqual(self.q.finish(second['id'],second['token']),'done')
 def test_retry_and_dead_letter(self):
  self.q.enqueue('a',{},2); a=self.q.claim(); self.assertEqual(self.q.finish(a['id'],a['token'],'timeout'),'pending'); self.assertIsNone(self.q.claim())
  self.now=200; a=self.q.claim(); self.assertEqual(self.q.finish(a['id'],a['token'],'timeout'),'dead')
 def test_expired_final_attempt(self):
  self.q.enqueue('a',{},1); self.q.claim(1); self.now=102; self.assertIsNone(self.q.claim()); self.assertEqual(self.q.jobs()[0]['status'],'dead')
 def test_restart(self):
  self.q.enqueue('a',{}); self.q.close(); self.q=Queue(self.path,lambda:self.now); self.assertIsNotNone(self.q.claim())
 def test_concurrent_claim(self):
  for i in range(30): self.q.enqueue(str(i),{})
  def run(_):
   q=Queue(self.path,lambda:100)
   try: return q.claim()['id']
   finally: q.close()
  with ThreadPoolExecutor(max_workers=6) as pool: ids=list(pool.map(run,range(30)))
  self.assertEqual(len(set(ids)),30)
 def test_validation(self):
  for key,attempts in [('',3),('a',0),('a',True)]:
   with self.assertRaises(ValueError): self.q.enqueue(key,{},attempts)
 def test_empty_error_still_has_backoff(self):
  from unittest.mock import patch
  self.q.enqueue('a',{}); job=self.q.claim()
  with patch('queue_engine.random.uniform', return_value=1):
   self.q.finish(job['id'],job['token'],'')
  self.assertEqual(self.q.jobs()[0]['available'],101)
  self.assertEqual(self.q.jobs()[0]['error'],'')
 def test_bool_lease_rejected(self):
  with self.assertRaises(ValueError): self.q.claim(True)
 def test_report_replay_after_lease_recovery(self):
  self.q.enqueue('a',{'x':1}); job=self.q.claim(1)
  result=self.q.apply_local_report(job['id'],job['token'])
  self.now=102; retry=self.q.claim()
  self.assertEqual(result,self.q.apply_local_report(retry['id'],retry['token']))
  self.assertEqual(len(self.q.reports()),1)
 def test_report_rejects_stale_worker(self):
  self.q.enqueue('a',{}); job=self.q.claim(1); self.now=102
  with self.assertRaises(ValueError): self.q.apply_local_report(job['id'],job['token'])
  self.assertEqual(self.q.reports(),[])
 def test_report_rollback_keeps_receipt_consistent(self):
  self.q.enqueue('a',{}); job=self.q.claim()
  def fail(_): raise RuntimeError('injected exception')
  with self.assertRaises(RuntimeError): self.q.apply_local_report(job['id'],job['token'],_fault=fail)
  self.assertEqual(self.q.reports(),[])
  self.assertEqual(self.q.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],0)
  self.q.apply_local_report(job['id'],job['token'])
  self.assertEqual(len(self.q.reports()),1)
if __name__=='__main__': unittest.main()
