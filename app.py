import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
import time
import re
from dateutil.relativedelta import relativedelta

# === CONFIGURACIÓN GENERAL ===
st.set_page_config(page_title="🌀 Bucle Vigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGODB ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === EVENTOS MONITOREADOS ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === CARGAR ÚLTIMOS EVENTOS ===
for evento in [evento_a, evento_b]:
    if evento not in st.session_state:
        doc = coleccion_eventos.find_one({"evento": evento}, sort=[("fecha_hora", -1)])
        if doc:
            st.session_state[evento] = doc["fecha_hora"].astimezone(colombia)

# === FUNCIÓN PARA REGISTRAR EVENTO ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[nombre_evento] = fecha_hora

# === FUNCIÓN PARA GUARDAR REFLEXIÓN ===
def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === MENÚ DESPLEGABLE ===
opcion = st.selectbox("Selecciona una opción:", [
    "Registrar reflexión",
    "Racha la iniciativa aquella",
    "Racha la iniciativa de pago",
    "Historial",
    "Registrar evento"
])

# === REGISTRAR REFLEXIÓN ===
if opcion == "Registrar reflexión":
    st.header("🧠 Reflexión")
    emociones_opciones = [
        "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
        "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
    ]
    emociones = st.multiselect("¿Cómo te sentías?", emociones_opciones)
    reflexion = st.text_area("¿Querés dejar algo escrito?", height=150)
    palabras = len(re.findall(r'\b\w+\b', reflexion))
    st.caption(f"📄 Palabras: {palabras}")
    if st.button("📝 Guardar"):
        if reflexion.strip() or emociones:
            guardar_reflexion(datetime.now(colombia), emociones, reflexion)
            st.success("✅ Reflexión guardada.")
        else:
            st.warning("Debes escribir algo o elegir al menos una emoción.")

# === RACHAS CON CRONÓMETRO ===
elif opcion in ["Racha la iniciativa aquella", "Racha la iniciativa de pago"]:
    st.header("⏱️ Racha activa")
    evento = evento_a if "aquella" in opcion else evento_b
    if evento in st.session_state:
        inicio = st.session_state[evento]
        cronometro = st.empty()
        detalle = st.empty()
        while True:
            ahora = datetime.now(colombia)
            delta = ahora - inicio
            minutos = int(delta.total_seconds() // 60)
            rdelta = relativedelta(ahora, inicio)
            tiempo_str = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
            cronometro.metric("⏳ Minutos", f"{minutos:,}".replace(",", "."))  # Separador de miles con punto
            detalle.caption(tiempo_str)
            time.sleep(1)
            st.experimental_rerun()
    else:
        st.info("No hay eventos registrados para esta categoría.")

# === HISTORIAL COMPLETO ===
elif opcion == "Historial":
    st.header("📑 Historial de eventos y reflexiones")

    def mostrar_historial(evento_nombre):
        eventos = list(coleccion_eventos.find({"evento": evento_nombre}).sort("fecha_hora", -1))
        if eventos:
            datos = [{
                "Fecha": e["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d"),
                "Hora": e["fecha_hora"].astimezone(colombia).strftime("%H:%M")
            } for e in eventos]
            st.subheader(evento_nombre)
            st.dataframe(pd.DataFrame(datos), use_container_width=True, hide_index=True)
        else:
            st.warning(f"No hay eventos registrados para {evento_nombre}")

    mostrar_historial(evento_a)
    mostrar_historial(evento_b)

    st.subheader("🧠 Reflexiones")
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    if docs:
        for doc in docs:
            fecha = doc["fecha_hora"].astimezone(colombia)
            emociones = " ".join(e["emoji"] for e in doc.get("emociones", []))
            with st.expander(f"{fecha.strftime('%Y-%m-%d %H:%M')} — {emociones}"):
                st.write(doc.get("reflexion", ""))
    else:
        st.info("No hay reflexiones registradas.")

# === REGISTRAR EVENTO MANUAL O AUTOMÁTICO ===
elif opcion == "Registrar evento":
    st.header("📍 Registrar evento")
    col1, col2 = st.columns(2)
    with col1:
        check_a = st.checkbox("✊🏽 La Iniciativa Aquella")
    with col2:
        check_b = st.checkbox("💸 La Iniciativa de Pago")

    usar_manual = st.checkbox("Ingresar fecha y hora manualmente")
    if usar_manual:
        fecha = st.date_input("Fecha", datetime.now(colombia).date())
        hora_texto = st.text_input("Hora (HH:MM)", value=datetime.now(colombia).strftime("%H:%M"))
        try:
            hora = datetime.strptime(hora_texto, "%H:%M").time()
            fecha_hora_evento = colombia.localize(datetime.combine(fecha, hora))
        except ValueError:
            st.error("Formato de hora inválido. Usa HH:MM.")
            fecha_hora_evento = None
    else:
        fecha_hora_evento = datetime.now(colombia)

    if st.button("✅ Registrar"):
        if fecha_hora_evento:
            if check_a:
                registrar_evento(evento_a, fecha_hora_evento)
                st.success("✅ Evento A registrado")
            if check_b:
                registrar_evento(evento_b, fecha_hora_evento)
                st.success("✅ Evento B registrado")
            if not check_a and not check_b:
                st.warning("Debes seleccionar al menos un evento.")