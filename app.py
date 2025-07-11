import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import re
import time

# === CONFIGURACIÓN ===
st.set_page_config("BucleVigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A BASE DE DATOS ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === VARIABLES CLAVE ===
nombres_eventos = {
    "masturbacion": "Masturbación",
    "pago": "Pago por sexo"
}

# === ESTADO INICIAL ===
for clave in nombres_eventos:
    if clave not in st.session_state:
        ultimo = coleccion_eventos.find_one({"evento": clave}, sort=[("fecha_hora", -1)])
        if ultimo:
            st.session_state[clave] = ultimo["fecha_hora"].astimezone(colombia)

# === FUNCIONES ===
def registrar_evento(clave_evento, fecha_hora):
    coleccion_eventos.insert_one({
        "evento": clave_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[clave_evento] = fecha_hora

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === UI PRINCIPAL ===
st.title("🔁 BucleVigilado")

# === SECCIÓN: REGISTRO DE EVENTO O REFLEXIÓN ===
st.header("📍 Registrar")

opcion = st.selectbox("¿Qué vas a registrar?", ["Masturbación", "Pago por sexo", "Reflexión"])

if opcion in ["Masturbación", "Pago por sexo"]:
    clave = "masturbacion" if opcion == "Masturbación" else "pago"
    fecha_manual = st.checkbox("Usar fecha/hora manual")
    if fecha_manual:
        fecha = st.date_input("Fecha", datetime.now(colombia).date())
        hora_str = st.text_input("Hora (HH:MM)", value=datetime.now().strftime("%H:%M"))
        try:
            hora = datetime.strptime(hora_str, "%H:%M").time()
            fecha_hora = colombia.localize(datetime.combine(fecha, hora))
        except:
            st.error("Hora inválida. Usa formato HH:MM.")
            fecha_hora = None
    else:
        fecha_hora = datetime.now(colombia)

    if st.button("✅ Registrar evento"):
        if fecha_hora:
            registrar_evento(clave, fecha_hora)
            st.success(f"🕒 {opcion} registrada.")
        else:
            st.warning("Fecha y hora inválidas.")

# === SECCIÓN: REGISTRO DE REFLEXIÓN ===
if opcion == "Reflexión":
    st.subheader("🧠 Reflexión")
    emociones_opciones = [
        "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
        "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
    ]
    emociones = st.multiselect("¿Cómo te sentías?", emociones_opciones)
    texto = st.text_area("¿Querés dejar algo escrito?", height=150)
    palabras = len(re.findall(r'\b\w+\b', texto))
    st.caption(f"📄 Palabras: {palabras}")
    if st.button("📝 Guardar reflexión"):
        if texto.strip() or emociones:
            guardar_reflexion(datetime.now(colombia), emociones, texto)
            st.success("💬 Reflexión guardada.")
        else:
            st.warning("Agrega emociones o escribe algo.")

# === SECCIÓN: CRONÓMETROS ===
st.subheader("⏱️ Racha actual")
cron_col1, cron_col2 = st.columns(2)

def mostrar_cronometro(clave, emoji, contenedor):
    if clave in st.session_state:
        inicio = st.session_state[clave]
        delta = datetime.now(colombia) - inicio
        rdelta = relativedelta(datetime.now(colombia), inicio)
        segundos = int(delta.total_seconds())
        detalle = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        contenedor.metric(label=emoji, value=f"{segundos // 60} min")
        contenedor.caption(detalle)
    else:
        contenedor.metric(label=emoji, value="0 min")
        contenedor.caption("0a 0m 0d 0h 0m 0s")

with cron_col1:
    mostrar_cronometro("masturbacion", "✊🏽", st)
with cron_col2:
    mostrar_cronometro("pago", "💸", st)

# === SECCIÓN: HISTORIAL ===
st.subheader("📑 Historial")
tabs = st.tabs(["✊🏽 Masturbación", "💸 Pago por sexo", "🧠 Reflexiones"])

def obtener_eventos(clave_evento):
    docs = list(coleccion_eventos.find({"evento": clave_evento}).sort("fecha_hora", -1))
    data = []
    for i, doc in enumerate(docs):
        fecha = doc["fecha_hora"].astimezone(colombia)
        data.append({
            "N°": len(docs) - i,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M")
        })
    return pd.DataFrame(data)

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    filas = []
    for d in docs:
        try:
            fecha = d["fecha_hora"].astimezone(colombia)
            emociones = " ".join(e["emoji"] for e in d.get("emociones", []))
            filas.append({
                "Fecha": fecha.strftime("%Y-%m-%d"),
                "Hora": fecha.strftime("%H:%M"),
                "Emociones": emociones,
                "Reflexión": d.get("reflexion", "")
            })
        except Exception as e:
            st.error(f"Error: {e}")
    return pd.DataFrame(filas)

with tabs[0]:
    st.dataframe(obtener_eventos("masturbacion"), use_container_width=True, hide_index=True)

with tabs[1]:
    st.dataframe(obtener_eventos("pago"), use_container_width=True, hide_index=True)

with tabs[2]:
    df_r = obtener_reflexiones()
    for _, row in df_r.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
            st.write(row["Reflexión"])