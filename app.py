import sys
import threading
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QFileDialog, QProgressBar, QPlainTextEdit, QMessageBox, QTabWidget)
from downloader import download, normalize_url, LocalDownloader
from batch import parse_links
from session import load_session, has_session, discover_profiles, session_cookie_names

class Worker(QThread):
    message = Signal(str)
    percent = Signal(int)
    queue_progress = Signal(int, int)
    result = Signal(bool, str)
    def __init__(self, urls, destination, session=None):
        super().__init__()
        self.urls = urls
        self.destination = destination
        self.session = session
        self.stop = threading.Event()
    def run(self):
        successes = failures = processed = 0
        total = len(self.urls)
        def progress(data):
            size = data.get('total_bytes') or data.get('total_bytes_estimate')
            if size:
                self.percent.emit(int(data.get('downloaded_bytes', 0) * 100 / size))
            if data.get('status') == 'finished':
                self.message.emit('Vídeo salvo: ' + data.get('filename', ''))
        self.queue_progress.emit(0, total)
        for index, url in enumerate(self.urls, 1):
            if self.stop.is_set():
                break
            self.percent.emit(0)
            self.message.emit(f'[{index}/{total}] {url}')
            try:
                download(url, self.destination, 'Sem sessão', '', progress,
                         self.message.emit, self.stop.is_set, session=self.session)
            except Exception as exc:
                if self.stop.is_set():
                    break
                failures += 1
                self.message.emit(f'Falhou: {url} — {exc}')
            else:
                successes += 1
                self.percent.emit(100)
            processed += 1
            self.queue_progress.emit(processed, total)
        cancelled = self.stop.is_set()
        status = 'Lote cancelado' if cancelled else 'Fila concluída'
        self.result.emit(not cancelled and failures == 0,
                         f'{status}: {successes} publicações baixadas, {failures} falhas, '
                         f'{total - processed} não processadas.')

class SessionWorker(QThread):
    result = Signal(object, str)
    def __init__(self, browser, cookie_file, profile, url, session=None):
        super().__init__()
        self.args = (browser, cookie_file, profile)
        self.url = url
        self.session = session
    def run(self):
        try:
            jar = self.session if self.session is not None else load_session(*self.args)
            if not has_session(jar):
                raise ValueError('Não há cookies de sessão utilizáveis.')
            message = 'Cookies de sessão reconhecidos. Cole uma publicação para verificar o acesso no X.'
            if self.url:
                with LocalDownloader({'quiet': True, 'no_warnings': True, 'proxy': '',
                                      'socket_timeout': 20, 'skip_download': True,
                                      'allowed_extractors': ['Twitter', 'TwitterCard']}) as ydl:
                    ydl.__dict__['cookiejar'] = jar
                    ydl.extract_info(normalize_url(self.url), download=False)
                message = 'Sessão carregada e acesso à publicação confirmado pelo X.'
            self.result.emit(jar, message)
        except Exception as exc:
            self.result.emit(None, 'Não foi possível verificar a sessão/acesso: ' + str(exc))

class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.session = None
        self.session_revision = 0
        self.checker = None
        self.login_window = None
        self.setWindowTitle('XDownloader — local')
        self.resize(780, 820)
        layout = QVBoxLayout(self)
        title = QLabel('XDownloader')
        title.setStyleSheet('font-size: 28px; font-weight: bold')
        layout.addWidget(title)
        layout.addWidget(QLabel('Vídeos do X • melhor qualidade disponível • processamento local'))
        self.url = QLineEdit()
        self.url.setPlaceholderText('https://x.com/usuario/status/…')
        self.tabs = QTabWidget()
        single = QWidget()
        single_layout = QVBoxLayout(single)
        single_layout.addWidget(self.url)
        self.tabs.addTab(single, 'Um link')
        self.batch_links = QPlainTextEdit()
        self.batch_links.setPlaceholderText('Cole um link por linha:\nhttps://x.com/usuario/status/123\nhttps://x.com/usuario/status/456')
        self.batch_links.setMaximumHeight(150)
        self.tabs.addTab(self.batch_links, 'Baixar em lote')
        layout.addWidget(self.tabs)
        layout.addWidget(QLabel('Links repetidos são removidos. Se um falhar, a fila continua.'))
        self.folder = QLineEdit(str(Path.home() / 'Downloads' / 'XDownloader'))
        row = QHBoxLayout()
        row.addWidget(self.folder)
        choose = QPushButton('Escolher pasta')
        choose.clicked.connect(self.choose_folder)
        row.addWidget(choose)
        layout.addWidget(QLabel('Salvar em'))
        layout.addLayout(row)
        self.browser = QComboBox()
        self.browser.addItems(['Sem sessão', 'firefox', 'chrome', 'chromium', 'brave', 'edge', 'opera', 'vivaldi', 'safari'])
        layout.addWidget(QLabel('Usar sessão autenticada do navegador'))
        layout.addWidget(self.browser)
        self.browser.setCurrentText('chrome')
        self.profile_path = QLineEdit()
        self.profile_path.setPlaceholderText('Perfil opcional: Default, Profile 1 ou caminho do perfil Firefox')
        layout.addWidget(self.profile_path)
        self.profiles = QComboBox()
        layout.addWidget(self.profiles)
        self.profiles.currentIndexChanged.connect(self.select_profile)
        self.browser.currentTextChanged.connect(self.refresh_profiles)
        self.session_status = QLabel('Sessão ainda não verificada.')
        self.session_status.setWordWrap(True)
        layout.addWidget(self.session_status)
        row = QHBoxLayout()
        self.check = QPushButton('Verificar sessão / acesso ao vídeo')
        self.check.clicked.connect(self.check_session)
        row.addWidget(self.check)
        login = QPushButton('Abrir X no perfil selecionado')
        login.clicked.connect(self.open_login)
        row.addWidget(login)
        layout.addLayout(row)
        hint = QLabel('Entre no X pelo navegador selecionado e conclua a verificação exigida pelo X.\n'
                      'A conta precisa conseguir assistir ao vídeo. Feche o navegador se a leitura da sessão falhar.\n'
                      'Escolha um perfil com sessão, abra o X nele e depois clique em Verificar sessão.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.cookies = QLineEdit()
        self.cookies.setPlaceholderText('Opcional: arquivo cookies.txt no formato Netscape (tem prioridade)')
        row = QHBoxLayout()
        row.addWidget(self.cookies)
        pick = QPushButton('Cookies…')
        pick.clicked.connect(self.choose_cookies)
        row.addWidget(pick)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.start = QPushButton('Baixar na melhor qualidade')
        self.start.clicked.connect(self.begin)
        self.cancel = QPushButton('Cancelar')
        self.cancel.setEnabled(False)
        self.cancel.clicked.connect(lambda: self.worker.stop.set())
        row.addWidget(self.start)
        row.addWidget(self.cancel)
        layout.addLayout(row)
        self.queue_label = QLabel('Fila: aguardando')
        layout.addWidget(self.queue_label)
        self.queue_bar = QProgressBar()
        layout.addWidget(self.queue_bar)
        layout.addWidget(QLabel('Progresso do arquivo atual'))
        self.bar = QProgressBar()
        layout.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        show = QPushButton('Abrir pasta de downloads')
        show.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.folder.text())))
        layout.addWidget(show)
        self.browser.currentTextChanged.connect(self.invalidate_session)
        self.profile_path.textChanged.connect(self.invalidate_session)
        self.cookies.textChanged.connect(self.invalidate_session)
        self.refresh_profiles()
    def invalidate_session(self, *_):
        self.session_revision += 1
        self.session = None
        self.session_status.setText('Fonte de sessão alterada. Verifique novamente.')
    def refresh_profiles(self, *_):
        self.profiles.blockSignals(True)
        self.profiles.clear()
        self.profiles.addItem('Automático — procurar sessão nos perfis', '')
        preferred = 0
        for profile in discover_profiles(self.browser.currentText()):
            present = {'auth_token', 'ct0'}.issubset(session_cookie_names(profile))
            self.profiles.addItem(profile.name + (' — cookies do X encontrados' if present else ' — sem cookies de login do X'), str(profile))
            if present and preferred == 0:
                preferred = self.profiles.count() - 1
        self.profiles.setCurrentIndex(preferred)
        self.profiles.blockSignals(False)
        self.select_profile()
    def select_profile(self, *_):
        self.profile_path.setText(self.profiles.currentData() or '')
    def open_login(self):
        from browser_login import open_browser_login
        try:
            open_browser_login(self.browser.currentText(), self.profile_path.text().strip())
            self.session_status.setText('X aberto no navegador selecionado. Após entrar, clique em Verificar sessão.')
        except ValueError as exc:
            self.session_status.setText(str(exc))
    def selected_urls(self):
        return parse_links(self.batch_links.toPlainText() if self.tabs.currentIndex() == 1 else self.url.text())
    def check_session(self):
        if self.checker and self.checker.isRunning():
            return
        try:
            text = self.batch_links.toPlainText() if self.tabs.currentIndex() == 1 else self.url.text()
            # For a batch, test session import here; access is checked separately per item.
            url = '' if self.tabs.currentIndex() == 1 or not text.strip() else self.selected_urls()[0]
        except ValueError as exc:
            self.session_status.setText(str(exc))
            return
        self.check.setEnabled(False)
        self.start.setEnabled(False)
        self.session_status.setText('Lendo sessão e verificando acesso…')
        self.checker = SessionWorker(self.browser.currentText(), self.cookies.text().strip(),
                                     self.profile_path.text().strip(), url, self.session)
        revision = self.session_revision
        self.checker.result.connect(lambda jar, message: self.session_checked(jar, message, revision))
        self.checker.finished.connect(lambda: self.check.setEnabled(True))
        self.checker.finished.connect(lambda: self.start.setEnabled(True))
        self.checker.start()
    def session_checked(self, jar, message, revision):
        if revision != self.session_revision:
            return
        self.session = jar
        self.session_status.setText(message)
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Pasta de destino', self.folder.text())
        if folder:
            self.folder.setText(folder)
    def choose_cookies(self):
        file, _ = QFileDialog.getOpenFileName(self, 'Cookies Netscape', '', 'Texto (*.txt);;Todos (*)')
        if file:
            self.cookies.setText(file)
    def begin(self):
        try:
            urls = self.selected_urls()
            if not self.folder.text().strip():
                raise ValueError('Escolha uma pasta de destino.')
            cookie_file = self.cookies.text().strip()
            if cookie_file and not Path(cookie_file).is_file():
                raise ValueError('Arquivo de cookies não encontrado.')
        except ValueError as exc:
            QMessageBox.warning(self, 'Confira os dados', str(exc))
            return
        self.log.clear()
        self.bar.setValue(0)
        browser = 'Sem sessão' if cookie_file else self.browser.currentText()
        if self.session is None and (browser != 'Sem sessão' or cookie_file):
            self.check_session()
            self.log.appendPlainText('Verificando a sessão. Após a confirmação, clique em baixar novamente.')
            return
        self.worker = Worker(urls, self.folder.text(), self.session)
        self.worker.queue_progress.connect(self.update_queue)
        self.worker.message.connect(self.log.appendPlainText)
        self.worker.percent.connect(self.bar.setValue)
        self.worker.result.connect(self.done)
        self.worker.finished.connect(lambda: self.start.setEnabled(True))
        self.worker.finished.connect(lambda: self.check.setEnabled(True))
        self.check.setEnabled(False)
        self.start.setEnabled(False)
        self.cancel.setEnabled(True)
        self.worker.start()
    def update_queue(self, processed, total):
        self.queue_label.setText(f'Fila: {processed}/{total} publicações processadas')
        self.queue_bar.setMaximum(total)
        self.queue_bar.setValue(processed)
    def done(self, ok, message):
        self.cancel.setEnabled(False)
        self.log.appendPlainText(message)
        if ok:
            self.bar.setValue(100)
        else:
            self.log.appendPlainText('Se o X exigir login/idade, confirme o acesso no navegador e tente novamente.')
    def closeEvent(self, event):
        if self.checker and self.checker.isRunning():
            self.session_status.setText('Aguarde a verificação terminar antes de fechar.')
            event.ignore()
        elif self.worker and self.worker.isRunning():
            self.worker.stop.set()
            self.log.appendPlainText('Cancelando… Aguarde o término antes de fechar.')
            event.ignore()
        else:
            event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
