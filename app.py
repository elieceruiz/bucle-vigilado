# app.py

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# =========================
# IMPORTS PROPIOS
# =========================
from config import EVENTO_A, EVENTO_B, colombia
from db import coleccion_eventos, coleccion_capital_b
from helpers import (
    registrar_evento,
    mostrar_racha,
    obtener_registros,
    obtener_reflexiones,
    guardar_reflexion,
    minutos_a_tiempo_humano
)
from servicios import (
    obtener_capital_desde_ynab,
    obtener_minutos_evento_b,
    obtener_historial_capital_b
)
from interrupcion import mostrar_interrupcion

# =========================
# CONFIGURACIÓN
# =========================
st.set_page_config(page_title="Reinicia", layout="centered")
st.title("Reinicia")

# =========================
# EVENTOS (MENÚ)
# =========================
eventos = {
    "🔴 Interrupción": "interrupcion",
    "🧠": "reflexion",
    "📑 Historial": "historial",
    "✊🏽": EVENTO_A,
    "💸": EVENTO_B,
    "🧭 Viaje en el tiempo": "viaje_tiempo",
}

# =========================
# SELECTOR CONTROLADO
# =========================
if "seleccion" not in st.session_state:
    st.session_state["seleccion"] = list(eventos.keys())[0]

# Redirección desde interrupción → historial
if st.session_state.get("ir_historial"):
    st.session_state["seleccion"] = "📑 Historial"
    del st.session_state["ir_historial"]

seleccion = st.selectbox(
    "Seleccioná qué registrar o consultar:",
    list(eventos.keys()),
    key="seleccion"
)

opcion = eventos[seleccion]

# =========================
# CARGA ESTADO INICIAL
# =========================
for ev in [EVENTO_A, EVENTO_B]:
    if ev not in st.session_state:
        ultimo = coleccion_eventos.find_one(
            {"evento": ev},
            sort=[("fecha_hora", -1)]
        )
        if ultimo:
            st.session_state[ev] = ultimo["fecha_hora"].astimezone(colombia)

# =========================
# RESET INTERRUPCIÓN SI SALES
# =========================
if opcion != "interrupcion":
    for k in [
        "paso_interrupcion",
        "interrupcion_inicio",
        "interrupcion_fin",
        "interrupcion_texto",
        "interrupcion_cerrada",
        "interrupcion_guardada"
    ]:
        if k in st.session_state:
            del st.session_state[k]

# =========================
# 🔴 INTERRUPCIÓN
# =========================
if opcion == "interrupcion":
    mostrar_interrupcion()

# =========================
# ✊🏽 / 💸 EVENTOS
# =========================
elif opcion in [EVENTO_A, EVENTO_B]:

    if st.button("Registrar"):
        ahora = datetime.now(colombia)
        registrar_evento(opcion, ahora)
        st.session_state[opcion] = ahora
        st.rerun()

    mostrar_racha(opcion, seleccion)

# =========================
# 🧭 VIAJE EN EL TIEMPO
# =========================
elif opcion == "viaje_tiempo":

    if "mensaje_guardado" in st.session_state:
        msg = st.session_state["mensaje_guardado"]

        st.success(
            f"✔ Capital registrado: {msg['capital']} COP\n\n"
            f"🎟️ Viajas hasta: {msg['fecha_futura']}"
        )

        st.session_state["borrar_mensaje"] = True

    monto, objetivo, progreso = obtener_capital_desde_ynab()

    monto_formateado = (
        f"{monto:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    st.markdown(f"**Capital detectado en YNAB:** {monto_formateado} COP")

    tiempo_humano = minutos_a_tiempo_humano(round(monto))

    st.markdown("### ⏳ Ventaja temporal")

    st.metric(
        "Tiempo acumulado",
        f"+ {int(monto):,} minutos".replace(",", "."),
        tiempo_humano
    )

    years = monto / 525600
    st.caption(f"≈ {years:.2f} años de vida acumulados")

    objetivo_formateado = (
        f"{objetivo:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    st.markdown(f"**Objetivo YNAB:** {objetivo_formateado} COP")
    st.progress(min(max(progreso / 100, 0), 1))
    st.caption(f"{progreso}% del objetivo alcanzado")

    if monto > 0:

        minutos_actuales = obtener_minutos_evento_b()
        diferencia = int(monto - minutos_actuales)
        ahora = datetime.now(colombia)

        if diferencia > 0:
            fecha_futura = ahora + timedelta(minutes=diferencia)
            tiempo_adelanto = minutos_a_tiempo_humano(diferencia)

            st.success(f"{tiempo_adelanto}")
            st.markdown(f"**Capital:** {monto_formateado} COP")
            st.markdown(f"**Fecha equivalente futura:** {fecha_futura.strftime('%d-%m-%y %H:%M')}")

        elif diferencia == 0:
            fecha_futura = ahora
            st.info("Capital exactamente alineado con el tiempo actual")

        else:
            atraso = abs(diferencia)
            fecha_futura = ahora
            st.warning(f"Atraso detectado: {atraso} minutos")

        if "mensaje_guardado" not in st.session_state:
            if st.button("Guardar estado"):
                coleccion_capital_b.insert_one({
                    "fecha_registro": ahora,
                    "fecha_futura": fecha_futura,
                    "monto": monto
                })

                st.session_state["mensaje_guardado"] = {
                    "capital": monto_formateado,
                    "fecha_futura": fecha_futura.strftime("%d-%m-%y %H:%M")
                }

                st.rerun()

    if st.session_state.get("borrar_mensaje"):
        del st.session_state["mensaje_guardado"]
        del st.session_state["borrar_mensaje"]

# =========================
# 🧠 REFLEXIONES
# =========================
elif opcion == "reflexion":

    if "mensaje_reflexion" in st.session_state:

        msg = st.session_state["mensaje_reflexion"]

        st.success("🧠 Reflexión registrada")
        st.markdown(f"**Reflexión:** {msg['texto']}")
        st.markdown(f"**Categoría:** {msg['categoria']}")

        del st.session_state["mensaje_reflexion"]

    if st.session_state.get("limpiar_reflexion", False):
        st.session_state["texto_reflexion"] = ""
        st.session_state["emociones_reflexion"] = []
        st.session_state["limpiar_reflexion"] = False

    emociones = st.multiselect(
        "¿Cómo te sentías?",
        ["😰 Ansioso", "😡 Irritado", "💪 Firme", "😌 Aliviado",
         "😓 Culpable", "🥱 Apático", "😔 Triste"],
        key="emociones_reflexion"
    )

    texto = st.text_area("¿Querés dejar algo escrito?", key="texto_reflexion")

    if (texto.strip() or emociones) and st.button("📝 Guardar reflexión"):

        categoria = guardar_reflexion(datetime.now(colombia), emociones, texto)

        st.session_state["mensaje_reflexion"] = {
            "texto": texto.strip(),
            "categoria": categoria
        }

        st.session_state["limpiar_reflexion"] = True
        st.rerun()

# =========================
# 📑 HISTORIAL
# =========================
elif opcion == "historial":

    tabs = st.tabs(["🧠", "✊🏽", "💸", "🧭"])

    with tabs[0]:

        interrupciones = list(
            coleccion_eventos.find({"evento": "interrupcion"})
            .sort("fecha_hora", -1)
        )

        if interrupciones:
            st.markdown("### 🔴 Interrupciones")

            for r in interrupciones:
                fecha = r["fecha_hora"].astimezone(colombia)

                dur = r.get("duracion_min")
                gap = r.get("desde_anterior_min")
                texto = r.get("texto", "")

                with st.expander(fecha.strftime("%d-%m-%y %H:%M")):

                    if dur is not None:
                        st.markdown(f"**Duración:** {dur} min")

                    if gap is not None:
                        st.markdown(f"**Desde anterior:** {gap} min")

                    if texto:
                        if len(texto) > 300:
                            st.write(texto[:300] + "...")
                            with st.expander("Ver completo"):
                                st.write(texto)
                        else:
                            st.write(texto)

        df = obtener_reflexiones()

        st.markdown("### 🧠 Reflexiones")
        st.caption(f"Total: {len(df)}")

        for _, r in df.iterrows():
            with st.expander(f"{r['Fecha']} {r['Hora']} {r['Emociones']}"):
                st.write(r["Reflexión"])
                st.divider()
                st.markdown(f"**Categoría:** {r['Categoría']}")
                st.markdown(f"**Subcategoría:** {r['Subcategoría']}")

    with tabs[1]:
        st.dataframe(obtener_registros(EVENTO_A), use_container_width=True)

    with tabs[2]:
        st.dataframe(obtener_registros(EVENTO_B), use_container_width=True)

    with tabs[3]:
        df_cap = obtener_historial_capital_b()
        if not df_cap.empty:
            st.dataframe(df_cap, use_container_width=True)
        else:
            st.info("Sin registros aún")