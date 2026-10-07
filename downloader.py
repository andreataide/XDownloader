"""Downloads locais: somente X/Twitter e sua infraestrutura de mídia."""
from pathlib import Path
import re
from urllib.parse import urlsplit
from yt_dlp import YoutubeDL
from yt_dlp.networking.common import RequestDirector
from yt_dlp.networking._urllib import UrllibRH
from urllib.request import BaseHandler

ALLOWED = ('x.com', 'twitter.com', 'twimg.com')

def validate_network_url(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Somente conexões HTTPS padrão são permitidas.')
    if not any(host == domain or host.endswith('.' + domain) for domain in ALLOWED):
        raise ValueError('Conexão bloqueada: domínio externo ao X.')

def normalize_url(url):
    validate_network_url(url)
    parsed = urlsplit(url)
    if parsed.hostname not in ('x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'):
        raise ValueError('Cole o endereço de uma publicação do X.')
    match = re.fullmatch(r'/(?:[A-Za-z0-9_]+/status|i/status)/(\d+)(?:/video/\d+)?/?', parsed.path)
    if not match:
        raise ValueError('URL inválida. Exemplo: https://x.com/usuario/status/123456789')
    return 'https://x.com/i/status/' + match.group(1)

class XOnlyDirector(RequestDirector):
    def send(self, request):
        validate_network_url(request.url)
        return super().send(request)

class DomainGuard(BaseHandler):
    handler_order = 0
    def https_request(self, request):
        validate_network_url(request.full_url)
        return request
    http_request = https_request

class XOnlyUrllibRH(UrllibRH):
    def _create_instance(self, *args, **kwargs):
        opener = super()._create_instance(*args, **kwargs)
        opener.add_handler(DomainGuard())
        return opener

class LocalDownloader(YoutubeDL):
    def build_request_director(self, handlers, preferences=None):
        # A single local HTTP backend; validates every request and redirect.
        director = super().build_request_director([XOnlyUrllibRH], set())
        director.__class__ = XOnlyDirector
        return director


def download(url, destination, browser, cookie_file, progress, log, cancelled, session=None):
    url = normalize_url(url)
    Path(destination).mkdir(parents=True, exist_ok=True)
    class Logger:
        def debug(self, message):
            if not message.startswith('[debug]'):
                log(message)
        info = debug
        warning = debug
        error = debug
    def hook(data):
        if cancelled():
            raise RuntimeError('Download cancelado. Arquivos parciais podem ser retomados.')
        progress(data)
    options = {
        'format': 'best',
        'outtmpl': str(Path(destination) / '%(id)s_%(playlist_index|0)s.%(ext)s'),
        'logger': Logger(), 'progress_hooks': [hook],
        'continuedl': True, 'overwrites': False, 'noplaylist': False,
        'retries': 3, 'socket_timeout': 25, 'proxy': '',
        'extractor_args': {'twitter': {'api': ['graphql']}},
        'allowed_extractors': ['Twitter', 'TwitterCard'],
        'hls_prefer_native': True,
    }
    with LocalDownloader(options) as ydl:
        if session is not None:
            from session import has_session
            if not has_session(session):
                raise ValueError('A sessão deixou de estar disponível. Verifique o login novamente.')
            ydl.__dict__['cookiejar'] = session
        elif cookie_file or browser != 'Sem sessão':
            from session import load_session
            ydl.__dict__['cookiejar'] = load_session(browser, cookie_file)
        ydl.download([url])
