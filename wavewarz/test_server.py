import copy
import json
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
import server

class WaveTests(unittest.TestCase):
    def setUp(self):
        server.CACHE.clear()

    def test_null_winner_never_inferred_from_pool(self):
        row = {'artist1': {'name': 'A', 'poolSol': 100}, 'artist2': {'name': 'B', 'poolSol': 1},
               'winnerSide': None, 'winnerDecided': True, 'type': 'quick'}
        result = server.battle(row)
        self.assertEqual(result['result'], 'No winner recorded')
        self.assertEqual(result['label'], 'Songs')
        row['winnerSide'] = 'artist2'
        self.assertEqual(server.battle(row)['result'], 'Winner: B')
        self.assertEqual(server.battle(row, True)['label'], 'Event')

    def test_cache_retains_data_and_marks_failure_stale(self):
        with patch.object(server, 'fetch', return_value={'usd': 1}) as fetch:
            first = server.cached('example')
            server.cached('example')
            self.assertEqual(fetch.call_count, 1)
        server.CACHE['example']['attempt'] -= 100
        with patch.object(server, 'fetch', side_effect=TimeoutError('offline')) as fetch:
            failed = server.cached('example')
            server.cached('example')
            self.assertEqual(fetch.call_count, 1)
        self.assertTrue(failed['stale'])
        self.assertEqual(failed['data'], first['data'])
        self.assertEqual(failed['fetchedAt'], first['fetchedAt'])

    def test_summary_failure_releases_lock(self):
        server.SUMMARY_LOCK.acquire()
        with patch.object(server, 'wave', return_value={'battles': []}):
            server.summary_worker()
        self.assertEqual(server.SUMMARY['status'], 'error')
        self.assertFalse(server.SUMMARY_LOCK.locked())

    def test_profile_does_not_guess_from_partial_handle(self):
        def fake(url, ttl):
            return {'data': {'artists': [{'name':'0xQuanFan'}]}, 'fetchedAt': None, 'stale': False, 'error': ''}
        with patch.object(server, 'cached', side_effect=fake):
            self.assertIsNone(server.wave()['profile'])

    def test_coin_id_cannot_be_a_url(self):
        with self.assertRaises(ValueError):
            server.prices('http://localhost/')

    def test_http_origin_and_post_protection(self):
        httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(httpd.server_port)
        try:
            with patch.object(server, 'PORT', httpd.server_port):
                with urllib.request.urlopen(base + '/health') as res:
                    self.assertTrue(json.load(res)['ok'])
                req = urllib.request.Request(base + '/summary', data=b'', headers={'Origin':'https://evil.example'})
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(req)
                self.assertEqual(error.exception.code, 403)
        finally:
            httpd.shutdown()
            httpd.server_close()

if __name__ == '__main__':
    unittest.main()
