"""Abre o navegador instalado e o perfil correto, sem shell."""
import shutil
import subprocess
from pathlib import Path


def open_browser_login(browser, profile=''):
    commands = {
        'chrome': ['google-chrome', 'google-chrome-stable'],
        'chromium': ['chromium', 'chromium-browser'],
        'firefox': ['firefox', 'firefox-esr'],
        'brave': ['brave-browser', 'brave'], 'edge': ['microsoft-edge'],
        'vivaldi': ['vivaldi', 'vivaldi-stable'], 'opera': ['opera'],
    }
    executable = next((shutil.which(c) for c in commands.get(browser, []) if shutil.which(c)), None)
    if not executable:
        raise ValueError('Navegador não encontrado. Selecione um navegador instalado.')
    args = [executable]
    if profile:
        if browser == 'firefox':
            args += ['-profile', str(Path(profile).expanduser())] if Path(profile).expanduser().is_dir() else ['-P', profile]
        else:
            path = Path(profile).expanduser()
            if path.is_dir():
                args += ['--user-data-dir=' + str(path.parent), '--profile-directory=' + path.name]
            else:
                args += ['--profile-directory=' + profile]
    args.append('https://x.com/home')
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
