# interrupcion.py

import streamlit as st
from datetime import datetime

from db import coleccion_eventos
from config import colombia


# =========================
# REGISTRO FINAL
# =========================
def guardar_interrupcion(data):
    coleccion_eventos.insert_one(data)


# =========================
# FLUJO LINEAL
# =========================
def mostrar_interrupcion():

    # =========================
    # INIT
    # =========================
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

    # =========================
    # PASOS DEL LIBRETO
    # =========================
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

    # =========================
    # BLOQUEO SI YA CERRÓ
    # =========================
    if st.session_state["interrupcion_cerrada"]:
        st.success("✔ Interrupción cerrada")

        if st.button("📑 Ver historial"):
            st.session_state["ir_historial"] = True
            st.rerun()

        return

    # =========================
    # INICIO
    # =========================
    if paso == 0:
        st.markdown("## 🔴 Interrupción")

        if st.button("🔘 Empezar"):
            st.session_state["interrupcion_inicio"] = datetime.now(colombia)
            st.session_state["paso_interrupcion"] = 1
            st.rerun()

    # =========================
    # LIBRETO
    # =========================
    elif 1 <= paso <= len(flujo):

        texto = flujo[paso - 1]
        st.write(texto)

        if paso < len(flujo):
            if st.button("¿Y luego?"):
                st.session_state["paso_interrupcion"] += 1
                st.rerun()

        else:
            st.markdown("### ¿Cómo quedaría o he quedado?")

            st.session_state["interrupcion_texto"] = st.text_area(
                "",
                value=st.session_state["interrupcion_texto"]
            )

            if st.button("Continuar"):
                st.session_state["paso_interrupcion"] += 1
                st.rerun()

    # =========================
    # CORTE
    # =========================
    elif paso == len(flujo) + 1:

        st.write("Ya sabés cómo termina")

        if st.button("🔴 Cortar"):
            st.session_state["interrupcion_fin"] = datetime.now(colombia)
            st.session_state["paso_interrupcion"] += 1
            st.rerun()

    # =========================
    # CÁLCULO Y GUARDADO
    # =========================
    elif paso == len(flujo) + 2:

        inicio = st.session_state.get("interrupcion_inicio")
        fin = st.session_state.get("interrupcion_fin")

        # =========================
        # DURACIÓN
        # =========================
        duracion_min = None
        if inicio and fin:
            try:
                duracion_min = int((fin - inicio).total_seconds() // 60)
            except:
                duracion_min = None

        # =========================
        # GAP
        # =========================
        gap_min = None

        ultimo = coleccion_eventos.find_one(
            {"evento": "interrupcion"},
            sort=[("fecha_hora", -1)]
        )

        if ultimo:
            fin_anterior = ultimo.get("fin")

            if inicio and fin_anterior:
                try:
                    gap_min = int((inicio - fin_anterior).total_seconds() // 60)
                except:
                    gap_min = None

        # =========================
        # GUARDAR (UNA SOLA VEZ)
        # =========================
        if not st.session_state["interrupcion_guardada"]:

            data = {
                "evento": "interrupcion",
                "inicio": inicio,
                "fin": fin,
                "duracion_min": duracion_min,
                "desde_anterior_min": gap_min,
                "texto": st.session_state.get("interrupcion_texto", ""),
                "fecha_hora": fin or datetime.now(colombia)
            }

            guardar_interrupcion(data)
            st.session_state["interrupcion_guardada"] = True

        # =========================
        # FEEDBACK
        # =========================
        if duracion_min is not None:
            st.success(f"Duración del impulso: {duracion_min} min")
        else:
            st.warning("Duración no disponible")

        if gap_min is not None:
            st.info(f"Tiempo desde el anterior: {gap_min} min")
        else:
            st.caption("Sin registro anterior")

        # =========================
        # CIERRE UX
        # =========================
        st.markdown("---")
        st.markdown("### ✔ Cerrado")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Listo"):
                st.session_state["interrupcion_cerrada"] = True
                st.rerun()

        with col2:
            if st.button("📑 Ir a historial"):
                st.session_state["ir_historial"] = True
                st.session_state["interrupcion_cerrada"] = True
                st.rerun()