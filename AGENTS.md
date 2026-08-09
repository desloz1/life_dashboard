# AGENTS.md

## Padrão: manter DONE.txt

Todo trabalho de melhoria neste projeto DEVE registrar-se em `DONE.txt`:

1. ANTES de qualquer ação (ler arquivos, buscar código, editar, criar), o agente
   deve consultar `DONE.txt` para saber o que já foi feito e evitar retrabalho
   ou mudanças duplicadas.

2. Sempre que uma sessão de trabalho concluir melhorias (novos recursos, mudanças
   de interface, refatorações, correções relevantes), adicione um novo bloco no
   TOPO do `DONE.txt` com:
   - Data no formato `AAAA-MM-DD`
   - Título curto da sessão
   - Lista objetiva das mudanças, agrupadas por área

3. Se já existir um bloco com a mesma data nesta sessão, adicione as mudanças nele
   (não crie blocos duplicados).

4. Mantenha entradas curtas e específicas (o quê mudou, onde, e o efeito visível).

## Comandos de verificação

- Não há suíte de testes no repositório; testes de regressão são executados via
  scripts temporários em `%TEMP%\opencode` (fora do workspace) com `python -u -X utf8`.
- Antes de finalizar alterações, verificar imports com:
  `python -X utf8 -c "import sys; sys.path.insert(0, r'<cwd>'); import main"`

## Convenções de código

- Python 3 + PySide6. Cada aba em seu módulo (`*_ui.py`), regras de negócio sem UI
  em módulos puros (`reminders.py`, `weather.py`, `tasks.py`).
- Temas claro/escuro centralizados em `theme.py` (variáveis globais + stylesheet);
  estados visuais via propriedades e QSS (ex.: `[seen="true"]`, `[overdue="true"]`).
- Persistência de estado de UI em arquivos JSON ao lado do código (ex.: `estado_noticias.json`);
  configuração em QSettings; senha SMTP no keyring.
- Atalhos e zoom de fonte definidos em `main.py` (`_setup_shortcuts`, `theme.FONT_SCALE`).
