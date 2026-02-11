"""
Font configuration for the Locus GUI.
Handles Chinese / English font resolution and provides font helper functions.
"""

import tkinter.font as tkfont
from i18n import get_lang


# Windows Chinese fonts in priority order
_ZH_FONT_CANDIDATES = [
    "Microsoft YaHei UI",   # 微软雅黑 UI — best for UI, ships with Win7+
    "Microsoft YaHei",      # 微软雅黑
    "SimHei",               # 黑体 — always available on Chinese Windows
    "DengXian",             # 等线 — Win10+ default
    "Source Han Sans SC",   # 思源黑体
    "Noto Sans CJK SC",    # Google Noto
]

_EN_FONT = "Segoe UI"
_MONO_FONT = "Consolas"
_EMOJI_FONT = "Segoe UI Emoji"

_zh_font_cache = None


def _resolve_zh_font(root=None) -> str:
    """Find the best available Chinese font on this system."""
    global _zh_font_cache
    if _zh_font_cache is not None:
        return _zh_font_cache

    available = set()
    try:
        if root:
            available = set(tkfont.families(root))
        else:
            available = set(tkfont.families())
    except Exception:
        pass

    for candidate in _ZH_FONT_CANDIDATES:
        if candidate in available:
            _zh_font_cache = candidate
            return candidate

    _zh_font_cache = _EN_FONT
    return _zh_font_cache


def ui_font(size: int = 11, bold: bool = False) -> tuple:
    """Return the correct UI font tuple for the current language."""
    if get_lang() == "zh":
        family = _resolve_zh_font()
    else:
        family = _EN_FONT
    if bold:
        return (family, size, "bold")
    return (family, size)


def mono_font(size: int = 10) -> tuple:
    return (_MONO_FONT, size)


def emoji_font(size: int = 48) -> tuple:
    return (_EMOJI_FONT, size)
