from __future__ import annotations

from io import BytesIO

import msoffcrypto
from openpyxl import load_workbook

from app.utils.errors import AppError


WRONG_PASSWORD_MESSAGE = "Unable to open GLF Assessment Workbook. Please check the password and try again."


def _load_workbook(stream: BytesIO):
    try:
        return load_workbook(stream, data_only=False)
    except Exception as exc:
        raise AppError("Invalid Excel file.") from exc


def load_glf_workbook_from_bytes(data: bytes, password: str):
    if not password or not password.strip():
        raise AppError("GLF workbook password is required.")
    source = BytesIO(data)
    try:
        office_file = msoffcrypto.OfficeFile(source)
        if office_file.is_encrypted():
            decrypted = BytesIO()
            office_file.load_key(password=password)
            office_file.decrypt(decrypted)
            decrypted.seek(0)
            workbook = _load_workbook(decrypted)
        else:
            source.seek(0)
            workbook = _load_workbook(source)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(WRONG_PASSWORD_MESSAGE) from exc
    if len(workbook.worksheets) < 2:
        raise AppError("The GLF workbook must contain at least two worksheets.")
    return workbook


def load_roster_workbook_from_bytes(data: bytes):
    workbook = _load_workbook(BytesIO(data))
    if len(workbook.worksheets) < 2:
        raise AppError("The roster workbook must contain at least two worksheets.")
    return workbook
