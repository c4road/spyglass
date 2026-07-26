"""Lens registry — the single list ``app.py`` reads to build the sidebar.

To add a new SpyGlass tool: write ``lenses/your_tool.py`` with a ``Lens``
subclass, import it here, and append an instance to ``LENSES``. Nothing else
changes. Order here is the order shown in the sidebar.
"""

from lenses.base import Lens
from lenses.position_sizer import PositionSizerLens

# The registered lenses, in sidebar order. Add new tools here.
LENSES: list[Lens] = [
    PositionSizerLens(),
]

__all__ = ["Lens", "LENSES"]
