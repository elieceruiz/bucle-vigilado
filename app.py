import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import re
import time

# === CONFIGURACIÓN GENERAL ===
st.set_page_config("BucleVigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === DEFINICIONES ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === ESTADO INICIAL (último evento de cada tipo) ===
for evento in [evento_a, evento_b]:
    if evento not in st.session_state:
        doc = coleccion_eventos.find_one({"evento": evento}, sort=[("fecha_hora", -1)])
        if doc:
            st.session_state[evento] = doc["fecha_hora"].astimezone(colombia)

# === FUNCIONES ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({"evento": nombre_evento, "fecha_hora": fecha_hora})
    st.session_state[nombre_evento] = fecha_hora

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === UI PRINCIPAL ===
st.title("⏳ BucleVigilado")

# === REGISTRO DE EVENTO ===
st.header("📍 Registrar evento")
tipo = st.selectbox("Selecciona tipo de evento:", ["✊🏽 Masturbación", "💸 Pago por sexo", "🧠 Reflexión"])

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
    if tipo == "🧠 Reflexión":
        st.warning("Usá el apartado de más abajo para registrar reflexiones.")
    elif fecha_hora_evento:
        if tipo.startswith("✊"):
            registrar_evento(evento_a, fecha_hora_evento)
            st.success("✊🏽 Evento registrado")
        elif tipo.startswith("💸"):
            registrar_evento(evento_b, fecha_hora_evento)
            st.success("💸 Evento registrado")

# === REGISTRAR REFLEXIÓN ===
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
        st.success("🧠 Reflexión guardada")
    else:
        st.warning("Escribí algo o seleccioná al menos una emoción.")

# === CRONÓMETROS AL SEGUNDO ===
st.subheader("⏱️ Racha actual")
col1, col2 = st.columns(2)

def mostrar_cronometro(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ahora = datetime.now(colombia)
        inicio = st.session_state[nombre_evento]
        delta = ahora - inicio
        rdelta = relativedelta(ahora, inicio)
        duracion = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        minutos = int(delta.total_seconds() // 60)
        st.metric(emoji, f"{minutos} min")
        st.caption(duracion)
    else:
        st.metric(emoji, "—")
        st.caption("Sin registro")

with col1:
    mostrar_cronometro(evento_a, "✊🏽")
with col2:
    mostrar_cronometro(evento_b, "💸")

# === HISTORIAL DE REGISTROS ===
st.subheader("📑 Historial")
tab1, tab2, tab3 = st.tabs(["✊🏽 Eventos A", "💸 Eventos B", "🧠 Reflexiones"])

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    for i, ev in enumerate(eventos):
        fecha = ev["fecha_hora"].astimezone(colombia)
        filas.append({
            "N°": len(eventos) - i,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M")
        })
    return pd.DataFrame(filas)

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    filas = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
        emociones = " ".join(e["emoji"] for e in d.get("emociones", []))
        filas.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Emociones": emociones,
            "Reflexión": d.get("reflexion", "")
        })
    return pd.DataFrame(filas)

with tab1:
    st.dataframe(obtener_registros(evento_a), use_container_width=True, hide_index=True)

with tab2:
    st.dataframe(obtener_registros(evento_b), use_container_width=True, hide_index=True)

with tab3:
    reflexiones = obtener_reflexiones()
    for _, row in reflexiones.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
            st.write(row["Reflexión"])