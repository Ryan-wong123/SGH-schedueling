from __future__ import annotations

import io
import json
import re
import tempfile
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import msoffcrypto
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

try:
    import cgi
except ModuleNotFoundError:  # pragma: no cover - provided by legacy-cgi on newer Python
    import legacy_cgi as cgi


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
OUTPUTS = Path(tempfile.gettempdir()) / "glf_scheduler_outputs"
HOST = "127.0.0.1"
PORT = 8000

ASSESSMENT_COLUMNS = {
    7: "Mini-CEX",
    8: "CBD",
    9: "Med Recon",
    10: "Dispensing",
    11: "Rx Check",
}

ASSESSMENT_REQUIREMENTS = {
    "Mini-CEX": "ward",
    "CBD": "general",
    "Med Recon": "ward",
    "Dispensing": "ops",
    "Rx Check": "general",
}

NON_WORKING_MARKERS = {
    "VL",
    "V L",
    "WL",
    "FCL",
    "PHOIL",
    "OIL",
    "HL",
    "ML",
    "AL",
    "CL",
    "OFF",
    "REST",
    "D",
    "N",
    "O",
}

COMPLETED_MARKERS = {
    "COMPLETED",
    "COMPLETE",
    "PASSED",
    "PASS",
    "DONE",
    "EXEMPT",
    "NA",
    "N/A",
    "NOT APPLICABLE",
}

OPS_MARKERS = {"OPS", "O-OPS", "OP", "DP SHIFT", "OPS IC"}
GREEN_FILLS = {"FF92D050", "FF00B050", "FF008000", "FF70AD47", "FF00FF00"}


@dataclass
class DayAvailability:
    glf: bool = False
    working: bool = False
    ops: bool = False
    wards: set[str] = field(default_factory=set)
    raw: list[str] = field(default_factory=list)


@dataclass
class Task:
    row: int
    col: int
    student: str
    assessment: str
    requirement: str


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\xa0", " ").strip()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_name(value: Any) -> str:
    text = clean_text(value)
    text = re.sub(r"[\{\}\[\]]", "", text)
    text = text.replace("*", "")
    text = re.sub(r"\([^)]*(?:float|floater)[^)]*\)", "", text, flags=re.I)
    return normalize_space(text)


def normalize_key(value: Any) -> str:
    return normalize_name(value).casefold()


def split_people(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    pieces = re.split(r"[\n,;/]+", text)
    names = []
    for piece in pieces:
        cleaned = normalize_name(piece)
        if cleaned and not looks_like_activity(cleaned):
            names.append(cleaned)
    return names


def canonical_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def cell_fill_rgb(cell: Cell) -> str:
    color = cell.fill.fgColor
    if color.type == "rgb" and color.rgb:
        return color.rgb.upper()
    return ""


def is_black_cell(cell: Cell) -> bool:
    return cell.fill.fill_type == "solid" and cell_fill_rgb(cell) in {"FF000000", "000000"}


def is_green_cell(cell: Cell) -> bool:
    return cell_fill_rgb(cell) in GREEN_FILLS


def looks_like_activity(text: str) -> bool:
    upper = normalize_space(text).upper()
    if not upper:
        return True
    if upper in NON_WORKING_MARKERS or upper in OPS_MARKERS:
        return True
    if upper == "GLF":
        return True
    return False


def looks_working(text: str) -> bool:
    upper = normalize_space(text).upper()
    if not upper:
        return False
    if upper in NON_WORKING_MARKERS:
        return False
    return True


def looks_ops(text: str, cell: Cell | None = None) -> bool:
    upper = normalize_space(text).upper()
    if any(marker in upper for marker in OPS_MARKERS):
        return True
    if re.fullmatch(r"[BC]\d?|\(?C\d\)?|X\(C\d\)|B\+|D\+|F|E", upper):
        return True
    return bool(cell and is_green_cell(cell))


def ward_tokens(text: str) -> set[str]:
    text = normalize_space(text).upper()
    tokens = set()
    for token in re.findall(r"\b\d{2}[A-Z]?(?:/[A-Z])?|\bAMW\d\b|\bACC\d\b|\bRS-\d\b|\bRICA\b|\bMICU\b|\bNICU-\d\b|\bCCU\b|\bCVM\b|\bIC\b|\bMIC\b", text):
        tokens.add(token)
    return tokens


def read_workbook(upload: bytes, password: str = ""):
    stream = io.BytesIO(upload)
    try:
        return load_workbook(stream)
    except Exception as first_error:
        stream.seek(0)
        try:
            office = msoffcrypto.OfficeFile(stream)
            if not office.is_encrypted():
                raise first_error
            if not password:
                raise ValueError("The GLF workbook is encrypted. Enter its password and try again.")
            decrypted = io.BytesIO()
            office.load_key(password=password)
            office.decrypt(decrypted)
            decrypted.seek(0)
            return load_workbook(decrypted)
        except ValueError:
            raise
        except Exception as decrypt_error:
            raise ValueError("Unable to open the encrypted workbook. Check the password and try again.") from decrypt_error


def find_date_columns(ws) -> dict[int, date]:
    best: dict[int, date] = {}
    for row in range(1, min(ws.max_row, 12) + 1):
        found = {}
        for col in range(1, ws.max_column + 1):
            header_date = canonical_date(ws.cell(row, col).value)
            if header_date:
                found[col] = header_date
        if len(found) > len(best):
            best = found
    return best


def get_availability(availability: dict[str, dict[date, DayAvailability]], name: str, when: date) -> DayAvailability:
    key = normalize_key(name)
    return availability[key].setdefault(when, DayAvailability())


def parse_roster_workbook(wb) -> tuple[dict[str, dict[date, DayAvailability]], dict[str, str], list[date]]:
    availability: dict[str, dict[date, DayAvailability]] = defaultdict(dict)
    display_names: dict[str, str] = {}
    roster_dates: set[date] = set()

    for ws in wb.worksheets:
        dates = find_date_columns(ws)
        if not dates:
            continue
        roster_dates.update(dates.values())
        is_ward_sheet = "ward" in ws.title.casefold()

        if is_ward_sheet:
            for row in range(1, ws.max_row + 1):
                ward_label = clean_text(ws.cell(row, 1).value)
                ward_set = ward_tokens(ward_label) or {normalize_space(ward_label).upper()} if ward_label else set()
                if not ward_set:
                    continue
                for col, when in dates.items():
                    for person in split_people(ws.cell(row, col).value):
                        key = normalize_key(person)
                        display_names.setdefault(key, person)
                        day = get_availability(availability, person, when)
                        day.working = True
                        day.wards.update(ward_set)
                        if "OPS" in ward_label.upper():
                            day.ops = True
            continue

        for row in range(1, ws.max_row + 1):
            name = normalize_name(ws.cell(row, 1).value)
            if not name:
                continue
            key = normalize_key(name)
            display_names.setdefault(key, name)
            for col, when in dates.items():
                cell = ws.cell(row, col)
                text = clean_text(cell.value)
                if not text and not is_green_cell(cell):
                    continue
                day = get_availability(availability, name, when)
                day.raw.append(text)
                if looks_working(text) or is_green_cell(cell):
                    day.working = True
                if "GLF" in text.upper():
                    day.glf = True
                    day.working = True
                if looks_ops(text, cell):
                    day.ops = True
                day.wards.update(ward_tokens(text))

    return availability, display_names, sorted(roster_dates)


def find_assessment_headers(ws) -> dict[int, str]:
    headers = ASSESSMENT_COLUMNS.copy()
    known = {
        "MINI": "Mini-CEX",
        "CEX": "Mini-CEX",
        "CBD": "CBD",
        "MED": "Med Recon",
        "RECON": "Med Recon",
        "DISP": "Dispensing",
        "RX": "Rx Check",
        "CHECK": "Rx Check",
    }
    for row in range(1, min(ws.max_row, 40) + 1):
        found = {}
        for col in ASSESSMENT_COLUMNS:
            text = clean_text(ws.cell(row, col).value).upper()
            for needle, label in known.items():
                if needle in text:
                    found[col] = label
                    break
        if len(found) >= 3:
            headers.update(found)
            break
    return headers


def extract_existing_assessor(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return ""
    first_line = normalize_space(text.splitlines()[0])
    first_line = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "", first_line)
    first_line = re.sub(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}\b", "", first_line)
    first_line = re.sub(r"\b(?:on|date)\b.*$", "", first_line, flags=re.I)
    return normalize_name(first_line)


def is_completed_cell(cell: Cell) -> bool:
    if is_black_cell(cell):
        return True
    text = normalize_space(clean_text(cell.value)).upper()
    if not text:
        return False
    return text in COMPLETED_MARKERS or any(marker == text for marker in COMPLETED_MARKERS)


def is_non_assessee_row(student: str) -> bool:
    upper = normalize_space(student).upper()
    if not upper:
        return True
    if upper in {"NAME", "STUDENT", "ASSESSEE", "LEGEND"}:
        return True
    if re.fullmatch(r"[YZ]\d+", upper):
        return True
    if "GLF ASSESSMENT" in upper or "NEW PRE-REG" in upper:
        return True
    if "ARRANGE FOR" in upper or "ROTATION IN" in upper:
        return True
    return False


def parse_glf_tasks(wb) -> tuple[Any, list[Task], dict[str, set[str]], dict[str, int]]:
    if len(wb.worksheets) < 2:
        raise ValueError("The GLF workbook must contain at least two worksheets.")
    ws = wb.worksheets[1]
    headers = find_assessment_headers(ws)
    tasks: list[Task] = []
    existing_by_student: dict[str, set[str]] = defaultdict(set)
    stats = Counter()

    for row in range(1, ws.max_row + 1):
        student = normalize_name(ws.cell(row, 1).value)
        if is_non_assessee_row(student):
            continue
        student_key = normalize_key(student)
        for col in ASSESSMENT_COLUMNS:
            cell = ws.cell(row, col)
            value = clean_text(cell.value)
            if value:
                existing = extract_existing_assessor(value)
                if existing:
                    existing_by_student[student_key].add(normalize_key(existing))
            if is_completed_cell(cell):
                stats["completed_or_exempt"] += 1
                continue
            if value:
                stats["already_assigned"] += 1
                continue
            assessment = headers[col]
            tasks.append(Task(row, col, student, assessment, ASSESSMENT_REQUIREMENTS[assessment]))
            stats["pending"] += 1

    return ws, tasks, existing_by_student, dict(stats)


def student_activity_match(student_day: DayAvailability, requirement: str) -> bool:
    if requirement == "ops":
        return student_day.ops
    if requirement == "ward":
        return bool(student_day.wards)
    return bool(student_day.wards or student_day.ops)


def eligible_dates_for_student(student: str, availability: dict[str, dict[date, DayAvailability]], dates: list[date]) -> list[date]:
    student_days = availability.get(normalize_key(student), {})
    return [when for when in dates if student_days.get(when) and student_days[when].working]


def schedule_tasks(
    tasks: list[Task],
    availability: dict[str, dict[date, DayAvailability]],
    display_names: dict[str, str],
    roster_dates: list[date],
    existing_by_student: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assignments = []
    unscheduled = []
    total_load = Counter()
    daily_load = Counter()
    daily_mini = Counter()
    assigned_by_student: dict[str, set[str]] = defaultdict(set)

    assessor_keys = sorted(
        key for key, days in availability.items() if any(day.glf and day.working for day in days.values())
    )

    for task in tasks:
        student_key = normalize_key(task.student)
        student_days = availability.get(student_key, {})
        candidates = []
        for when in eligible_dates_for_student(task.student, availability, roster_dates):
            s_day = student_days[when]
            for assessor_key in assessor_keys:
                if assessor_key == student_key:
                    continue
                if assessor_key in existing_by_student[student_key]:
                    continue
                assessor_day = availability[assessor_key].get(when)
                if not assessor_day or not assessor_day.glf or not assessor_day.working:
                    continue
                if daily_load[(assessor_key, when)] >= 4:
                    continue
                if task.assessment == "Mini-CEX" and daily_mini[(assessor_key, when)] >= 2:
                    continue
                if not student_activity_match(s_day, task.requirement):
                    continue
                repeat_penalty = 1 if assessor_key in assigned_by_student[student_key] else 0
                candidates.append(
                    (
                        repeat_penalty,
                        total_load[assessor_key],
                        daily_load[(assessor_key, when)],
                        when,
                        assessor_key,
                    )
                )

        if not candidates:
            unscheduled.append(
                {
                    "student": task.student,
                    "assessment": task.assessment,
                    "row": task.row,
                    "reason": "No eligible GLF/date/location match found",
                }
            )
            continue

        _, _, _, when, assessor_key = min(candidates)
        assessor = display_names.get(assessor_key, assessor_key.title())
        assignment = {
            "row": task.row,
            "col": task.col,
            "student": task.student,
            "assessment": task.assessment,
            "assessor": assessor,
            "date": when,
        }
        assignments.append(assignment)
        total_load[assessor_key] += 1
        daily_load[(assessor_key, when)] += 1
        if task.assessment == "Mini-CEX":
            daily_mini[(assessor_key, when)] += 1
        assigned_by_student[student_key].add(assessor_key)

    return assignments, unscheduled


def apply_assignments(ws, assignments: list[dict[str, Any]]) -> None:
    for item in assignments:
        when: date = item["date"]
        cell = ws.cell(item["row"], item["col"])
        cell.value = f"{item['assessor']}\n{when.strftime('%d %b %Y')}"
        cell.alignment = cell.alignment.copy(wrap_text=True)


def schedule_workbooks(roster_bytes: bytes, glf_bytes: bytes, password: str) -> tuple[Path, dict[str, Any]]:
    roster_wb = read_workbook(roster_bytes)
    glf_wb = read_workbook(glf_bytes, password=password)

    availability, display_names, roster_dates = parse_roster_workbook(roster_wb)
    glf_ws, tasks, existing_by_student, task_stats = parse_glf_tasks(glf_wb)
    assignments, unscheduled = schedule_tasks(tasks, availability, display_names, roster_dates, existing_by_student)
    apply_assignments(glf_ws, assignments)

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUTS / f"GLF_Assessment_Overview_scheduled_{uuid.uuid4().hex[:10]}.xlsx"
    glf_wb.save(output_path)

    assigned_by_assessor = Counter(item["assessor"] for item in assignments)
    summary = {
        "scheduled": len(assignments),
        "unscheduled": len(unscheduled),
        "pending": len(tasks),
        "stats": task_stats,
        "dateRange": [d.isoformat() for d in roster_dates],
        "assessorLoad": dict(assigned_by_assessor.most_common()),
        "assignments": [
            {**item, "date": item["date"].isoformat()} for item in assignments[:100]
        ],
        "unscheduledItems": unscheduled[:100],
    }
    return output_path, summary


class SchedulerHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        if path == "/":
            return str(STATIC / "index.html")
        if path.startswith("/static/"):
            return str(ROOT / path.lstrip("/"))
        if path.startswith("/download/"):
            filename = Path(path).name
            return str(OUTPUTS / filename)
        return str(STATIC / path.lstrip("/"))

    def do_POST(self) -> None:
        if self.path != "/api/schedule":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
                },
            )
            roster_item = form["roster"] if "roster" in form else None
            glf_item = form["glf"] if "glf" in form else None
            password = form.getfirst("password", "")
            if roster_item is None or glf_item is None:
                raise ValueError("Upload both the roster workbook and GLF assessment workbook.")

            output_path, summary = schedule_workbooks(roster_item.file.read(), glf_item.file.read(), password)
            self.send_json(
                {
                    "ok": True,
                    "downloadUrl": f"/download/{output_path.name}",
                    "summary": summary,
                }
            )
        except Exception as error:
            self.send_json({"ok": False, "error": str(error)}, status=HTTPStatus.BAD_REQUEST)

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    STATIC.mkdir(exist_ok=True)
    OUTPUTS.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), SchedulerHandler)
    print(f"GLF Scheduler running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
