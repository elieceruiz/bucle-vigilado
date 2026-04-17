# interrupcion.py

import streamlit as st
from datetime import datetime

from db import coleccion_eventos
from config import colombia


# =========================
# REGISTRO
# =========================
def registrar_interrupcion(tipo, extra=None):
    coleccion_eventos.insert_one({
        "evento": "interrupcion",
        "tipo": tipo,
        "extra": extra,
        "fecha_hora": datetime.now(colombia)
    })


# =========================
# FLUJO NEIL
# =========================
def mostrar_interrupcion():

    if "paso_interrupcion" not in st.session_state:
        st.session_state["paso_interrupcion"] = 0

    paso = st.session_state["paso_interrupcion"]

    # =========================
    # INICIO
    # =========================
    if paso == 0:
        st.markdown("## 🔴 Interrupción")

        if st.button("🔘 Estoy a punto"):
            st.session_state["paso_interrupcion"] = 1
            st.rerun()

    # =========================
    # CONTEXTO
    # =========================
    elif paso == 1:
        st.write("¿Qué está pasando ahora mismo?")

        if st.button("Abrir incógnito"):
            registrar_interrupcion("inicio", "incognito")
            st.session_state["paso_interrupcion"] = 2
            st.rerun()

        if st.button("Escribirle a alguien"):
            registrar_interrupcion("inicio", "whatsapp")
            st.session_state["paso_interrupcion"] = 2
            st.rerun()

    # =========================
    # CADENA 1
    # =========================
    elif paso == 2:
        st.write("Si lo hacés… ¿qué pasa?")

        if st.button("Scrollear perfiles"):
            st.session_state["paso_interrupcion"] = 3
            st.rerun()

    # =========================
    # CADENA 2
    # =========================
    elif paso == 3:
        st.write("¿Y después?")

        if st.button("Contactar"):
            st.session_state["paso_interrupcion"] = 4
            st.rerun()

    # =========================
    # CONSECUENCIA
    # =========================
    elif paso == 4:
        st.write("Después de todo… ¿cómo te sentís?")

        if st.button("Derrotado"):
            registrar_interrupcion("resultado_anticipado", "derrota")
            st.session_state["paso_interrupcion"] = 5
            st.rerun()

    # =========================
    # RECONOCIMIENTO
    # =========================
    elif paso == 5:
        st.write("Ya sabés cómo termina.")

        if st.button("Sí, lo veo"):
            st.session_state["paso_interrupcion"] = 6
            st.rerun()

    # =========================
    # CONTEXTO FÍSICO
    # =========================
    elif paso == 6:
        st.write("¿Dónde estás ahora mismo?")

        if st.button("Solo, en mi cuarto, con el celular"):
            st.session_state["paso_interrupcion"] = 7
            st.rerun()

    # =========================
    # CORTE
    # =========================
    elif paso == 7:
        st.write("Cortá el acceso ahora.")

        if st.button("Modo avión"):
            registrar_interrupcion("corte", "modo_avion")
            st.session_state["paso_interrupcion"] = 8
            st.rerun()

        if st.button("Apagar celular"):
            registrar_interrupcion("corte", "apagar")
            st.session_state["paso_interrupcion"] = 8
            st.rerun()

        if st.button("Cerrar Edge"):
            registrar_interrupcion("corte", "cerrar_edge")
            st.session_state["paso_interrupcion"] = 8
            st.rerun()

    # =========================
    # REPORTE
    # =========================
    elif paso == 8:
        st.write("Volviste. ¿Qué hiciste?")

        if st.button("Caminé"):
            registrar_interrupcion("post", "camine")
            st.session_state["paso_interrupcion"] = 9
            st.rerun()

        if st.button("Nada (pero no caí)"):
            registrar_interrupcion("post", "resisti")
            st.session_state["paso_interrupcion"] = 9
            st.rerun()

    # =========================
    # IMPULSO
    # =========================
    elif paso == 9:
        st.write("¿El impulso bajó?")

        if st.button("Sí"):
            registrar_interrupcion("impulso", "bajo")
            st.session_state["paso_interrupcion"] = 10
            st.rerun()

        if st.button("Sigue"):
            registrar_interrupcion("impulso", "igual")
            st.session_state["paso_interrupcion"] = 10
            st.rerun()

    # =========================
    # FINAL
    # =========================
    elif paso == 10:
        st.success("Cortaste esto.")

        if st.button("Listo"):
            st.session_state["paso_interrupcion"] = 0
            st.rerun()
