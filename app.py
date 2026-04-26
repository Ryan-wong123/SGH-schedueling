from __future__ import annotations

import cgi
import html
import io
import json
import re
import tempfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

try:
    import msoffcrypto
except Exception:  # pragma: no cover - optional dependency at runtime
    msoffcrypto = None


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
STATIC_DIR = ROOT / "static"

ASSESSMENT_ALIASES = {
    "mini_cex": ["mini cex", "minicex", "mini-cex", "mini_cex"],
    "cbd": ["cbd", "case based", "case-based"],
    "med_recon": ["med recon", "medication reconciliation", "med reconciliation"],
    "dispensing": ["dispensing", "dispense"],
    "rx_check": ["rx check", "rxcheck", "prescription check", "rx"],
}

ASSESSMENT_LABELS = {
    "mini_cex": "Mini-CEX",
    "cbd": "CBD",
    "med_recon": "Med Recon",
    "dispensing": "Dispensing",
    "rx_check": "Rx Check",
}

NEEDS_WARD = {"mini_cex", "med_recon"}
NEEDS_OPS = {"dispensing"}
MAX_DAILY_ASSESSMENTS = 4
MAX_DAILY_MINI_CEX = 2


@dataclass
class Cell:
    value: Any
    fill: str = ""
    comment: str = ""


@dataclass
class Task:
    assessee: str
    assessment: str
    source_sheet: str
    source_cell: str
    avoid: set[str] = field(default_factory=set)


@dataclass
class Availability:
    roster_text: str = ""
    wards: set[str] = field(default_factory=set)
    is_ops: bool = False
    is_glf: bool = False
    is_working: bool = False

    @property
    def location(self) -> str:
        if self.wards and self.is_ops:
            return f"Ward {', '.join(sorted(self.wards))} / OPS"
        if self.wards:
            return f"Ward {', '.join(sorted(self.wards))}"
        if self.is_ops:
            return "OPS"
        return self.roster_text or "Working"


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def norm_name(value: Any) -> str:
    text = norm_text(value)
    text = re.sub(r"[*{}()\[\]]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def name_key(value: Any) -> str:
    return norm_name(value).casefold()


def detect_assessment(text: Any) -> str | None:
    haystack = norm_text(text).casefold()
    if not haystack:
        return None
    for key, aliases in ASSESSMENT_ALIASES.items():
        if any(alias in haystack for alias in aliases):
            return key
    return None


def parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = norm_text(value)
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%b-%y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def rgb_from_cell(cell: Any) -> str:
    try:
        fill = cell.fill
        color = fill.fgColor
        if color.type == "rgb" and color.rgb:
            return color.rgb.upper()
        if color.type == "indexed" and color.indexed is not None:
            return f"INDEXED:{color.indexed}"
    except Exception:
        return ""
    return ""


def is_black(fill: str) -> bool:
    return fill in {"FF000000", "000000", "INDEXED:64", "INDEXED:8"}


def is_green(fill: str) -> bool:
    return fill.startswith("FF00") or fill in {"FF92D050", "FF00B050", "FF00FF00", "INDEXED:17", "INDEXED:50"}


def load_excel_bytes(raw: bytes, password: str = "") -> Workbook:
    if raw[:2] == b"PK":
        return load_workbook(io.BytesIO(raw), data_only=False)

    if raw[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        if msoffcrypto is None:
            raise ValueError("This workbook is encrypted. Install msoffcrypto-tool or save it unencrypted.")
        office = msoffcrypto.OfficeFile(io.BytesIO(raw))
        if office.is_encrypted():
            if not password:
                raise ValueError("The GLF workbook is encrypted. Enter its Excel password and run again.")
            decrypted = io.BytesIO()
            office.load_key(password=password)
            office.decrypt(decrypted)
            decrypted.seek(0)
            return load_workbook(decrypted, data_only=False)

    raise ValueError("Unsupported workbook format. Please save the file as a normal .xlsx workbook.")


def workbook_cells(wb: Workbook) -> dict[str, list[list[Cell]]]:
    result: dict[str, list[list[Cell]]] = {}
    for ws in wb.worksheets:
        rows: list[list[Cell]] = []
        for row in ws.iter_rows():
            rows.append([
                Cell(
                    value=cell.value,
                    fill=rgb_from_cell(cell),
                    comment=cell.comment.text if cell.comment else "",
                )
                for cell in row
            ])
        result[ws.title] = rows
    return result


def split_people(value: Any) -> list[str]:
    text = norm_text(value)
    text = re.sub(r"[{}]", "\n", text)
    pieces = re.split(r"\n|/|;|,", text)
    names = []
    for piece in pieces:
        candidate = norm_name(piece)
        if len(candidate) >= 3 and not re.fullmatch(r"[A-Z0-9\- ]+", candidate):
            names.append(candidate)
    return names


def looks_like_person(text: str) -> bool:
    if not text or len(text) < 4:
        return False
    if any(ch.isdigit() for ch in text):
        return False
    if text.casefold() in {"date", "working hours", "ops", "ward", "name"}:
        return False
    return bool(re.search(r"[A-Za-z].+\s+[A-Za-z]", text))


def parse_roster(wb: Workbook) -> tuple[dict[str, dict[date, Availability]], list[date]]:
    sheets = workbook_cells(wb)
    availability: dict[str, dict[date, Availability]] = defaultdict(lambda: defaultdict(Availability))
    all_dates: set[date] = set()

    for sheet_name, rows in sheets.items():
        if "ward" in sheet_name.casefold():
            date_row_idx = max(
                range(min(len(rows), 8)),
                key=lambda r: sum(1 for cell in rows[r] if parse_date(cell.value)),
                default=0,
            )
            date_cols = {c: parse_date(cell.value) for c, cell in enumerate(rows[date_row_idx]) if parse_date(cell.value)}
            for cdate in date_cols.values():
                all_dates.add(cdate)
            for r in range(date_row_idx + 1, len(rows)):
                ward = norm_text(rows[r][0].value if rows[r] else "")
                if not ward or ward.casefold() == "date":
                    continue
                for c, cdate in date_cols.items():
                    if c >= len(rows[r]):
                        continue
                    for person in split_people(rows[r][c].value):
                        key = name_key(person)
                        if not key or person.casefold() == "ops":
                            continue
                        slot = availability[key][cdate]
                        slot.wards.add(ward)
                        slot.is_working = True
            continue

        date_row_idx = max(
            range(min(len(rows), 10)),
            key=lambda r: sum(1 for cell in rows[r] if parse_date(cell.value)),
            default=0,
        )
        date_cols = {c: parse_date(cell.value) for c, cell in enumerate(rows[date_row_idx]) if parse_date(cell.value)}
        for cdate in date_cols.values():
            all_dates.add(cdate)
        for r in range(date_row_idx + 1, len(rows)):
            if not rows[r]:
                continue
            person = norm_name(rows[r][0].value)
            if not looks_like_person(person):
                continue
            key = name_key(person)
            for c, cdate in date_cols.items():
                if c >= len(rows[r]):
                    continue
                cell = rows[r][c]
                text = norm_text(cell.value)
                if text.casefold() in {"", "al", "mc", "off", "leave", "ph", "do", "x"}:
                    continue
                slot = availability[key][cdate]
                slot.roster_text = text or slot.roster_text
                slot.is_working = True
                if "glf" in text.casefold():
                    slot.is_glf = True
                if is_green(cell.fill) or "ops" in text.casefold() or re.fullmatch(r"(X\()?([A-Z]\d|DP|B|C\d|D\d|E\d|F\d)(\))?", text.strip()):
                    slot.is_ops = True
    return availability, sorted(all_dates)


def find_name_column(row: list[Cell]) -> int:
    for idx, cell in enumerate(row[:8]):
        text = norm_text(cell.value).casefold()
        if text in {"name", "pharmacist", "assessee", "assesses", "staff"}:
            return idx
    return 0


def parse_glf_tasks(wb: Workbook) -> list[Task]:
    tasks: list[Task] = []
    sheets = workbook_cells(wb)
    for sheet_name, rows in sheets.items():
        for header_idx, header in enumerate(rows[:40]):
            assessment_cols = {c: detect_assessment(cell.value) for c, cell in enumerate(header)}
            assessment_cols = {c: a for c, a in assessment_cols.items() if a}
            if len(assessment_cols) < 1:
                continue

            name_col = find_name_column(header)
            for r in range(header_idx + 1, len(rows)):
                row = rows[r]
                if name_col >= len(row):
                    continue
                assessee = norm_name(row[name_col].value)
                if not looks_like_person(assessee):
                    continue
                row_text = " ".join(norm_text(cell.value) for cell in row)
                row_avoid = set()
                if re.search(r"past|previous|cycle|assessor", row_text, re.I):
                    row_avoid.update(name_key(name) for name in split_people(row_text))

                for c, assessment in assessment_cols.items():
                    if c >= len(row):
                        continue
                    cell = row[c]
                    text = norm_text(cell.value)
                    if is_black(cell.fill):
                        continue
                    if text and re.search(r"pass|complete|done|exempt|n/a", text, re.I):
                        continue
                    if text and looks_like_person(text):
                        row_avoid.add(name_key(text))
                        continue
                    if text and not re.search(r"due|pending|assign|yes|y|to do|^$", text, re.I):
                        continue
                    tasks.append(Task(
                        assessee=assessee,
                        assessment=assessment,
                        source_sheet=sheet_name,
                        source_cell=f"{get_column_letter(c + 1)}{r + 1}",
                        avoid={n for n in row_avoid if n and n != name_key(assessee)},
                    ))
            break
    return dedupe_tasks(tasks)


def dedupe_tasks(tasks: list[Task]) -> list[Task]:
    seen = set()
    unique = []
    for task in tasks:
        key = (name_key(task.assessee), task.assessment, task.source_sheet, task.source_cell)
        if key in seen:
            continue
        seen.add(key)
        unique.append(task)
    return unique


def requirement_met(assessment: str, slot: Availability) -> bool:
    if not slot.is_working:
        return False
    if assessment in NEEDS_WARD:
        return bool(slot.wards)
    if assessment in NEEDS_OPS:
        return slot.is_ops
    return bool(slot.wards or slot.is_ops or slot.roster_text)


def schedule_tasks(tasks: list[Task], availability: dict[str, dict[date, Availability]], dates: list[date]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scheduled = []
    unscheduled = []
    load_by_assessor_day: dict[tuple[str, date], int] = defaultdict(int)
    mini_by_assessor_day: dict[tuple[str, date], int] = defaultdict(int)
    assessor_names = sorted(availability.keys())
    glf_days = {
        cdate
        for person_days in availability.values()
        for cdate, slot in person_days.items()
        if slot.is_glf
    }

    for task in sorted(tasks, key=lambda t: (t.assessment != "mini_cex", t.assessee)):
        assessee_key = name_key(task.assessee)
        best = None
        best_score = 10**9
        reasons = []

        for cdate in dates:
            assessee_slot = availability.get(assessee_key, {}).get(cdate, Availability())
            if not requirement_met(task.assessment, assessee_slot):
                continue
            strict_glf = cdate in glf_days
            for assessor_key in assessor_names:
                if assessor_key == assessee_key or assessor_key in task.avoid:
                    continue
                assessor_slot = availability[assessor_key].get(cdate, Availability())
                if not assessor_slot.is_working:
                    continue
                if strict_glf and not assessor_slot.is_glf:
                    continue
                day_key = (assessor_key, cdate)
                if load_by_assessor_day[day_key] >= MAX_DAILY_ASSESSMENTS:
                    continue
                if task.assessment == "mini_cex" and mini_by_assessor_day[day_key] >= MAX_DAILY_MINI_CEX:
                    continue
                score = load_by_assessor_day[day_key] * 10 + (0 if assessor_slot.is_glf else 4)
                if task.assessment in NEEDS_WARD and assessor_slot.wards & assessee_slot.wards:
                    score -= 3
                if score < best_score:
                    best_score = score
                    best = (cdate, assessor_key, assessee_slot, assessor_slot)

        if best is None:
            reasons.append("No date had a matching assessee location plus an available assessor within daily limits.")
            unscheduled.append({
                "assessee": task.assessee,
                "assessment": ASSESSMENT_LABELS[task.assessment],
                "source": f"{task.source_sheet}!{task.source_cell}",
                "reason": " ".join(reasons),
            })
            continue

        cdate, assessor_key, assessee_slot, assessor_slot = best
        load_by_assessor_day[(assessor_key, cdate)] += 1
        if task.assessment == "mini_cex":
            mini_by_assessor_day[(assessor_key, cdate)] += 1
        scheduled.append({
            "date": cdate.isoformat(),
            "assessee": task.assessee,
            "assessment": ASSESSMENT_LABELS[task.assessment],
            "assessor": display_name(assessor_key, availability),
            "assessee_location": assessee_slot.location,
            "assessor_location": assessor_slot.location,
            "source": f"{task.source_sheet}!{task.source_cell}",
        })
    return scheduled, unscheduled


def display_name(key: str, availability: dict[str, dict[date, Availability]]) -> str:
    # Name casing is reconstructed from the normalized key when the source row is not retained.
    return " ".join(part.capitalize() for part in key.split())


def write_schedule_xlsx(scheduled: list[dict[str, Any]], unscheduled: list[dict[str, Any]]) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUTPUT_DIR / f"final-glf-schedule-{stamp}.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Final Schedule"
    headers = ["Date", "Assessee", "Assessment", "Assessor", "Assessee Location", "Assessor Location", "Source"]
    ws.append(headers)
    for item in scheduled:
        ws.append([item["date"], item["assessee"], item["assessment"], item["assessor"], item["assessee_location"], item["assessor_location"], item["source"]])

    us = wb.create_sheet("Unscheduled")
    us.append(["Assessee", "Assessment", "Source", "Reason"])
    for item in unscheduled:
        us.append([item["assessee"], item["assessment"], item["source"], item["reason"]])

    for sheet in wb.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(horizontal="center")
        sheet.freeze_panes = "A2"
        for col_idx, column in enumerate(sheet.columns, 1):
            width = min(max(len(str(cell.value or "")) for cell in column) + 2, 42)
            sheet.column_dimensions[get_column_letter(col_idx)].width = width
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
    wb.save(out)
    return out


def run_scheduler(roster_raw: bytes, glf_raw: bytes, password: str) -> dict[str, Any]:
    roster_wb = load_excel_bytes(roster_raw)
    glf_wb = load_excel_bytes(glf_raw, password=password)
    availability, dates = parse_roster(roster_wb)
    tasks = parse_glf_tasks(glf_wb)
    if not tasks:
        raise ValueError("No assignable GLF assessment cells were found. Check that the GLF overview has assessment headers and blank/due cells.")
    scheduled, unscheduled = schedule_tasks(tasks, availability, dates)
    out = write_schedule_xlsx(scheduled, unscheduled)
    return {
        "scheduled": scheduled,
        "unscheduled": unscheduled,
        "output": f"/outputs/{out.name}",
        "counts": {
            "tasks": len(tasks),
            "scheduled": len(scheduled),
            "unscheduled": len(unscheduled),
            "dates": len(dates),
            "people": len(availability),
        },
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/static/styles.css":
            self.serve_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
        elif path.startswith("/outputs/"):
            target = (OUTPUT_DIR / Path(path).name).resolve()
            if target.parent == OUTPUT_DIR.resolve() and target.exists():
                self.serve_file(target, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/api/schedule":
            self.send_error(404)
            return
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")},
        )
        try:
            roster = form["roster"].file.read()
            glf = form["glf"].file.read()
            password = form.getfirst("password", "")
            result = run_scheduler(roster, glf, password)
            self.send_json(result)
        except Exception as exc:
            self.send_json({"error": html.escape(str(exc))}, status=400)

    def serve_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    STATIC_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Scheduler website running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
