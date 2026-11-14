"""Color normalization for imported units.

Supplier files may write a unit's color in English or Chinese, in any casing.
Known foreign-language names are translated to the Spanish name the app uses
(the same vocabulary as the units UI, see ``frontend/lib/colors.ts``). Anything
else, including Spanish names, is kept exactly as the supplier wrote it.
"""

from typing import Optional

# Canonical Spanish name (uppercase, as the app stores colors) -> lowercase
# aliases in other languages.
_COLOR_ALIASES: dict[str, tuple[str, ...]] = {
    "NEGRO": ("black", "黑色"),
    "ROJO": ("red", "红色"),
    "AZUL": ("blue", "蓝色"),
    "BLANCO": ("white", "白色"),
    "VERDE": ("green", "绿色"),
    "GRIS": ("grey", "gray", "灰色"),
    "AMARILLO": ("yellow", "黄色"),
    "NARANJA": ("orange", "橙色"),
    "ROSA": ("pink", "粉色"),
}

_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in _COLOR_ALIASES.items()
    for alias in aliases
}


def normalize_color(value: Optional[str]) -> Optional[str]:
    """Translate a foreign-language color name to its Spanish equivalent.

    Matching ignores case and surrounding whitespace, so ``"Black"``, ``"BLACK"``
    and ``" black "`` all become ``"NEGRO"``. Values with no known alias are
    returned unchanged (stripped), so Spanish or unknown colors are never lost.
    """
    if value is None:
        return None
    text = str(value).strip()
    return _ALIAS_TO_CANONICAL.get(text.lower(), text)
