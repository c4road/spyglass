"""Position Sizer — standalone SpyGlass lens (entry point).

Each lens is its own Streamlit app: this file is what you deploy and what you
run. It owns page config and layout; the inputs live in ``sidebar.py`` and the
results rendering in ``view.py``. Shared, pure logic stays in the repo-root
``core/`` package.

Run locally (from the repo root):
    streamlit run lenses/position_sizer/app.py
"""

from __future__ import annotations

import os
import sys

import streamlit as st

# Make the repo root importable so `core/` resolves when run via `streamlit run`
# from anywhere. This file is at <root>/lenses/position_sizer/app.py.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lenses.position_sizer.glossary import render_glossary  # noqa: E402
from lenses.position_sizer.sidebar import Inputs, render_sidebar  # noqa: E402
from lenses.position_sizer.view import render_results  # noqa: E402

TITLE = "Calculadora de Riesgo"
ICON = "🎯"
TAGLINE = "Gestión cuantitativa del riesgo, con el mismo marco que usan las instituciones."
DESCRIPTION = (
    "Las mesas institucionales no adivinan cuánto comprar: **derivan** el tamaño "
    "de la posición a partir de un presupuesto de riesgo y de la distribución real "
    "de retornos del activo. Esta herramienta hace exactamente eso — **VaR**, "
    "**CVaR** y **ATR** sobre datos de mercado en vivo — y te devuelve el número "
    "de acciones y el stop que respetan tu límite de pérdida. No es intuición ni "
    "corazonadas: es estadística aplicada a la gestión de capital."
)

st.set_page_config(page_title=f"SpyGlass · {TITLE}", page_icon=ICON, layout="wide")


def main() -> None:
    st.title(f"{ICON} {TITLE}")
    st.caption(TAGLINE)

    inputs: Inputs | None = render_sidebar()

    if inputs is None:
        # Landing state: sell the method, then teach the vocabulary.
        st.markdown(DESCRIPTION)
        st.info(
            "Completá el **ticker** y el **monto a arriesgar** en la barra "
            "lateral, y tocá **Calcular**."
        )
        render_glossary(expanded=True)
        return

    render_results(inputs)
    # Glossary echoes the confidence the user actually picked, so the "%" in the
    # copy always matches the numbers above it.
    render_glossary(expanded=False, confidence=inputs.confidence)


if __name__ == "__main__":
    main()
