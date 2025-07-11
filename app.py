import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
import pandas as pd
import re
from streamlit_autorefresh import st_autorefresh

# === CONFIG ===
st.set_page_config(page_title="BucleVigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")
st_autorefresh(interval=5000, key="refresh_cronometro")

# === DB ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
iconos = {
    evento_a: "✊🏽",
    evento_b: "💸"
}

# === FUNCIONES ===
def cerrar_evento_anterior(evento):
    ultimo = coleccion_eventos.find_one({"evento": evento, "fin": {"$exists": False}}, sort=[("inicio", -1)])
    if ultimo:
        coleccion_eventos.update_one(
            {"_id": ultimo["_id"]},
            {"$set": {"fin": datetime.now(colombia)}}
        )

def iniciar_evento(evento):
    cerrar_evento_anterior(evento)
    nuevo = {
        "evento": evento,
        "inicio": datetime.now(colombia)
    }
    coleccion_eventos.insert_one(nuevo)

def evento_activo(evento):
    return coleccion_eventos.find_one({"evento": evento, "fin": {"$exists": False}}, sort=[("inicio", -1)])

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

def formatear_duracion(td):
    rdelta = relativedelta(datetime.now(colombia), td)
    return f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"

# === UI PRINCIPAL ===
st.title("📍 Registrar evento con cronómetro")

st.checkbox(f"{iconos[evento_a]} {evento_a}", key="check_a")
st.checkbox(f"{iconos[evento_b]} {evento_b}", key="check_b")

if st.button("🚀 Iniciar evento"):
    if st.session_state.check_a:
        iniciar_evento(evento_a)
        st.success("Evento A registrado")
    if st.session_state.check_b:
        iniciar_evento(evento_b)
        st.success("Evento B registrado")
    if not st.session_state.check_a and not st.session_state.check_b:
        st.warning("No seleccionaste ningún evento")

# === ESTADO ACTUAL DE EVENTO ===
st.header("🕒 Estado actual de eventos")
for evento in [evento_a, evento_b]:
    activo = evento_activo(evento)
    if activo:
        inicio = activo["inicio"].astimezone(colombia)
        duracion = datetime.now(colombia) - inicio
        st.success(f"{iconos[evento]} Evento activo desde el {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"⏱️ Duración: {formatear_duracion(inicio)}")
        st.button(f"⛔ Detener {iconos[evento]}", key=f"stop_{evento}", on_click=cerrar_evento_anterior, args=(evento,))

# === REFLEXIONES ===
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

# === HISTORIAL ===
st.header("📑 Historial de eventos")
tab_a, tab_b = st.tabs([f"{iconos[evento_a]} Historial A", f"{iconos[evento_b]} Historial B"])

def obtener_historial(evento):
    docs = list(coleccion_eventos.find({"evento": evento}).sort("inicio", -1))
    rows = []
    for d in docs:
        inicio = d["inicio"].astimezone(colombia)
        fin = d.get("fin")
        fin_fmt = fin.astimezone(colombia).strftime("%H:%M:%S") if fin else "⏳ Activo"
        duracion = formatear_duracion(inicio) if not fin else str(relativedelta(fin, inicio)).replace("relativedelta(", "").replace(")", "").replace(", ", " ")
        rows.append({
            "Fecha": inicio.strftime("%Y-%m-%d"),
            "Inicio": inicio.strftime("%H:%M:%S"),
            "Fin": fin_fmt,
            "Duración": duracion
        })
    return pd.DataFrame(rows)

with tab_a:
    st.dataframe(obtener_historial(evento_a), use_container_width=True, hide_index=True)
with tab_b:
    st.dataframe(obtener_historial(evento_b), use_container_width=True, hide_index=True)

# === REFLEXIONES PREVIAS ===
st.header("📖 Reflexiones previas")
docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
for doc in docs:
    fecha = doc["fecha_hora"].astimezone(colombia).strftime("%Y-%m-%d %H:%M")
    emociones = " ".join(e["emoji"] for e in doc.get("emociones", []))
    texto = doc.get("reflexion", "")
    with st.expander(f"{fecha} — {emociones}"):
        st.write(texto)