import streamlit as st
import time
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
import re

# === CONFIG ===
st.set_page_config(page_title="BucleVigiladoApp", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === DB CONNECTION ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === FUNCIONES ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

def obtener_ultimo_evento(nombre_evento):
    doc = coleccion_eventos.find_one({"evento": nombre_evento}, sort=[("fecha_hora", -1)])
    return doc["fecha_hora"].astimezone(colombia) if doc else None

def formatear_duracion(td):
    total_seg = int(td.total_seconds())
    dias, resto = divmod(total_seg, 86400)
    horas, resto = divmod(resto, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{dias}d {horas}h {minutos}m {segundos}s"

def formatear_minutos(m):
    return f"{int(m):,}".replace(",", ".")

# === UI ===
st.title("🧠 BucleVigilado")

# === REGISTRO EVENTO ===
st.header("📍 Registrar evento")
col1, col2 = st.columns(2)
with col1:
    tipo_evento = st.selectbox("Tipo de evento", [evento_a, evento_b])
with col2:
    usar_manual = st.checkbox("⏱️ Ingresar hora manual")

if usar_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora_texto = st.text_input("Hora (HH:MM)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora = colombia.localize(datetime.combine(fecha, hora))
    except:
        st.error("⚠️ Formato inválido.")
        fecha_hora = None
else:
    fecha_hora = datetime.now(colombia)

if st.button("✅ Registrar evento") and fecha_hora:
    registrar_evento(tipo_evento, fecha_hora)
    st.success(f"📌 Evento registrado: {tipo_evento}")

# === REGISTRO REFLEXIÓN ===
st.header("🧠 Registrar reflexión")
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
        guardar_reflexion(datetime.now(colombia), emociones, reflexion)
        st.success("🧠 Reflexión guardada")
    else:
        st.warning("Seleccioná al menos una emoción o escribí algo.")

# === RACHAS EN TIEMPO REAL ===
st.header("⏱️ Racha actual")

racha_container = st.empty()

def mostrar_racha(nombre_evento, emoji):
    inicio = obtener_ultimo_evento(nombre_evento)
    if inicio:
        ahora = datetime.now(colombia)
        delta = ahora - inicio
        minutos = int(delta.total_seconds() // 60)
        return f"{emoji} {formatear_minutos(minutos)} min", formatear_duracion(delta), inicio.strftime("%Y-%m-%d %H:%M")
    return f"{emoji} 0 min", "0d 0h 0m 0s", "—"

while True:
    with racha_container.container():
        col1, col2 = st.columns(2)
        for col, (evento, emoji) in zip([col1, col2], [(evento_a, "✊🏽"), (evento_b, "💸")]):
            racha, detalle, fecha = mostrar_racha(evento, emoji)
            col.metric(label=f"{evento}", value=racha, delta=detalle)
            col.caption(f"Último: {fecha}")
        st.caption("Se actualiza cada segundo.")
    time.sleep(1)