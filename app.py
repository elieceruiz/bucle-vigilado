import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import re
import time

# === CONFIG ===
st.set_page_config(page_title="BucleVigiladoApp", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === DB CONNECTION ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === NOMBRES DE EVENTOS ===
opciones_evento = {
    "✊🏽 La Iniciativa Aquella": "La Iniciativa Aquella",
    "💸 La Iniciativa de Pago": "La Iniciativa de Pago",
    "🧠 Reflexión": "Reflexión"
}

# === EVENTOS EN CURSO EN SESSION_STATE ===
for key in opciones_evento.values():
    if key not in st.session_state:
        ultimo = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if ultimo:
            st.session_state[key] = ultimo["fecha_hora"].astimezone(colombia)

# === FUNCIONES ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[nombre_evento] = fecha_hora

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === UI PRINCIPAL ===
st.title("🌀 BucleVigilado")

# === REGISTRO EVENTO ===
st.header("📍 Registrar evento")
tipo_evento = st.selectbox("Seleccioná el tipo", list(opciones_evento.keys()))
usar_manual = st.checkbox("Ingresar fecha y hora manualmente")

if usar_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora_txt = st.text_input("Hora (HH:MM)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_txt, "%H:%M").time()
        fecha_hora = colombia.localize(datetime.combine(fecha, hora))
    except ValueError:
        st.error("Formato inválido.")
        fecha_hora = None
else:
    fecha_hora = datetime.now(colombia)

if st.button("✅ Registrar evento"):
    if fecha_hora:
        nombre_evento = opciones_evento[tipo_evento]
        registrar_evento(nombre_evento, fecha_hora)
        st.success(f"{tipo_evento} registrado correctamente")

# === REGISTRO REFLEXIÓN ===
st.header("🧠 Registrar reflexión")
fecha_hora_reflexion = datetime.now(colombia)
emociones_opciones = [
    "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
    "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
]
emociones = st.multiselect("¿Cómo te sentías?", emociones_opciones)
reflexion = st.text_area("¿Querés dejar algo escrito?", height=150)
palabras = len(re.findall(r'\b\w+\b', reflexion))
st.caption(f"📄 Palabras: {palabras}")

if st.button("📝 Guardar reflexión"):
    if reflexion.strip() or emociones:
        guardar_reflexion(fecha_hora_reflexion, emociones, reflexion)
        registrar_evento("Reflexión", fecha_hora_reflexion)
        st.success("🧠 Reflexión guardada")
    else:
        st.warning("Escribí algo o seleccioná al menos una emoción.")

# === RACHA ACTUAL ===
st.subheader("⏱️ Racha actual")
col1, col2 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ahora = datetime.now(colombia)
        inicio = st.session_state[nombre_evento]
        delta = ahora - inicio
        minutos = int(delta.total_seconds() // 60)
        rdelta = relativedelta(ahora, inicio)
        detalle = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        st.metric(emoji, f"{minutos} min")
        st.caption(detalle)
    else:
        st.metric(emoji, "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")

with col1:
    mostrar_racha("La Iniciativa Aquella", "✊🏽")
with col2:
    mostrar_racha("La Iniciativa de Pago", "💸")

# === HISTORIAL ===
st.subheader("📑 Historial")
tab1, tab2, tab3 = st.tabs(["✊🏽 Eventos A", "💸 Eventos B", "🧠 Reflexiones"])

def obtener_eventos(nombre_evento):
    docs = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    data = []
    for i, doc in enumerate(docs):
        try:
            fecha = doc["fecha_hora"].astimezone(colombia)
            data.append({
                "N°": len(docs) - i,
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Hora": fecha.strftime("%H:%M")
            })
        except KeyError:
            continue
    return pd.DataFrame(data)

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        emociones = " ".join(e["emoji"] for e in d.get("emociones", []))
        texto = d.get("reflexion", "")
        fecha = d["fecha_hora"].astimezone(colombia)
        rows.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Emociones": emociones,
            "Reflexión": texto
        })
    return pd.DataFrame(rows)

with tab1:
    st.dataframe(obtener_eventos("La Iniciativa Aquella"), use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(obtener_eventos("La Iniciativa de Pago"), use_container_width=True, hide_index=True)
with tab3:
    df = obtener_reflexiones()
    for _, row in df.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
            st.write(row["Reflexión"])