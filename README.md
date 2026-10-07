# XDownloader

Aplicativo local com interface gráfica para baixar vídeos do X (Twitter), individualmente ou em lote, usando Python, Qt e yt-dlp.

- Melhor formato disponível com vídeo e áudio, sem recodificação.
- Links em lote, um por linha, com remoção de duplicatas.
- Importação da sessão do navegador para conteúdo acessível à sua conta.
- Descoberta dos perfis locais e abertura do X no perfil selecionado.
- Progresso por arquivo e por fila, cancelamento e retomada de arquivos parciais.
- Sem conversores online, serviços intermediários, telemetria ou atualizações automáticas.

## Requisitos

- Linux com ambiente gráfico (plataforma validada).
- Python 3.10 ou superior, com `venv` e `pip`.
- Navegador compatível, como Chrome, Chromium ou Firefox, para vídeos que exigem sessão.

A descoberta automática de perfis e a abertura do navegador foram implementadas para Linux. Outros sistemas ainda não foram validados.

## Instalação

```bash
git clone https://github.com/andreataide/XDownloader.git
cd XDownloader
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./iniciar.sh
```

Se o sistema não tiver suporte a `venv`, instale o pacote correspondente da sua distribuição, como `python3-venv` no Debian/Ubuntu. O Qt também precisa das bibliotecas gráficas do sistema.

A instalação baixa bibliotecas do PyPI. Durante os downloads, o aplicativo permite apenas HTTPS para `x.com`, `twitter.com`, `twimg.com` e seus subdomínios, incluindo redirecionamentos. Proxies do ambiente são desativados. O navegador aberto pelo aplicativo tem seu funcionamento normal.

## Uso

1. Cole uma publicação na aba **Um link** ou vários links na aba **Baixar em lote**, um por linha.
2. Escolha a pasta de destino.
3. Para vídeos restritos, selecione o navegador e o perfil onde sua conta está conectada. A lista indica os perfis com cookies de sessão; isso ainda não comprova que a sessão é válida no X.
4. Se necessário, clique em **Abrir X no perfil selecionado**, entre no próprio X e confirme que consegue assistir à publicação.
5. Clique em **Verificar sessão / acesso ao vídeo**, depois em **Baixar na melhor qualidade**.

Um arquivo `cookies.txt` no formato Netscape pode ser usado como alternativa à leitura direta do navegador. Ele tem prioridade sobre o navegador selecionado.

No modo de um link, a verificação consulta a publicação sem baixar o vídeo. No modo em lote, ela verifica os cookies locais; cada publicação é consultada no X durante seu download.

### Lotes

Linhas vazias são ignoradas. Links equivalentes da mesma publicação são deduplicados, inclusive entre X/Twitter e URLs com parâmetros. Links inválidos são indicados pelo número da linha antes de iniciar.

A fila é sequencial e reutiliza a sessão autenticada. Se uma publicação falhar, o erro é registrado e a fila segue. O resumo final mostra publicações baixadas, falhas e itens não processados. Uma publicação pode conter vários vídeos.

**Cancelar** interrompe no próximo evento de progresso e impede o início dos próximos links. A requisição atual pode precisar terminar antes do cancelamento. Arquivos parciais são preservados para retomada.

## Sessão e restrições de idade

O programa não solicita senha, não altera idade e não contorna a verificação oficial do X. Sua conta deve concluir as exigências da plataforma e ter acesso ao vídeo. Confira também a configuração de mídia sensível no X.

Os cookies importados ficam na memória e não são exportados pelo aplicativo. No Linux, a dependência `SecretStorage` permite acessar o chaveiro local quando necessário para descriptografar cookies do Chrome. Se houver uma solicitação de desbloqueio do chaveiro, ela pertence ao sistema operacional.

Arquivos de cookies contêm credenciais: mantenha-os privados e nunca os envie em issues ou pull requests. Use o programa somente para conteúdo que você tem autorização para baixar.

## Diagnóstico

- **Sessão não encontrada:** selecione o perfil correto ou escolha o modo automático. Faça login no X nesse perfil e verifique novamente.
- **Falha de leitura/descriptografia:** feche o navegador e tente novamente. Verifique se o chaveiro do Linux está desbloqueado. Como alternativa, use Firefox ou um arquivo Netscape de cookies da sua sessão.
- **Erro 403, login ou idade:** confirme que sua conta consegue assistir ao mesmo vídeo no X e renove a sessão.
- **Link externo incorporado:** o downloader aceita somente publicações e mídia dos domínios permitidos.
- **Mudanças nas APIs do X:** podem exigir atualização manual do yt-dlp e ajustes no aplicativo. As versões são fixadas em `requirements.txt` porque o programa usa interfaces internas da biblioteca.

## Desenvolvimento e testes

```bash
.venv/bin/python -m unittest discover -s tests -v
```

A suíte cobre URLs e restrição de domínio, importação de sessão e seleção de perfil, deduplicação, continuidade após falhas e cancelamento do lote. Não precisa de conta nem faz downloads reais. A interface também pode ser validada sem monitor:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "from PySide6.QtWidgets import QApplication; from app import Window; app = QApplication([]); window = Window(); window.show(); app.processEvents(); window.close()"
```

Para contribuir, abra uma issue ou pull request descrevendo o problema e os passos para reproduzir. Remova cookies, identificadores pessoais e dados privados de logs e imagens.

## Licença e dependências

Código do projeto sob [licença MIT](LICENSE). As dependências mantêm suas próprias licenças: [yt-dlp](https://github.com/yt-dlp/yt-dlp) e [PySide6/Qt](https://doc.qt.io/qtforpython-6/licenses.html).

Projeto independente, sem afiliação com X Corp.
