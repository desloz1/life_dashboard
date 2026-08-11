---

## 2026-08-11 — Aba Compras: "NameError: name 'QCursor' is not defined" no leaveEvent

- **Causa**: `compras_ui.py:309` (`ProductCard.leaveEvent`) usava `QCursor.pos()` mas o import do arquivo só trazia `QDesktopServices` de `PySide6.QtGui` — `QCursor` nunca foi importado. O `leaveEvent` (override de `QFrame`) disparava o traceback ao mover o mouse para fora de um card.
- **Solução**: `compras_ui.py` — adicionado `QCursor` ao import de `PySide6.QtGui`. Validado com `import compras_ui` OK.

---

## 2026-08-11 — Warning "QGradient::setColorAt: Color position must be specified in the range 0 to 1" no console

- **Causa**: `common.py` (`ShineEffect.paintEvent`) — o brilho de shimmer anima `_offset` de 0 a 1.5 (`_anim.setEndValue(1.5)`); as posições `left` (`pos - 0.15`) e `mid1` (`pos - 0.02`) só eram clampeadas em `>= 0` (`max`), então com `_offset > 1.0` passavam de 1 e o Qt emitia o warning (ignorando a cor). Não era erro nem quebrava a UI — só poluía o console.
- **Solução**: `common.py` — `left` e `mid1` agora também clampeadas a 1.0 (`min(1.0, max(0.0, ...))`), mesmas restrições já aplicadas a `mid2`/`right`. Validado: `import common` OK e `setColorAt` acima de 1 já não é chamado.

---

## 2026-08-10 — App não abria: lembrete "única" sem data quebrava o `describe_schedule`

- **Causa**: um lembrete com `Recorrência: única` e `Data:` vazia fazia `reminders.py` (`describe_schedule`) quebrar com `ValueError: time data '' does not match format '%Y-%m-%d'` na montagem do `ReminderCard` — a inicialização da janela falhava logo em `RemindersView`. O `compute_next_trigger` já tratava `not reminder.date`, mas o `describe_schedule` não.
- **Solução**: `reminders.py` (`describe_schedule`) — quando `one_time` não tem data, retorna `"Única às HH:MM (sem data)"` em vez de chamar `strptime`. Validado offscreen (renderiza card sem data) e `import main` OK.

---

## 2026-08-10 — Borda esquerda dos cards cortada (sombra clippada) nas abas

- **Causa**: os layouts de lista/scroll usavam `setContentsMargins(0, 0, 6, 6)` — margem esquerda **0** enquanto a direita era 6. Como os cards têm `QGraphicsDropShadowEffect` (blur 12–22), o primeiro card encostava exatamente na borda esquerda do viewport e a sombra à esquerda era recortada (pixels transparentes), dando o aspecto de "bolha cortada" na borda esquerda — enquanto à direita a sombra aparecia normal.
- **Solução**: margem esquerda passou a `6` (igual à direita) nos layouts de Notícias (`news.py`), Lembretes (`reminders_ui.py`), Tarefas (`tasks_ui.py`), Notas (`notes_ui.py`), Agenda (Por dia/Mês/Semana — `agenda_ui.py`), Busca global (`search_ui.py`) e Clima (`weather_ui.py`, página + faixas horizontais). Validado offscreen por análise de pixels: sombra esquerda agora aparece simétrica à direita nos temas claro e escuro; `import main` OK.

---

## 2026-08-10 — Estatísticas de tarefas no Início apareciam quebradas ("4 5 7" soltos)

- **Causa**: o `TaskWeekChart` tinha `setMinimumWidth(220)` e era adicionado no HBox do card `#dashStats` **sem stretch** (a coluna lateral tinha `stretch 1`), então o layout sempre o mantinha em 220 px de largura mesmo com o card com 1050 px+. O gráfico ficava espremido no canto e a linha de números do dia (4, 5, 6, 7…) aparecia descolada no rodapé da bolha, sem conexão visual com as barras. Quando não havia conclusões nos últimos 7 dias (ex.: tarefas antigas, sem `completed_at`), só os números do dia eram pintados sobre a área vazia — parecia texto solto/quebrado.
- **Solução**: `dashboard_ui.py` — `stats_layout.addWidget(self.stats_chart, 2)` dá stretch ao gráfico (largura passa a ~670 px em janela maximizada), desenhada uma linha de base (`theme.BORDER`) conectando barras aos rótulos, e o `paintEvent` agora mostra "Sem conclusões ainda" centralizado quando o total do período é zero (em vez de pintar só os números do dia). Validado offscreen (temas claro/escuro, com dados e vazio) e `import main` OK.

---

# BUG_FIX — Registro de correções de bugs

Toda correção de defeito de funcionamento ou aparência deve ser registrada aqui,
com causa e solução. Blocos novos vão ao TOPO, em ordem cronológica.

---

## 2026-08-10 — Notícia vista não esmaecia ao clicar (sem repaint)

- **Causa**: `set_seen()` (em `NewsCard`, `FeaturedCard` — `news.py` — e `DashNewsRow` — `dashboard_ui.py`) trocava a propriedade `seen` e chamava apenas `style().unpolish()/polish()`. Em widgets com `QGraphicsDropShadowEffect` (o `make_shadow` de todos os cards de notícia), essa sequência reavalia a regra QSS mas **não agenda repintura** (bug conhecido do Qt); o esmaecimento `[seen="true"]` só aparecia quando outro evento forçava repaint. Além disso, no tema claro o fundo `PAUSED_BG` vs `CARD` é quase idêntico (255 vs 247), o que tornava o efeito praticamente invisível.
- **Solução**: adicionado `self.update()` logo após o repolish nos três `set_seen` — agenda um `paintEvent` que re-renderiza o card através do efeito gráfico, aplicando imediatamente o fundo/título esmaecidos. Validado offscreen: clique real (QTest) muda a cor de fundo e do título nos dois temas e `import main` OK.

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
