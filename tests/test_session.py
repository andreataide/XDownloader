import time
import unittest
from http.cookiejar import Cookie
from unittest.mock import patch, ANY
from session import x_cookies, has_session, load_session

def cookie(name, domain='.x.com', expires=None):
    return Cookie(0, name, 'test-value', None, False, domain, True, True,
                  '/', True, True, expires, expires is None, None, None, {}, False)

class SessionTests(unittest.TestCase):
    def test_real_extractor_scope(self):
        self.assertTrue(has_session(x_cookies([cookie('auth_token'), cookie('ct0')])))
    def test_legacy_domain_works_on_current_api(self):
        jar = x_cookies([cookie('auth_token', '.twitter.com'), cookie('ct0', '.twitter.com')])
        self.assertTrue(has_session(jar))
    def test_missing_expired_external(self):
        self.assertFalse(has_session(x_cookies([cookie('auth_token')])))
        self.assertFalse(has_session(x_cookies([cookie('auth_token', expires=int(time.time()) - 20), cookie('ct0')])))
        self.assertFalse(has_session(x_cookies([cookie('auth_token', '.other.com'), cookie('ct0')])))
    def test_profile_and_browser(self):
        with patch('session.extract_cookies_from_browser', return_value=[cookie('auth_token'), cookie('ct0')]) as read:
            self.assertTrue(has_session(load_session('chrome', profile='Profile 2')))
            read.assert_called_once_with('chrome', 'Profile 2', logger=ANY)
    def test_auto_tries_profile_with_login(self):
        from pathlib import Path
        profiles = [Path('/tmp/Profile 1'), Path('/tmp/Default')]
        def extract(browser, profile, **kwargs):
            return [cookie('auth_token'), cookie('ct0')] if profile.endswith('Default') else []
        with patch('session.discover_profiles', return_value=profiles), patch('session.session_cookie_names', side_effect=lambda p: {'auth_token', 'ct0'} if p.name == 'Default' else set()), patch('session.extract_cookies_from_browser', side_effect=extract) as read:
            self.assertTrue(has_session(load_session('chrome')))
            self.assertEqual(read.call_args.args[1], '/tmp/Default')
    def test_no_silent_guest_fallback(self):
        with patch('session.extract_cookies_from_browser', return_value=[]):
            with self.assertRaises(ValueError):
                load_session('chrome')

if __name__ == '__main__':
    unittest.main()
