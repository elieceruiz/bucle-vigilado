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
            # =========================
            # TEXTO FINAL
            # =========================
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
        # DURACIÓN (SEGURA)
        # =========================
        duracion_min = None
        if inicio and fin:
            try:
                duracion_min = int((fin - inicio).total_seconds() // 60)
            except:
                duracion_min = None

        # =========================
        # GAP DESDE ANTERIOR (BLINDADO)
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
        # GUARDAR
        # =========================
        data = {
            "evento": "interrupcion",
            "inicio": inicio,
            "fin": fin,
            "duracion_min": duracion_min,
            "desde_anterior_min": gap_min,
            "texto": st.session_state.get("interrupcion_texto", ""),
            "fecha_hora": fin or datetime.now(colombia)  # fallback
        }

        guardar_interrupcion(data)

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
        # RESET
        # =========================
        if st.button("Listo"):

            for k in [
                "paso_interrupcion",
                "interrupcion_inicio",
                "interrupcion_fin",
                "interrupcion_texto"
            ]:
                if k in st.session_state:
                    del st.session_state[k]

            st.rerun()