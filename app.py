import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import re

# === CONFIGURACIÓN ===
st.set_page_config(page_title="🧭 Bucle Vigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === CONEXIÓN MONGO ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === OPCIONES DE EVENTO ===
eventos_disponibles = {
    "✊🏽 La Iniciativa Aquella": "La Iniciativa Aquella",
    "💸 La Iniciativa de Pago": "La Iniciativa de Pago"
}
iconos = {v: k.split()[0] for k, v in eventos_disponibles.items()}

# === UTILIDADES ===
def cerrar_evento_anterior(evento):
    coleccion_eventos.update_many(
        {"evento": evento, "fin": {"$exists": False}},
        {"$set": {"fin": datetime.now(colombia)}}
    )

def registrar_evento(nombre_evento, fecha_hora):
    cerrar_evento_anterior(nombre_evento)
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "inicio": fecha_hora
    })

def formatear_duracion(inicio):
    ahora = datetime.now(colombia)
    delta = relativedelta(ahora, inicio)
    return f"{delta.years}a {delta.months}m {delta.days}d {delta.hours}h {delta.minutes}m {delta.seconds}s"

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

def obtener_evento_activo(evento):
    return coleccion_eventos.find_one(
        {"evento": evento, "fin": {"$exists": False}},
        sort=[("inicio", -1)]
    )

def obtener_historial(evento):
    docs = coleccion_eventos.find({"evento": evento}).sort("inicio", -1)
    rows = []
    for d in docs:
        inicio = d["inicio"].astimezone(colombia)
        fin = d.get("fin")
        if fin:
            fin = fin.astimezone(colombia)
            duracion = relativedelta(fin, inicio)
            texto_duracion = f"{duracion.years}a {duracion.months}m {duracion.days}d {duracion.hours}h {duracion.minutes}m"
            estado = fin.strftime("%H:%M:%S")
        else:
            texto_duracion = formatear_duracion(inicio)
            estado = "⏳ Activo"
        rows.append({
            "Fecha": inicio.strftime("%Y-%m-%d"),
            "Inicio": inicio.strftime("%H:%M:%S"),
            "Fin": estado,
            "Duración": texto_duracion
        })
    return pd.DataFrame(rows)

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

# === INTERFAZ PRINCIPAL ===
st.title("📍 Registrar evento con cronómetro")

# === SELECCIÓN E INICIO ===
evento_seleccionado = st.selectbox("Seleccioná el evento a iniciar", list(eventos_disponibles.values()))
if st.button("🚀 Iniciar evento"):
    registrar_evento(evento_seleccionado, datetime.now(colombia))
    st.rerun()

# === ESTADO ACTUAL ===
st.subheader("🕰️ Estado actual de eventos")
for evento in eventos_disponibles.values():
    activo = obtener_evento_activo(evento)
    if activo and "inicio" in activo:
        inicio = activo["inicio"].astimezone(colombia)
        st.success(f"{iconos[evento]} Evento activo desde el {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"⏱️ Duración: {formatear_duracion(inicio)}")
    else:
        st.info(f"{iconos[evento]} No hay evento activo registrado.")

# === SECCIÓN DE REFLEXIONES ===
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
tab1, tab2 = st.tabs(["✊🏽 Historial A", "💸 Historial B"])
with tab1:
    st.dataframe(obtener_historial("La Iniciativa Aquella"), use_container_width=True, hide_index=True)
with tab2:
    st.dataframe(obtener_historial("La Iniciativa de Pago"), use_container_width=True, hide_index=True)

# === HISTORIAL DE REFLEXIONES ===
st.subheader("📖 Reflexiones previas")
df_r = obtener_reflexiones()
for i, row in df_r.iterrows():
    with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
        st.write(row["Reflexión"])