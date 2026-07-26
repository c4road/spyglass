"""SpyGlass — a set of focused trading & research lenses on the market.

Multi-lens Streamlit app: the sidebar picks a Lens (a self-contained tool) and
renders it. Tools live in ``lenses/`` and register themselves in
``lenses/__init__.py``; shared pure logic lives in ``core/``. Adding a tool is
one new file — this entry point never changes.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys

import streamlit as st

# Make sibling packages (lenses/, core/) importable when run via `streamlit run`.
sys.path.insert(0, os.path.dirname(__file__))

from lenses import LENSES  # noqa: E402  (after sys.path tweak)

st.set_page_config(page_title="SpyGlass", page_icon="🔭", layout="wide")


def main() -> None:
    st.sidebar.title("🔭 SpyGlass")
    st.sidebar.caption("Focused lenses on market risk. Pick a tool.")

    if not LENSES:
        st.error("No lenses registered.")
        return

    labels = [lens.label for lens in LENSES]
    choice = st.sidebar.radio("Lens", labels, label_visibility="collapsed")
    lens = LENSES[labels.index(choice)]

    st.sidebar.divider()
    st.sidebar.caption("Educational tools · not financial advice.")

    lens.render()


if __name__ == "__main__":
    main()
