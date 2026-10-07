"""Validação da lista de publicações."""
from downloader import normalize_url


def parse_links(text):
    urls = []
    errors = []
    seen = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            url = normalize_url(line.strip())
        except ValueError as exc:
            errors.append(f'Linha {number}: {exc}')
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    if errors:
        raise ValueError('\n'.join(errors))
    if not urls:
        raise ValueError('Cole pelo menos um link, um por linha.')
    return urls
