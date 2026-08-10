# AGENTS.md

## Padrão: manter DONE.txt

Todo trabalho de melhoria neste projeto DEVE registrar-se em `DONE.txt`:

1. ANTES de qualquer ação (ler arquivos, buscar código, editar, criar), o agente
   deve consultar `DONE.txt` **e** `BUG_FIX.md` para:
   - saber o que já foi feito (evitar retrabalho ou mudanças duplicadas); e
   - aprender com os erros anteriores (não repetir causas de bugs já corrigidos).

2. Sempre que uma sessão de trabalho concluir melhorias (novos recursos, mudanças
   de interface, refatorações, correções relevantes), adicione um novo bloco no
   TOPO do `DONE.txt` com:
   - Data no formato `AAAA-MM-DD`
   - Título curto da sessão
   - Lista objetiva das mudanças, agrupadas por área

3. Se já existir um bloco com a mesma data nesta sessão, adicione as mudanças nele
   (não crie blocos duplicados).

4. Mantenha entradas curtas e específicas (o quê mudou, onde, e o efeito visível).

## Padrão: manter BUG_FIX.md

Correções de bug (defeitos de funcionamento ou aparência) DEVEM ser registradas
em `BUG_FIX.md`, além do registro normal em `DONE.txt`:

1. O `BUG_FIX.md` também deve ser consultado antes de iniciar qualquer trabalho,
   junto com o `DONE.txt` — o histórico de causa/solução serve para não repetir
   erros já diagnosticados.

2. Ao diagnosticar/resolver um bug, adicione um novo bloco no TOPO de `BUG_FIX.md` com:
   - Data no formato `AAAA-MM-DD`
   - Título curto do bug (o sintoma relatado)
   - **Causa**: o que realmente provocava o problema (arquivo:linha quando aplicável)
   - **Solução**: a mudança aplicada e por que resolve

3. Se já existir um bloco com a mesma data nesta sessão, adicione as correções nele
   (não crie blocos duplicados).

4. Bugs são diferentes de melhorias: use `DONE.txt` para recursos, mudanças de
   interface e refatorações; use `BUG_FIX.md` para causa + solução de defeitos.

5. Mantenha entradas curtas e específicas (sintoma → causa → solução).

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
