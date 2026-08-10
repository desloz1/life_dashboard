# BUG_FIX — Registro de correções de bugs

Toda correção de defeito de funcionamento ou aparência deve ser registrada aqui,
com causa e solução. Blocos novos vão ao TOPO, em ordem cronológica.

---

## 2026-08-10 — Aba Clima não carregava (conteúdo quebrado por erro de SSL)

- **Causa**: `api.open-meteo.com` entrega cadeia TLS não confiável nesta máquina
  (`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`), o mesmo
  problema já corrigido para fontes de notícias. A requisição em `weather.py` usava
  a verificação padrão do `requests`, falhava sempre, e a aba Clima mostrava só a
  mensagem de erro no lugar de qualquer conteúdo.
- **Solução**: `weather.py` — requisição do clima com `verify=False`, seguindo o
  padrão já usado em `scraper.py`, com aviso suprimido via `urllib3.disable_warnings`
  no import do módulo. Validado: `get_weather()` retorna 24 horas + 7 dias e a aba
  renderiza (offscreen) com os cards, gráfico e status "Atualizado agora".

## 2026-08-10 — Cantos do campo data do lembrete quebrados ao clicar

- **Causa**: `QDateEdit` com `setCalendarPopup(True)` desenhava o sub-controle `::drop-down`
  (botão do calendário) com fundo opaco quadrado por cima do canto arredondado do campo;
  ao focar/clicar, a borda (ACCENT) deixava os cantos superiores e inferiores direitos visivelmente retos.
- **Solução**: `theme.py` — adicionada regra `QDateEdit::drop-down { border: none; width: 26px;
  background: transparent; }`. O fundo transparente deixa o arredondamento do widget aparecer;
  os 4 cantos ficam simétricos (validado por análise de pixels nos temas claro e escuro).

## 2026-08-10 — "Python nao foi encontrado no PATH" ao rodar run.bat

- **Causa**: a checagem `where python` do `run.bat` depende do `where.exe`, que fica em
  `C:\Windows\System32` — diretório que não está no PATH deste usuário. A checagem falhava
  sempre, mesmo com Python instalado, e o script exibia a mensagem enganosa. Além disso,
  a única instalação Python (`C:\PYTHON`) estava sem as dependências do app.
- **Solução**: `run.bat` — detecção de Python com a expansão nativa do cmd (`%%~$PATH:i`,
  sem `where.exe`) e execução pelo caminho absoluto; verificações de versão; instalação
  automática de Python (winget/instalador oficial) e de dependências (`pip install -r requirements.txt`).

## 2026-08-10 — Notícias de "O Blumenauense" e "AJ Notícias" não carregavam (SSL)

- **Causa**: `oblumenauense.com.br` e `ajnoticias.com.br` servem cadeia TLS incompleta;
  `requests` (verificação padrão) falhava com `CERTIFICATE_VERIFY_FAILED`. A fonte AJ falhava
  em silêncio antes mesmo de a nova fonte ser adicionada.
- **Solução**: `scraper.py` — requisições dessas fontes com `verify=False`, com aviso suprimido
  via `urllib3.disable_warnings` no import do módulo.

## 2026-08-09 — Cards do Início sumiam no hover

- **Causa**: o `QGraphicsOpacityEffect` permanente no stack do `main.py` somava com o
  `QGraphicsDropShadowEffect` dos cards e os fazia sumir ao repintar no hover (bug conhecido do Qt).
- **Solução**: o fade passou a ser aplicado só durante a transição de aba (`_start_fade`) e
  removido ao terminar (`_finish_fade` via `setGraphicsEffect(None)`), preservando a sombra dos cards.

## 2026-08-09 — App não iniciava no Python 3.9 (erro de sintaxe)

- **Causa**: `reminders.py` usava backslash dentro de f-string em `serialize_reminder`, sintaxe
  só disponível a partir do Python 3.12.
- **Solução**: removido o backslash do f-string; o app volta a rodar no Python 3.9+.
