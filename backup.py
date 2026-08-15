"""Backup e exportação/importação de dados (módulo puro, sem Qt).

- `run_backup(keep)` — copia os arquivos de dados para `backups/backup_<ts>/`
  e mantém apenas os `keep` backups mais recentes.
- `export_all(path)` — grava um único JSON com o conteúdo de todos os arquivos
  de dados (round-trip exato).
- `import_all(path)` — restaura os arquivos de dados a partir de um export.
"""

import datetime
import json
import shutil
from pathlib import Path

import log

logger = log.get_logger("life_dashboard.backup")

_DIR = Path(__file__).resolve().parent
BACKUP_DIR = _DIR / "backups"

# Um por formato de persistência do app (mesmos arquivos em .gitignore).
DATA_FILENAMES = (
    "tarefas.txt",
    "notas.json",
    "compras.json",
    "lembretes.txt",
    "estado_noticias.json",
)


def data_files():
    """Caminhos absolutos dos arquivos de dados que o app mantém."""
    return [(_DIR / name) for name in DATA_FILENAMES]


def existing_data_files():
    return [path for path in data_files() if path.exists()]


def run_backup(keep=7):
    """Copia os dados atuais para um subdiretório novo em `backups/`.

    Remove backups antigos excedentes (mantém os `keep` mais recentes).
    Retorna o caminho do backup criado, ou None se não havia dados.
    """
    sources = existing_data_files()
    if not sources:
        logger.info("Backup: nenhum arquivo de dados presente.")
        return None

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"backup_{stamp}"
    try:
        target.mkdir(parents=True, exist_ok=True)
        for path in sources:
            shutil.copy2(path, target / path.name)
    except OSError as exc:
        logger.error("Falha ao criar backup em %s: %s", target, exc)
        return None

    pruned = _prune(BACKUP_DIR, keep)
    if pruned:
        logger.debug("Backup: removidos %d backup(s) antigo(s).", pruned)
    logger.info("Backup criado: %s (%d arquivos)", target, len(sources))
    return str(target)


def _prune(directory, keep):
    dirs = [p for p in directory.iterdir() if p.is_dir() and p.name.startswith("backup_")]
    dirs.sort()
    removed = 0
    while len(dirs) > keep:
        shutil.rmtree(dirs.pop(0), ignore_errors=True)
        removed += 1
    return removed


def export_all(path):
    """Exporta todos os dados para um único arquivo JSON. Retorna o caminho."""
    payload = {
        "app": "organizador-pessoal",
        "exported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "data": {},
    }
    for name in DATA_FILENAMES:
        source = _DIR / name
        if source.exists():
            try:
                payload["data"][name] = source.read_text(encoding="utf-8")
            except OSError as exc:
                logger.error("Falha ao ler %s para export: %s", source, exc)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Export completo gravado em %s", out)
    return str(out)


def import_all(path, backup_first=True):
    """Restaura os dados a partir de um export JSON. Retorna lista de arquivos gravados.

    Antes de sobrescrever, cria um backup dos dados atuais (por segurança).
    Arquivos ausentes no export são ignorados (não são apagados).
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise ValueError("Arquivo de export inválido: seção 'data' ausente.")

    if backup_first:
        run_backup()

    restored = []
    for name in DATA_FILENAMES:
        content = data.get(name)
        if content is None:
            continue
        target = _DIR / name
        try:
            target.write_text(content, encoding="utf-8")
            restored.append(name)
        except OSError as exc:
            logger.error("Falha ao restaurar %s: %s", target, exc)
    logger.info("Import restaurado de %s (%d arquivos)", path, len(restored))
    return restored