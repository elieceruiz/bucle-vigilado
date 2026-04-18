# interrupcion.py

import streamlit as st
from datetime import datetime

from db import coleccion_eventos
from config import colombia


def guardar_interrupcion(data):
    coleccion_eventos.insert_one(data)


def mostrar_interrupcion():

    if "paso_interrupcion" not in st.session_state:
        st.session_state["paso_interrupcion"] = 0

    if "interrupcion_inicio" not in st.session_state:
        st.session_state["interrupcion_inicio"] = None

    if "interrupcion_fin" not in st.session_state:
        st.session_state["interrupcion_fin"] = None

    if "interrupcion_texto" not in st.session_state:
        st.session_state["interrupcion_texto"] = ""

    if "interrupcion_cerrada" not in st.session_state:
        st.session_state["interrupcion_cerrada"] = False

    if "interrupcion_guardada" not in st.session_state:
        st.session_state["interrupcion_guardada"] = False

    paso = st.session_state["paso_interrupcion"]

    flujo = [
        "A punto de abrir Edge.",
        "Pestaña en incógnito.",
        "Buscar.",
        "Scrollear.",
        "Elegir.",
        "Escribirle.",
        "Coordinar.",
        "Pagar.",
        "Encuentro."
    ]

    # TIEMPO DESDE ÚLTIMO
    ultimo_valido = coleccion_eventos.find_one(
        {"evento": "interrupcion", "fin": {"$ne": None}},
        sort=[("fecha_hora", -1)]
    )

    if ultimo_valido:
        try:
            minutos = int((datetime.now(colombia) - ultimo_valido["fin"]).total_seconds() // 60)
            st.info(f"🧭 Llevas {minutos} min desde el último impulso")
        except:
            pass

    if st.session_state["interrupcion_cerrada"]:
        st.success("✔ Interrupción cerrada")

        if st.button("📑 Ver historial"):
            st.session_state["ir_historial"] = True
            st.rerun()

        return

    if paso == 0:
        st.markdown("## 🔴 Interrupción")

        if st.button("🔘 Empezar"):
            st.session_state["interrupcion_inicio"] = datetime.now(colombia)
            st.session_state["paso_interrupcion"] = 1
            st.rerun()

    elif 1 <= paso <= len(flujo):

        st.write(flujo[paso - 1])

        if paso < len(flujo):
            if st.button("¿Y luego?"):
                st.session_state["paso_interrupcion"] += 1
                st.rerun()

        else:
            st.markdown("### ¿Cómo quedaría o he quedado?")
            st.caption("Sé directo. Qué pasó y cómo te sentiste.")

            st.session_state["interrupcion_texto"] = st.text_area(
                "",
                value=st.session_state["interrupcion_texto"]
            )

            if st.button("Continuar"):
                st.session_state["paso_interrupcion"] += 1
                st.rerun()

    elif paso == len(flujo) + 1:

        st.write("Ya sabés cómo termina")

        if st.button("🔴 Cortar"):
            st.session_state["interrupcion_fin"] = datetime.now(colombia)
            st.session_state["paso_interrupcion"] += 1
            st.rerun()

    elif paso == len(flujo) + 2:

        inicio = st.session_state.get("interrupcion_inicio")
        fin = st.session_state.get("interrupcion_fin")

        duracion_min = None
        if inicio and fin:
            try:
                duracion_min = int((fin - inicio).total_seconds() // 60)
            except:
                pass

        gap_min = None
        if ultimo_valido and inicio:
            try:
                gap_min = int((inicio - ultimo_valido["fin"]).total_seconds() // 60)
            except:
                pass

        if not st.session_state["interrupcion_guardada"]:
            guardar_interrupcion({
                "evento": "interrupcion",
                "inicio": inicio,
                "fin": fin,
                "duracion_min": duracion_min,
                "desde_anterior_min": gap_min,
                "texto": st.session_state.get("interrupcion_texto", ""),
                "fecha_hora": fin or datetime.now(colombia)
            })
            st.session_state["interrupcion_guardada"] = True

        if duracion_min is not None:
            st.success(f"⏱️ {duracion_min} min sin caer")

        if gap_min is not None:
            st.info(f"Desde el anterior: {gap_min} min")
        else:
            st.caption("Primer registro de seguimiento")

        st.markdown("### ✔ Cerrado")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✔ Cerrar"):
                st.session_state["interrupcion_cerrada"] = True
                st.rerun()

        with col2:
            if st.button("📑 Ir a historial"):
                st.session_state["ir_historial"] = True
                st.session_state["interrupcion_cerrada"] = True
                st.rerun()