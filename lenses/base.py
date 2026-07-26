"""The Lens protocol — the plugin contract every SpyGlass tool implements.

A SpyGlass has many *lenses*; each is one self-contained tool the user picks from
the sidebar. Adding a new lead-magnet tool = write one new module in ``lenses/``
that defines a ``Lens`` subclass and append it to the registry in
``lenses/__init__.py``. ``app.py`` never changes.

A Lens is intentionally minimal: an identity (name/icon/description) and a
``render()`` that draws its Streamlit UI. All heavy/pure logic lives in ``core/``
so lenses stay thin and the math stays testable without Streamlit.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Lens(ABC):
    """One pluggable SpyGlass tool.

    Subclasses set the class attributes and implement :meth:`render`.
    """

    #: Display name shown in the sidebar and header, e.g. "Position Sizer".
    name: str = "Unnamed Lens"
    #: An emoji shown next to the name, e.g. "🎯".
    icon: str = "🔭"
    #: One-line description shown under the header.
    description: str = ""

    @property
    def label(self) -> str:
        """Sidebar label — icon + name."""
        return f"{self.icon} {self.name}"

    @abstractmethod
    def render(self) -> None:
        """Draw this lens's Streamlit UI. Called when the lens is selected."""
        raise NotImplementedError
