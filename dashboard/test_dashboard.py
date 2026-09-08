import json
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import threading
import server

class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        server.PORT=cls.http.server_port
        server.ORIGIN=f'http://127.0.0.1:{server.PORT}'
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
    def request(self,path,body=None,origin=None,host=None):
        headers={}
        if body is not None: headers['Content-Type']='application/json'
        if origin: headers['Origin']=origin
        if host: headers['Host']=host
        req=urllib.request.Request(server.ORIGIN+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        return urllib.request.urlopen(req)
    def test_machine_real_metrics(self):
        with self.request('/api/machine') as res: d=json.load(res)
        self.assertGreater(d['ramTotal'],0)
        self.assertLessEqual(d['ramUsed'],d['ramTotal'])
    def test_wanderer_readings_are_a_json_array(self):
        with self.request('/wanderer/readings.json') as res:
            self.assertEqual(res.headers.get_content_type(), 'application/json')
            readings = json.load(res)
        self.assertIsInstance(readings, list)
        self.assertGreater(len(readings), 0)
        for reading in readings:
            self.assertTrue({'title', 'kind', 'topic', 'description', 'source', 'url', 'prompt'} <= reading.keys())
    def test_wanderer_page_and_live_palette(self):
        with self.request('/wanderer/') as res:
            self.assertIn(b'id="machine-theme"', res.read())
        with patch('server.wanderer_theme.stylesheet', return_value=b':root{--background:#123456}'):
            with self.request('/wanderer/theme.css?t=123') as res:
                self.assertEqual(res.headers.get_content_type(), 'text/css')
                self.assertEqual(res.headers['Cache-Control'], 'no-store')
                self.assertIn(b'--background:#123456', res.read())
    def test_cross_origin_action_rejected(self):
        with patch('server.subprocess.Popen') as launch:
            with self.assertRaises(urllib.error.HTTPError) as err:
                self.request('/api/action',{'action':'terminal'},'https://attacker.example')
            self.assertEqual(err.exception.code,403)
            launch.assert_not_called()
    def test_host_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as err: self.request('/api/machine',host='attacker.example')
        self.assertEqual(err.exception.code,403)
    def test_arbitrary_commands_rejected(self):
        with patch('server.subprocess.Popen') as launch:
            with self.assertRaises(urllib.error.HTTPError) as err:
                self.request('/api/action',{'action':'echo injected'},server.ORIGIN)
            self.assertEqual(err.exception.code,400)
            launch.assert_not_called()
    def test_launch_allowlist(self):
        with patch('server.subprocess.Popen') as launch:
            with self.request('/api/action',{'action':'resume'},server.ORIGIN) as res: self.assertTrue(json.load(res)['ok'])
            command=launch.call_args.args[0]
            self.assertEqual(command[-2:],['resume','--all'])
            self.assertIn('--hold',command)
    def test_no_filesystem_traversal(self):
        with self.assertRaises(urllib.error.HTTPError) as err: self.request('/../../server.py')
        self.assertEqual(err.exception.code,404)
    def test_remote_model_rejected(self):
        with patch('server.local_models',return_value={'models':[{'name':'local'}]}):
            with self.assertRaises(urllib.error.HTTPError) as err:
                self.request('/api/chat',{'model':'cloud','messages':[{'role':'user','content':'hello'}]},server.ORIGIN)
            self.assertEqual(err.exception.code,400)
if __name__=='__main__': unittest.main()
