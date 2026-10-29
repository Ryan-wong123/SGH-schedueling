from __future__ import annotations

import re
from typing import FrozenSet


def normalize_name(name: object) -> str:
    if name is None:
        return ""
    return re.sub(r"\s+", " ", str(name).replace("\xa0", " ")).strip().casefold()


def names_match(a: object, b: object) -> bool:
    return normalize_name(a) == normalize_name(b)


def name_tokens(name: object) -> FrozenSet[str]:
    # Bracketed notes such as "(Megan)" or "(DI/IP)" are not part of the name.
    text = re.sub(r"\([^)]*\)", " ", normalize_name(name))
    return frozenset(re.findall(r"[^\W_]+", text))


def names_token_match(full_name: object, short_name: object) -> bool:
    """True when every word of short_name appears in full_name, in any order.

    "Kelly Ho" matches "Ho Siang Kin Kelly" and "Kristy Chan" matches "Chan Xiao Ting, Kristy".
    """
    full = name_tokens(full_name)
    short = name_tokens(short_name)
    return bool(full and short and short <= full)
