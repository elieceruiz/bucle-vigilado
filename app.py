import streamlit as st
from datetime import datetime, timedelta

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
# SELECTOR
# =========================
seleccion = st.selectbox(
    "Seleccioná qué registrar o consultar:",
    list(eventos.keys())
)

opcion = eventos[seleccion]

# =========================
# 🔴 INTERRUPCIÓN (NEIL)
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

    # Mostrar confirmación si existe
    if "mensaje_guardado" in st.session_state:

        msg = st.session_state["mensaje_guardado"]

        st.success(
            f"✔ Capital registrado: {msg['capital']} COP\n\n"
            f"🎟️ Viajas hasta: {msg['fecha_futura']}"
        )

        st.session_state["borrar_mensaje"] = True

    # =========================
    # CAPITAL YNAB
    # =========================
    monto, objetivo, progreso = obtener_capital_desde_ynab()

    monto_formateado = (
        f"{monto:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    st.markdown(f"**Capital detectado en YNAB:** {monto_formateado} COP")

    # =========================
    # VENTAJA TEMPORAL
    # =========================
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

    # =========================
    # LÓGICA DE TIEMPO
    # =========================
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
            st.caption(f"Ventaja exacta: +{diferencia:,} minutos".replace(",", "."))

        elif diferencia == 0:

            fecha_futura = ahora

            st.info("Capital exactamente alineado con el tiempo actual")
            st.markdown(f"**Capital:** {monto_formateado} COP")

        else:

            atraso = abs(diferencia)
            fecha_futura = ahora

            st.warning(f"Atraso detectado: {atraso} minutos")
            st.markdown(f"**Capital:** {monto_formateado} COP")

        # GUARDAR
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

    # limpiar mensaje
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
        df = obtener_reflexiones()
        st.caption(f"Total de registros: {len(df)}")

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
