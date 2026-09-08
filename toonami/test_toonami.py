import datetime as dt
import unittest
from unittest.mock import patch
import toonami
import windowing

class GuideTests(unittest.TestCase):
    def test_mini_geometry_accounts_for_scale_bar_and_negative_monitor(self):
        monitor = dict(width=1920, height=1200, scale=1.25, x=-1536, y=0, reserved=[0,24,0,0])
        self.assertEqual(windowing.geometry(monitor,320,'bottom-right'), (320,240,-336,704))
        self.assertEqual(windowing.geometry(monitor,320,'top-left'), (320,240,-1520,40))
        monitor.update(width=300, height=400, scale=1, transform=1)
        w,h,x,y = windowing.geometry(monitor,640,'bottom-right')
        self.assertLessEqual(w,368)
        self.assertLessEqual(h,244)

    def test_current_and_next_use_actual_start_times(self):
        data = [{'name': 'Toonami Aftermath East', 'media': [
            {'name': 'Next', 'startDate': '2026-09-08T10:30:00Z'},
            {'name': 'Current', 'startDate': '2026-09-08T10:00:00Z'},
            {'name': 'Old', 'startDate': '2026-09-08T09:30:00Z'}]}]
        row = toonami.guide_rows(data, dt.datetime(2026, 9, 8, 10, 15, tzinfo=dt.timezone.utc))[0]
        self.assertEqual(row['now'], 'Current')
        self.assertIn('Next', row['next'])

    def test_west_requests_delay_and_rejects_untrusted_stream(self):
        with patch.object(toonami, 'fetch', return_value='https://asp10.toonamiaftermath.com/live/test.m3u8') as fetch:
            toonami.stream_url(toonami.STATIONS[1])
            self.assertIn('streamDelay=180', fetch.call_args.args[0])
            self.assertIn('channelName=est', fetch.call_args.args[0])
        with patch.object(toonami, 'fetch', return_value='file:///tmp/test.m3u8'):
            with self.assertRaises(RuntimeError): toonami.stream_url(toonami.STATIONS[0])

if __name__ == '__main__': unittest.main()
