"""Importação local de sessão, sem registrar valores de credenciais."""
import copy
import time
from pathlib import Path
import sqlite3
from http.cookiejar import MozillaCookieJar
from yt_dlp.cookies import extract_cookies_from_browser
from yt_dlp.utils import YoutubeDLCookieJar


def x_cookies(cookies):
    jar = YoutubeDLCookieJar()
    now = time.time()
    for cookie in cookies:
        domain = cookie.domain.lstrip('.').lower()
        if domain not in ('x.com', 'twitter.com') or (cookie.expires and cookie.expires <= now):
            continue
        jar.set_cookie(copy.copy(cookie))
        if domain == 'twitter.com':
            alias = copy.copy(cookie)
            alias.domain = '.x.com'
            alias.domain_specified = True
            alias.domain_initial_dot = True
            jar.set_cookie(alias)
    return jar


def has_session(jar):
    # Check the actual cookie scope used by the extractor, not just cookie names.
    from yt_dlp.extractor.twitter import TwitterBaseIE
    from downloader import LocalDownloader
    with LocalDownloader({'quiet': True, 'proxy': ''}) as ydl:
        ydl.__dict__['cookiejar'] = jar
        ie = TwitterBaseIE(ydl)
        cookies = ie._get_cookies(ie._API_BASE)
        return all(cookies.get(name) and cookies[name].value for name in ('auth_token', 'ct0'))


def discover_profiles(browser):
    roots = {
        'chrome': ['.config/google-chrome'],
        'chromium': ['.config/chromium', 'snap/chromium/common/chromium'],
        'brave': ['.config/BraveSoftware/Brave-Browser'],
        'edge': ['.config/microsoft-edge'],
        'firefox': ['.mozilla/firefox', 'snap/firefox/common/.mozilla/firefox',
                    '.var/app/org.mozilla.firefox/.mozilla/firefox'],
        'vivaldi': ['.config/vivaldi'], 'opera': ['.config/opera'],
    }
    profiles = []
    for root in roots.get(browser, []):
        directory = Path.home() / root
        if not directory.is_dir():
            continue
        for profile in [directory, *sorted(directory.iterdir())]:
            if profile.is_dir() and any((profile / f).is_file() for f in ('Cookies', 'Network/Cookies', 'cookies.sqlite')):
                profiles.append(profile)
    return profiles


def session_cookie_names(profile):
    """Profile discovery reads cookie names only, never encrypted values."""
    for name in ('Network/Cookies', 'Cookies', 'cookies.sqlite'):
        database = Path(profile) / name
        if not database.is_file():
            continue
        table, host = ('moz_cookies', 'host') if name == 'cookies.sqlite' else ('cookies', 'host_key')
        try:
            with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=1) as db:
                return {row[0] for row in db.execute(
                    f"SELECT name FROM {table} WHERE {host} IN ('.x.com','x.com','.twitter.com','twitter.com') "
                    "AND name IN ('auth_token','ct0')")}
        except sqlite3.Error:
            continue
    return set()


class SessionLogger:
    def debug(self, *_, **kwargs): pass
    def info(self, *_, **kwargs): pass
    def warning(self, *_, **kwargs): pass
    def error(self, *_, **kwargs): pass


def load_session(browser, cookie_file='', profile=''):
    if cookie_file:
        cookies = MozillaCookieJar(cookie_file)
        cookies.load(ignore_discard=True, ignore_expires=True)
        jar = x_cookies(cookies)
        if has_session(jar):
            return jar
        raise ValueError('Arquivo sem sessão utilizável do X. Exporte novamente da conta autenticada.')
    if browser == 'Sem sessão':
        raise ValueError('Selecione o navegador onde você está logado.')
    candidates = [profile] if profile else discover_profiles(browser)
    if not candidates:
        candidates = [None]
    # Prefer profiles containing the two required names, then try the remaining ones.
    if not profile:
        candidates.sort(key=lambda p: not {'auth_token', 'ct0'}.issubset(session_cookie_names(p)) if p else True)
    failures = 0
    encrypted_session_found = False
    for candidate in candidates:
        try:
            if candidate and Path(candidate).is_dir():
                encrypted_session_found |= {'auth_token', 'ct0'}.issubset(session_cookie_names(candidate))
            cookies = extract_cookies_from_browser(browser, str(candidate) if candidate else None,
                                                  logger=SessionLogger())
            jar = x_cookies(cookies)
            if has_session(jar):
                return jar
        except Exception:
            failures += 1
    if failures or encrypted_session_found:
        raise ValueError('Não foi possível ler/descriptografar a sessão. Feche o navegador e tente novamente; '
                         'se persistir, importe cookies.txt da conta autenticada.')
    raise ValueError('Nenhum perfil selecionado contém uma sessão utilizável do X. '
                     'Escolha outro perfil, entre no X nesse perfil e verifique novamente.')
