import unittest
import urllib.request
from downloader import normalize_url, validate_network_url, DomainGuard, LocalDownloader

class SecurityTests(unittest.TestCase):
    def test_status(self):
        self.assertEqual(normalize_url('https://twitter.com/person/status/123/video/1?s=20'), 'https://x.com/i/status/123')
    def test_rejected(self):
        for url in ['http://x.com/a/status/1', 'https://x.com.evil.org/a/status/1',
                    'https://evil.org/a/status/1', 'https://x.com/home',
                    'https://user:pass@x.com/a/status/1', 'https://x.com:444/a/status/1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_url(url)
    def test_media(self):
        validate_network_url('https://video.twimg.com/video.mp4')
    def test_redirect_guard(self):
        with self.assertRaises(ValueError):
            DomainGuard().https_request(urllib.request.Request('https://external.example/video'))
    def test_backend(self):
        with LocalDownloader({'quiet': True, 'proxy': ''}) as ydl:
            self.assertEqual(list(ydl._request_director.handlers), ['XOnlyUrllib'])
            with self.assertRaises(ValueError):
                ydl.urlopen('https://external.example/video')

if __name__ == '__main__':
    unittest.main()
