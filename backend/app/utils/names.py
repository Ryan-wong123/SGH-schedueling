from __future__ import annotations

import re


def normalize_name(name: object) -> str:
    if name is None:
        return ""
    return re.sub(r"\s+", " ", str(name).replace("\xa0", " ")).strip().casefold()


def names_match(a: object, b: object) -> bool:
    return normalize_name(a) == normalize_name(b)


def names_prefix_match(longer_name: str, shorter_name: str) -> bool:
    longer = normalize_name(longer_name)
    shorter = normalize_name(shorter_name)
    return bool(shorter and longer and (longer == shorter or longer.startswith(shorter + " ")))
