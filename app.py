import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
import re

# === CONFIG ===
st.set_page_config(page_title="BucleVigiladoApp", layout="centered")
st_autorefresh(interval=1000, key="refresh")
colombia = pytz.timezone("America/Bogota")

# === DATABASE CONNECTION ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === EVENT DEFINITIONS ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === INITIAL STATE ===
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# === SAVE EVENT FUNCTION ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[nombre_evento] = fecha_hora

# === SAVE REFLECTION FUNCTION ===
def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === UI: MAIN TITLE ===
st.title("BucleVigilado")

# === UI: EVENT REGISTRATION ===
st.subheader("Registrar evento")
col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽", value=False)
with col2:
    check_b = st.checkbox("💸", value=False)

usar_fecha_hora_manual = st.checkbox("Ingresar fecha y hora manualmente")
if usar_fecha_hora_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora_texto = st.text_input("Hora (HH:MM, formato 24h)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora = colombia.localize(datetime.combine(fecha, hora))
    except ValueError:
        st.error("Formato de hora no válido. Usa HH:MM en formato 24h.")
        fecha_hora = None
else:
    fecha_hora = datetime.now(colombia)

# === EMOTION OPTIONS ===
emociones_opciones = [
    "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
    "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
]

# === REFLECTION UI ===
emociones_sueltas = st.multiselect("¿Cómo te sentías en ese momento?", emociones_opciones)
reflexion_suelta = st.text_area("¿Querés decir algo más sobre lo que sentiste o pensaste?", height=150)
palabras = len(re.findall(r'\b\w+\b', reflexion_suelta))
st.caption(f"📄 Palabras: {palabras}")

# === SAVE BUTTON ===
if st.button("Registrar"):
    if fecha_hora:
        if check_a:
            registrar_evento(evento_a, fecha_hora)
            st.success("✊🏽 Evento registrado")
        if check_b:
            registrar_evento(evento_b, fecha_hora)
            st.success("💸 Evento registrado")
        if emociones_sueltas or reflexion_suelta.strip():
            guardar_reflexion(fecha_hora, emociones_sueltas, reflexion_suelta)
            st.success("🧠 Reflexión guardada")
        if not check_a and not check_b and not emociones_sueltas and not reflexion_suelta.strip():
            st.warning("No se seleccionó ningún evento ni se escribió una reflexión.")

# === STREAK METRICS ===
st.subheader("⏱️ Racha actual")
col3, col4 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ahora = datetime.now(colombia)
        ultimo = st.session_state[nombre_evento]
        delta = ahora - ultimo
        minutos = int(delta.total_seconds() // 60)
        rdelta = relativedelta(ahora, ultimo)
        detalle = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        st.metric(emoji, f"{minutos} min")
        st.caption(detalle)
    else:
        st.metric(emoji, "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")

with col3:
    mostrar_racha(evento_a, "✊🏽")
with col4:
    mostrar_racha(evento_b, "💸")

# === TABS ===
st.subheader("📑 Historial de registros")
tab1, tab2, tab3 = st.tabs(["✊🏽", "💸", "🧠 Reflexiones y Descargas"])

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{"N°": total - i, "Fecha": f.date(), "Hora": f.strftime("%H:%M")} for i, f in enumerate(fechas)])

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
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("🧠 Reflexiones completas y análisis")
    df_r = obtener_reflexiones()
    for i, row in df_r.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
            st.write(row["Reflexión"])p