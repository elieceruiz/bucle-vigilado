# interrupcion.py

import streamlit as st
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from db import coleccion_eventos
from config import colombia


def guardar_interrupcion(data):
    coleccion_eventos.insert_one(data)


def mostrar_interrupcion():

    # =========================
    # AUTOREFRESH
    # =========================
    st_autorefresh(interval=1000, key="refresh_interrupcion")

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
    # ÚLTIMO REGISTRO (para tiempo en vivo)
    # =========================
    ultimo_global = coleccion_eventos.find_one(
        {"evento": "interrupcion"},
        sort=[("fecha_hora", -1)]
    )

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
    # INICIO (TIEMPO VISIBLE)
    # =========================
    if paso == 0:
        st.markdown("## 🔴 Interrupción")

        if ultimo_global:
            try:
                referencia = ultimo_global.get("fin") or ultimo_global.get("fecha_hora")
                referencia = referencia.astimezone(colombia)

                ahora = datetime.now(colombia)
                segundos = int((ahora - referencia).total_seconds())
                minutos = segundos // 60

                st.metric("🧭 Tiempo sin caer", f"{minutos} min")

                progreso = (segundos % 3600) / 3600
                st.progress(progreso)

            except:
                pass

        if st.button("🔘 Empezar"):
            st.session_state["interrupcion_inicio"] = datetime.now(colombia)
            st.session_state["paso_interrupcion"] = 1
            st.rerun()

    # =========================
    # LIBRETO
    # =========================
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
    # CIERRE + GUARDADO
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
                pass

        # =========================
        # BUSCAR EL ANTERIOR REAL
        # =========================
        anterior = None
        if inicio:
            anterior = coleccion_eventos.find_one(
                {
                    "evento": "interrupcion",
                    "fecha_hora": {"$lt": inicio}
                },
                sort=[("fecha_hora", -1)]
            )

        # =========================
        # GAP CORRECTO
        # =========================
        gap_min = None
        if anterior and inicio:
            try:
                referencia = anterior.get("fin") or anterior.get("fecha_hora")
                referencia = referencia.astimezone(colombia)

                gap_min = int((inicio - referencia).total_seconds() // 60)

                # blindaje: evitar negativos
                if gap_min < 0:
                    gap_min = None

            except:
                gap_min = None

        # =========================
        # GUARDAR
        # =========================
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

        # =========================
        # FEEDBACK
        # =========================
        if duracion_min is not None:
            st.success(f"⏱️ Impulso duró {duracion_min} min")

        if gap_min is not None:
            st.info(f"Desde el anterior: {gap_min} min")
        else:
            st.caption("Sin referencia anterior válida")

        # =========================
        # CONTEXTO FINAL
        # =========================
        if anterior and fin:
            try:
                referencia = anterior.get("fin") or anterior.get("fecha_hora")
                referencia = referencia.astimezone(colombia)

                minutos_post = int((fin - referencia).total_seconds() // 60)

                if minutos_post >= 0:
                    st.caption(f"🧭 Este corte ocurrió {minutos_post} min después del anterior")

            except:
                pass

        # =========================
        # CIERRE UX
        # =========================
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