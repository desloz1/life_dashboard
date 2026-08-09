import os
import uuid
from dataclasses import dataclass

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tarefas.txt")


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    due: str = ""  # ISO date
    completed: bool = False
    priority: str = ""  # "", "alta", "media", "baixa"
    category: str = ""


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
                for raw in fh:
                    line = raw.rstrip("\n\r")
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) < 5:
                        continue
                    tid, title, desc, due, completed = parts[0:5]
                    priority = parts[5] if len(parts) > 5 else ""
                    category = parts[6] if len(parts) > 6 else ""
                    task = Task(id=tid, title=title, description=desc, due=due,
                                completed=(completed == "1"), priority=priority, category=category)
                    self.tasks.append(task)
        except OSError:
            return

    def save(self):
        lines = []
        for t in self.tasks:
            lines.append("|".join([
                t.id, t.title, t.description or "", t.due or "",
                "1" if t.completed else "0", t.priority or "", t.category or "",
            ]))
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + ("\n" if lines else ""))
        except OSError:
            pass

    def add(self, title, description="", due="", completed=False, priority="", category=""):
        t = Task(id=uuid.uuid4().hex, title=title, description=description, due=due,
                 completed=completed, priority=priority, category=category)
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
                t.completed = not t.completed
                self.save()
                return
