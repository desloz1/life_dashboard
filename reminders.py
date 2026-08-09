import calendar
import os
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lembretes.txt")

WEEKDAY_NAMES = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

DAY_INDEX = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6}

TYPE_TO_PT = {
    "one_time": "única",
    "daily": "diária",
    "weekly": "semanal",
    "monthly": "mensal",
}

TYPE_NAMES = {
    "one_time": "Única",
    "daily": "Diária",
    "weekly": "Semanal",
    "monthly": "Mensal",
}


def _norm(text):
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


@dataclass
class Reminder:
    id: str
    title: str
    description: str = ""
    trigger_type: str = "one_time"
    time: str = "09:00"
    date: str = ""
    weekdays: list = field(default_factory=list)
    day_of_month: int = 1
    enabled: bool = True
    next_trigger: str = ""


def compute_next_trigger(reminder, now=None):
    now = now or datetime.now().replace(second=0, microsecond=0)
    hour, minute = (int(x) for x in reminder.time.split(":"))

    if reminder.trigger_type == "one_time":
        if not reminder.date:
            return None
        when = datetime.strptime(reminder.date, "%Y-%m-%d").replace(hour=hour, minute=minute)
        return when if when > now else None

    if reminder.trigger_type == "daily":
        candidate = now.replace(hour=hour, minute=minute)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if reminder.trigger_type == "weekly":
        if not reminder.weekdays:
            return None
        for offset in range(1, 8):
            candidate = (now + timedelta(days=offset)).replace(hour=hour, minute=minute)
            if candidate.weekday() in reminder.weekdays and candidate > now:
                return candidate
        return None

    if reminder.trigger_type == "monthly":
        year, month = now.year, now.month
        for _ in range(13):
            month += 1
            if month > 12:
                month, year = 1, year + 1
            last_day = calendar.monthrange(year, month)[1]
            day = min(reminder.day_of_month, last_day)
            candidate = datetime(year, month, day, hour, minute)
            if candidate > now:
                return candidate
        return None

    return None


def describe_schedule(reminder):
    time = reminder.time
    if reminder.trigger_type == "one_time":
        day = datetime.strptime(reminder.date, "%Y-%m-%d").strftime("%d/%m/%Y")
        return f"Única em {day} às {time}"
    if reminder.trigger_type == "daily":
        return f"Diária às {time}"
    if reminder.trigger_type == "weekly":
        days = ", ".join(WEEKDAY_NAMES[w] for w in sorted(reminder.weekdays))
        return f"Semanal ({days}) às {time}"
    if reminder.trigger_type == "monthly":
        return f"Mensal dia {reminder.day_of_month} às {time}"
    return time


def format_next(next_trigger, now=None):
    if not next_trigger:
        return "Sem alarme agendado"
    dt = datetime.fromisoformat(next_trigger)
    now = now or datetime.now()
    if dt.date() == now.date():
        return f"Hoje às {dt:%H:%M}"
    if dt.date() == (now + timedelta(days=1)).date():
        return f"Amanhã às {dt:%H:%M}"
    return f"{dt:%d/%m/%Y} às {dt:%H:%M}"


def _type_to_pt(trigger_type):
    return TYPE_TO_PT.get(trigger_type, trigger_type)


def _pt_to_type(value):
    norm = _norm(value)
    for key, label in TYPE_TO_PT.items():
        if norm in (key, _norm(label)):
            return key
    return "one_time"


def _weekday_name(weekday):
    return WEEKDAY_NAMES[weekday]


def _date_to_pt(iso_date):
    if not iso_date:
        return ""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")


def _date_to_iso(text):
    text = (text or "").strip()
    if not text:
        return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def serialize_reminder(reminder):
    weekdays = ", ".join(_weekday_name(w) for w in sorted(reminder.weekdays))
    return (
        f"ID: {reminder.id}\n"
        f"Título: {reminder.title}\n"
        f"Descrição: {reminder.description}\n"
        f"Recorrência: {_type_to_pt(reminder.trigger_type)}\n"
        f"Horário: {reminder.time}\n"
        f"Data: {_date_to_pt(reminder.date)}\n"
        f"Dias: {weekdays}\n"
        f"Dia do mês: {reminder.day_of_month}\n"
        f"Ativo: {'sim' if reminder.enabled else 'não'}"
    )


def parse_reminder(block_lines):
    data = {}
    for line in block_lines:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        data[_norm(key)] = value.strip()

    title = data.get("titulo", "").strip()
    if not title:
        return None

    weekdays = []
    for token in data.get("dias", "").split(","):
        if _norm(token) in DAY_INDEX:
            weekdays.append(DAY_INDEX[_norm(token)])

    enabled = _norm(data.get("ativo", "sim")) in ("sim", "s", "1", "true", "yes")
    try:
        day_of_month = int(data.get("dia do mes", "1"))
        day_of_month = max(1, min(31, day_of_month))
    except ValueError:
        day_of_month = 1

    return Reminder(
        id=data.get("id", "") or uuid.uuid4().hex,
        title=title,
        description=data.get("descricao", ""),
        trigger_type=_pt_to_type(data.get("recorrencia", "única")),
        time=data.get("horario", "09:00"),
        date=_date_to_iso(data.get("data", "")),
        weekdays=weekdays,
        day_of_month=day_of_month,
        enabled=enabled,
    )


class ReminderManager:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.reminders = []
        self.load()

    def load(self):
        self.reminders = []
        if not os.path.exists(self.path):
            return
        blocks = []
        current = []
        try:
            with open(self.path, "r", encoding="utf-8-sig") as fh:
                for raw in fh:
                    line = raw.rstrip("\r\n")
                    if line.startswith("#"):
                        continue
                    if not line.strip():
                        if current:
                            blocks.append(current)
                            current = []
                        continue
                    current.append(line)
                if current:
                    blocks.append(current)
        except OSError:
            return

        seen_ids = set()
        for block in blocks:
            reminder = parse_reminder(block)
            if reminder is None:
                continue
            if not reminder.id or reminder.id in seen_ids:
                reminder.id = uuid.uuid4().hex
            seen_ids.add(reminder.id)
            if reminder.enabled:
                next_trigger = compute_next_trigger(reminder)
                reminder.next_trigger = next_trigger.isoformat() if next_trigger else ""
            self.reminders.append(reminder)

    def save(self):
        lines = [
            "# Lembretes do Organizador Pessoal",
            "# Campos separados por ':' e cada lembrete separado por uma linha em branco.",
            "# Recorrência: única, diária, semanal ou mensal.",
            "# Dias (para semanal): Seg, Ter, Qua, Qui, Sex, Sáb, Dom.",
            "# Ativo: sim ou não.",
        ]
        for index, reminder in enumerate(self.reminders):
            if index:
                lines.append("")
            lines.append(serialize_reminder(reminder))
        with open(self.path, "w", encoding="utf-8-sig") as fh:
            fh.write("\n".join(lines) + "\n")

    def add(self, title, description="", trigger_type="one_time", time="09:00",
            date="", weekdays=None, day_of_month=1, enabled=True):
        reminder = Reminder(
            id=uuid.uuid4().hex,
            title=title,
            description=description,
            trigger_type=trigger_type,
            time=time,
            date=date,
            weekdays=weekdays or [],
            day_of_month=day_of_month,
            enabled=enabled,
        )
        if enabled:
            next_trigger = compute_next_trigger(reminder)
            reminder.next_trigger = next_trigger.isoformat() if next_trigger else ""
        self.reminders.append(reminder)
        self.save()
        return reminder

    def update(self, reminder):
        reminder.next_trigger = ""
        if reminder.enabled:
            next_trigger = compute_next_trigger(reminder)
            reminder.next_trigger = next_trigger.isoformat() if next_trigger else ""
        self.save()

    def remove(self, reminder_id):
        self.reminders = [r for r in self.reminders if r.id != reminder_id]
        self.save()

    def toggle(self, reminder_id):
        for reminder in self.reminders:
            if reminder.id == reminder_id:
                reminder.enabled = not reminder.enabled
                reminder.next_trigger = ""
                if reminder.enabled:
                    next_trigger = compute_next_trigger(reminder)
                    reminder.next_trigger = next_trigger.isoformat() if next_trigger else ""
                self.save()
                return

    def check_due(self, now=None):
        now = now or datetime.now()
        fired = []
        changed = False
        for reminder in self.reminders:
            if not reminder.enabled or not reminder.next_trigger:
                continue
            if datetime.fromisoformat(reminder.next_trigger) <= now:
                fired.append(reminder)
                changed = True
                if reminder.trigger_type == "one_time":
                    reminder.enabled = False
                    reminder.next_trigger = ""
                else:
                    next_trigger = compute_next_trigger(reminder, now)
                    reminder.next_trigger = next_trigger.isoformat() if next_trigger else ""
        if changed:
            self.save()
        return fired
