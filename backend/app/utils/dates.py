from __future__ import annotations

from datetime import date, datetime
from typing import Optional


TEXT_DATE_FORMATS = ("%d/%m/%y", "%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y")


def parse_date(value: object) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in TEXT_DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def format_date(value: object) -> str:
    parsed = parse_date(value)
    if parsed:
        return parsed.strftime("%d/%m/%y")
    return "" if value is None else str(value).strip()
