import unittest,threading,json,tempfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import server
class APITests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(); cls.old=server.ROOT; server.ROOT=Path(cls.tmp.name)
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler); cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True); cls.thread.start(); cls.url='http://127.0.0.1:'+str(cls.http.server_port)+'/api'
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown(); cls.http.server_close(); cls.thread.join(); server.ROOT=cls.old; cls.tmp.cleanup()
 def test_domain_request(self):
  data={'action': 'enqueue', 'key': 'report-001', 'payload': {'report': 'daily-sales'}}
  req=Request(self.url,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
  with urlopen(req) as response: self.assertEqual(response.status,200); self.assertTrue(json.load(response))
 def test_invalid_action(self):
  with self.assertRaises(HTTPError) as cm: urlopen(Request(self.url,data=b'{"action":"invalid"}'))
  self.assertEqual(cm.exception.code,400)
 def test_foreign_origin(self):
  with self.assertRaises(HTTPError) as cm: urlopen(Request(self.url,data=b'{}',headers={'Origin':'https://example.com'}))
  self.assertEqual(cm.exception.code,403)
