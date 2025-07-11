import streamlit as st
from datetime import datetime
from pymongo import MongoClient
from dateutil.relativedelta import relativedelta
import pytz
import pandas as pd
import re

# === CONFIG ===
st.set_page_config("Bucle Vigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN A MONGO ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === ETIQUETAS ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
iconos = {evento_a: "✊🏽", evento_b: "💸"}

# === FUNCIÓN PARA REGISTRAR NUEVO EVENTO Y CERRAR EL ANTERIOR ===
def iniciar_evento(nombre_evento):
    ahora = datetime.now(colombia)

    # Cerrar evento activo actual (si hay)
    ultimo = coleccion_eventos.find_one(
        {"fin": {"$exists": False}}, sort=[("fecha_hora", -1)]
    )
    if ultimo:
        coleccion_eventos.update_one(
            {"_id": ultimo["_id"]}, {"$set": {"fin": ahora}}
        )

    # Insertar nuevo evento
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": ahora
    })

    st.success(f"{iconos[nombre_evento]} Nuevo evento iniciado.")

# === FUNCIÓN PARA MOSTRAR EVENTO ACTIVO CON CRONÓMETRO ===
def mostrar_estado(nombre_evento):
    evento = coleccion_eventos.find_one(
        {"evento": nombre_evento, "fin": {"$exists": False}},
        sort=[("fecha_hora", -1)]
    )
    if evento:
        inicio = evento["fecha_hora"].astimezone(colombia)
        ahora = datetime.now(colombia)
        rdelta = relativedelta(ahora, inicio)
        duracion = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d, {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        st.success(f"{iconos[nombre_evento]} Evento activo desde el {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        st.metric("⏱️ Duración", duracion)

# === FUNCIÓN PARA GUARDAR REFLEXIÓN ===
def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === FUNCIÓN PARA MOSTRAR HISTORIAL ===
def historial_eventos(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    data = []
    for e in eventos:
        inicio = e["fecha_hora"].astimezone(colombia)
        fin = e.get("fin", datetime.now(pytz.utc)).astimezone(colombia)
        rdelta = relativedelta(fin, inicio)
        duracion = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m"
        data.append({
            "Fecha": inicio.strftime("%Y-%m-%d"),
            "Inicio": inicio.strftime("%H:%M:%S"),
            "Fin": fin.strftime("%H:%M:%S") if "fin" in e else "⏳ Activo",
            "Duración": duracion
        })
    return pd.DataFrame(data)

# === FUNCIÓN PARA MOSTRAR REFLEXIONES ===
def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
        emociones = " ".join(e["emoji"] for e in d.get("emociones", []))
        texto = d.get("reflexion", "")
        rows.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Emociones": emociones,
            "Reflexión": texto
        })
    return rows

# === INTERFAZ ===
st.title("📍 Registrar evento con cronómetro")

# === INICIAR EVENTO ===
st.subheader("🚀 Iniciar evento")
col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox(f"{iconos[evento_a]} {evento_a}")
with col2:
    check_b = st.checkbox(f"{iconos[evento_b]} {evento_b}")

if st.button("🚀 Iniciar evento"):
    if check_a:
        iniciar_evento(evento_a)
    elif check_b:
        iniciar_evento(evento_b)
    else:
        st.warning("Seleccioná un evento para iniciar.")

# === ESTADO ACTUAL ===
st.subheader("⏱️ Estado actual de eventos")
mostrar_estado(evento_a)
mostrar_estado(evento_b)

# === REGISTRAR REFLEXIÓN ===
st.subheader("🧠 Registrar reflexión")
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

# === HISTORIAL ===
st.subheader("📑 Historial de eventos")
tab1, tab2 = st.tabs([f"{iconos[evento_a]} Historial A", f"{iconos[evento_b]} Historial B"])
with tab1:
    df_a = historial_eventos(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)
with tab2:
    df_b = historial_eventos(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)

# === REFLEXIONES ===
st.subheader("📖 Reflexiones previas")
reflexiones = obtener_reflexiones()
for r in reflexiones:
    with st.expander(f"{r['Fecha']} {r['Hora']} — {r['Emociones']}"):
        st.write(r["Reflexión"])