import calendar
import datetime
import os
import uuid
from dataclasses import dataclass

import log

logger = log.get_logger("life_dashboard.tasks")

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tarefas.txt")

RECURRENCE_NAMES = {
    "": "Nenhuma",
    "diaria": "Diária",
    "semanal": "Semanal",
    "mensal": "Mensal",
}


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    due: str = ""  # ISO date
    completed: bool = False
    completed_at: str = ""  # ISO date when completed
    priority: str = ""  # "", "alta", "media", "baixa"
    category: str = ""
    recurrence: str = ""  # "", "diaria", "semanal", "mensal"
    overdue_notified: str = ""  # ISO date of the last overdue alert shown


def next_occurrence(due, recurrence):
    """Próximo vencimento após concluir uma tarefa recorrente (nunca no passado)."""
    if not due or not recurrence:
        return ""
    try:
        d = datetime.date.fromisoformat(due)
    except (ValueError, TypeError):
        return ""
    today = datetime.date.today()
    if recurrence == "diaria":
        nxt = d + datetime.timedelta(days=1)
    elif recurrence == "semanal":
        nxt = d + datetime.timedelta(days=7)
    elif recurrence == "mensal":
        if d.month == 12:
            month, year = 1, d.year + 1
        else:
            month, year = d.month + 1, d.year
        last = calendar.monthrange(year, month)[1]
        nxt = datetime.date(year, month, min(d.day, last))
    else:
        return ""
    return max(nxt, today).isoformat()


class TaskManager:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.tasks = []
        self.load()

    def load(self):
        self.tasks = []
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            logger.error("Falha ao carregar tarefas de %s: %s", self.path, exc)
            return
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue
            if line.startswith("id:"):
                block = []
                while i < len(lines) and lines[i].strip():
                    block.append(lines[i].strip())
                    i += 1
                task = self._parse_block(block)
                if task is not None:
                    self.tasks.append(task)
                continue
            task = self._parse_legacy(line)
            if task is not None:
                self.tasks.append(task)
            i += 1

    @staticmethod
    def _parse_legacy(line):
        parts = line.split("|")
        if len(parts) < 5:
            return None
        tid, title, desc, due, completed = parts[0:5]
        priority = parts[5] if len(parts) > 5 else ""
        category = parts[6] if len(parts) > 6 else ""
        return Task(id=tid, title=title, description=desc, due=due,
                    completed=(completed == "1"), priority=priority, category=category)

    @staticmethod
    def _parse_block(block):
        data = {}
        for line in block:
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            data[key.strip().lower()] = value.strip()
        tid = data.get("id", "")
        if not tid:
            return None
        completed = str(data.get("concluída", "não")).lower() in ("sim", "1", "true", "verdadeiro")
        return Task(
            id=tid,
            title=data.get("título", data.get("titulo", "")),
            description=data.get("descrição", data.get("descricao", "")),
            due=data.get("prazo", ""),
            completed=completed,
            completed_at=data.get("concluída em", data.get("concluida em", "")).strip(),
            priority=data.get("prioridade", ""),
            category=data.get("categoria", ""),
            recurrence=data.get("recorrência", data.get("recorrencia", "")).strip(),
            overdue_notified=data.get("notificado", "").strip(),
        )

    def save(self):
        lines = ["# tarefas.txt — dados salvos pelo app. Cada bloco abaixo é uma tarefa."]
        for t in self.tasks:
            lines.append("id: " + t.id)
            lines.append("título: " + (t.title or ""))
            lines.append("descrição: " + (t.description or ""))
            lines.append("prazo: " + (t.due or ""))
            lines.append("concluída: " + ("sim" if t.completed else "não"))
            lines.append("concluída em: " + (t.completed_at or ""))
            lines.append("prioridade: " + (t.priority or ""))
            lines.append("categoria: " + (t.category or ""))
            lines.append("recorrência: " + (t.recurrence or ""))
            lines.append("notificado: " + (t.overdue_notified or ""))
            lines.append("")
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        except OSError as exc:
            logger.error("Falha ao salvar tarefas em %s: %s", self.path, exc)

    def add(self, title, description="", due="", completed=False, priority="", category="",
            recurrence=""):
        t = Task(id=uuid.uuid4().hex, title=title, description=description, due=due,
                 completed=completed, completed_at=datetime.date.today().isoformat() if completed else "",
                 priority=priority, category=category, recurrence=recurrence)
        self.tasks.append(t)
        self.save()
        return t

    def update(self, task):
        self.save()

    def remove(self, task_id):
        self.tasks = [t for t in self.tasks if t.id != task_id]
        self.save()

    def toggle(self, task_id):
        for t in self.tasks:
            if t.id == task_id:
                if not t.completed and t.recurrence:
                    self.tasks.append(Task(
                        id=uuid.uuid4().hex,
                        title=t.title,
                        description=t.description,
                        due=next_occurrence(t.due, t.recurrence),
                        completed=False,
                        priority=t.priority,
                        category=t.category,
                        recurrence=t.recurrence,
                    ))
                t.completed = not t.completed
                t.completed_at = datetime.date.today().isoformat() if t.completed else ""
                t.overdue_notified = ""
                self.save()
                return

    def overdue_tasks(self, today=None):
        """Tarefas pendentes com prazo já vencido, ordenadas pelo mais antigo."""
        today = today or datetime.date.today()
        overdue = []
        for t in self.tasks:
            if t.completed or not t.due:
                continue
            try:
                due = datetime.date.fromisoformat(t.due)
            except (ValueError, TypeError):
                continue
            if due < today:
                overdue.append(t)
        overdue.sort(key=lambda t: (t.due or "9999-12-31", t.title.lower()))
        return overdue

    def mark_overdue_notified(self, task_ids, day=None):
        """Registra que o alerta de atraso foi mostrado no dia (evita repetir a cada tick)."""
        day = day or datetime.date.today().isoformat()
        changed = False
        for t in self.tasks:
            if t.id in task_ids and t.overdue_notified != day:
                t.overdue_notified = day
                changed = True
        if changed:
            self.save()

    def _completed_dates(self):
        dates = []
        for t in self.tasks:
            if t.completed and t.completed_at:
                try:
                    dates.append(datetime.date.fromisoformat(t.completed_at))
                except ValueError:
                    pass
        return dates

    def completed_last_days(self, days=7):
        today = datetime.date.today()
        start = today - datetime.timedelta(days=days - 1)
        counts = {}
        for d in self._completed_dates():
            if start <= d <= today:
                counts[d.isoformat()] = counts.get(d.isoformat(), 0) + 1
        return [
            (start + datetime.timedelta(days=i),
             counts.get((start + datetime.timedelta(days=i)).isoformat(), 0))
            for i in range(days)
        ]

    def streak_days(self):
        dates = {d for d in self._completed_dates()}
        if not dates:
            return 0
        today = datetime.date.today()
        anchor = today if today in dates else today - datetime.timedelta(days=1)
        streak = 0
        while anchor in dates:
            streak += 1
            anchor -= datetime.timedelta(days=1)
        return streak

    def search(self, query):
        q = (query or "").strip().lower()
        if not q:
            return list(self.tasks)
        fields = ("title", "description", "category", "priority", "due", "recurrence")
        return [t for t in self.tasks if q in " ".join(getattr(t, f) or "" for f in fields).lower()]

    def category_stats(self):
        cats = {}
        for t in self.tasks:
            cat = (t.category or "").strip() or "Sem categoria"
            entry = cats.setdefault(cat, {"total": 0, "done": 0})
            entry["total"] += 1
            if t.completed:
                entry["done"] += 1
        items = []
        for cat, e in cats.items():
            items.append({
                "category": cat,
                "total": e["total"],
                "done": e["done"],
                "pct": round(e["done"] * 100 / e["total"]) if e["total"] else 0,
            })
        items.sort(key=lambda x: (-x["total"], x["category"]))
        return items
