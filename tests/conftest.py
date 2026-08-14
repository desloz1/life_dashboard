"""Configuração compartilhada da suíte pytest.

Insere a raiz do projeto no sys.path para permitir `import news`, `tasks`, etc.
Executa todos os testes fora de threads/Qt (módulos puros).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))