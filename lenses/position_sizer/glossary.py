"""Glossary of the risk measures the lens reports — user-facing Spanish copy.

Kept out of ``view.py`` so the results renderer stays about results. Pure copy
plus Streamlit calls; no computation.

Accuracy note: the confidence level is a statement about the DAILY return
distribution — a 95% VaR is exceeded on ~5% of historical days. It is NOT a
promise that a trade survives 95% of the time: over a multi-day hold the chance
of touching the stop compounds, and the estimate is backward-looking. The copy
below says so explicitly rather than overselling the number.
"""

from __future__ import annotations

import streamlit as st

_TERMS = [
    (
        "VaR — Valor en Riesgo",
        """
**Qué es:** la pérdida diaria que sólo se supera en el **{tail}%** de los días.
Con una confianza del **{pct}%**, el VaR es el umbral que separa a los días
normales del **{tail}%** de días peores.

**Cómo se calcula acá:** de forma *histórica* — se ordenan los retornos diarios
reales del activo y se toma el percentil {tail}. No asume que el mercado sea una
campana de Gauss perfecta.

**Para qué te sirve:** poner el stop en el nivel del VaR {pct}% significa que,
mirando el historial, un día de mercado corriente **no** debería tocarlo: sólo
lo alcanzó el {tail}% de los días. Es ruido de mercado contra movimiento real.
""",
    ),
    (
        "CVaR — Pérdida Esperada en la Cola",
        """
**Qué es:** el promedio de las pérdidas *dentro* de ese peor **{tail}%** de días.
También se lo llama **Expected Shortfall**.

**La diferencia con el VaR:** el VaR te dice *dónde empieza* la zona mala; el
CVaR te dice **qué tan mala es en promedio** cuando entrás. El VaR ignora todo lo
que pasa más allá del umbral — el CVaR, no.

**Por qué es el método por defecto acá:** el CVaR ve las colas gordas (esos días
de pánico que el VaR recorta) y por construcción **siempre es ≥ VaR**, así que da
un stop más holgado y una posición más conservadora. Es la medida que Basilea III
adoptó en lugar del VaR para capital de riesgo de mercado.
""",
    ),
    (
        "ATR — Rango Verdadero Promedio",
        """
**Qué es:** cuánto se mueve el activo en un día típico, en dólares — promediando
el rango real de las últimas 14 ruedas (incluidos los *gaps* de apertura).

**En qué se diferencia:** VaR y CVaR miden *pérdidas* (sólo la cola izquierda);
el ATR mide **volatilidad** en ambas direcciones. No sabe de probabilidades: sabe
de amplitud.

**Para qué te sirve:** un stop de `entrada − 2×ATR` se adapta solo a cada activo.
Ese múltiplo (2, 3…) lo elegís vos según cuánto ruido querés tolerar antes de
salir.
""",
    ),
    (
        "Cómo se convierte todo eso en un tamaño de posición",
        """
La regla es **el riesgo primero**: vos fijás cuánto estás dispuesto a perder, y
ese número determina cuántas acciones comprás — nunca al revés.

```
riesgo por acción = entrada − stop
acciones          = $ a arriesgar ÷ riesgo por acción
```

Por eso un activo volátil (stop lejos) te da **menos** acciones y uno tranquilo
te da más: la pérdida en dólares si salta el stop es **la misma** en los dos
casos. Eso es lo que estandariza el riesgo entre operaciones.

Las acciones se redondean **hacia abajo** al lote, así que la pérdida real nunca
supera tu presupuesto.
""",
    ),
    (
        "Ajustarla todos los días: permanecer en tu intervalo de confianza",
        """
Acá está el punto clave: el VaR, el CVaR y el ATR **cambian con el mercado**. Si
elegís un stop hoy y lo dejás quieto, el nivel de confianza que creés tener se te
va desalineando a medida que la volatilidad se mueve.

**Ajustar la posición todos los días es lo que te mantiene *dentro* del intervalo
de confianza que elegiste.** No reduce el {tail}% — lo **sostiene** en {tail}%.
Si no reajustás, tu tasa real de rupturas se despega del {pct}% que pediste.

- **Si la volatilidad sube**, el nivel se ensancha: un stop que antes era
  razonable ahora queda *dentro* del ruido, y te sacan de la posición por
  movimientos que ya son normales.
- **Si la volatilidad baja**, el nivel se comprime: podés ajustar el stop y
  liberar riesgo que ya no necesitás tener expuesto.
- **Si el precio avanzó a tu favor**, subir el stop (*trailing*) va asegurando
  ganancia y reduce lo que todavía tenés en juego.

Eso es exactamente lo que hace una mesa institucional: recalibrar la exposición
contra el régimen de volatilidad **vigente**, no fijar un número y olvidarlo.
Correr esta herramienta a diario sobre tus posiciones abiertas es esa misma
rutina.

**Dos precisiones, para que quede claro qué te da y qué no:** el {pct}% *está
definido* como el nivel que se excede el {tail}% de las ruedas, así que reajustar
no elimina esos días malos — los mantiene en la frecuencia esperada en lugar de
dejarla derivar. Y ningún stop protege contra un **gap** de apertura, porque el
precio salta por encima de tu orden.
""",
    ),
]

_CAVEAT = """
**Los límites de esto — importante:**

- El **{pct}%** se refiere a **días históricos**, no a operaciones. Que el VaR
  {pct}% sea superado por el {tail}% de los días **no** significa que una
  operación tenga {pct}% de probabilidad de éxito: si la mantenés varias ruedas,
  las chances de tocar el stop se **acumulan** con el tiempo.
- Todo esto es **retrospectivo**: se calcula sobre lo que el activo ya hizo. Un
  régimen nuevo (una crisis, un *earnings*, una noticia) puede exceder cualquier
  cola histórica.
- Un **gap** de apertura puede saltear tu stop: se ejecuta al precio siguiente
  disponible, que puede ser peor. La pérdida "máxima" no está garantizada.
- Los cálculos asumen una posición **larga**, y que vos **respetás el stop**.
"""


def render_glossary(expanded: bool = False, confidence: float = 0.95) -> None:
    """Draw the glossary. ``expanded`` opens it (used on the landing screen)."""
    pct = int(round(confidence * 100))
    tail = int(round((1 - confidence) * 100))

    with st.expander("📘 Glosario — qué significa cada medida", expanded=expanded):
        st.caption(
            "Las tres medidas describen el riesgo desde ángulos distintos. "
            "Entenderlas es la diferencia entre usar la herramienta y confiar en ella."
        )
        for title, body in _TERMS:
            st.markdown(f"#### {title}")
            st.markdown(body.format(pct=pct, tail=tail).strip())
            st.divider()

        st.markdown(_CAVEAT.format(pct=pct, tail=tail).strip())
