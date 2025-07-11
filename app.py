import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import re

# === CONFIG ===
st.set_page_config(page_title="BucleVigiladoApp", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === DATABASE CONNECTION ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === EVENT DEFINITIONS ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === FUNCTIONS ===

def registrar_evento(nombre_evento, fecha_hora):
    # Cierra evento anterior si está en curso
    ultimo = coleccion_eventos.find_one(
        {"evento": nombre_evento},
        sort=[("fecha_hora", -1)]
    )
    if ultimo and "inicio" in ultimo and "fin" not in ultimo:
        coleccion_eventos.update_one(
            {"_id": ultimo["_id"]},
            {"$set": {"fin": fecha_hora}}
        )
    
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "inicio": fecha_hora
    })

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

def obtener_ultimo_evento(nombre_evento):
    doc = coleccion_eventos.find_one(
        {"evento": nombre_evento},
        sort=[("fecha_hora", -1)]
    )
    if not doc:
        return None
    fecha_raw = doc.get("inicio") or doc.get("fecha_hora")
    if not fecha_raw:
        return None
    return fecha_raw.astimezone(colombia)

# === UI ===
st.title("BucleVigilado")

# === SECTION 1: REGISTRAR EVENTO ===
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

if st.button("✅ Registrar evento"):
    if fecha_hora_evento:
        if check_a:
            registrar_evento(evento_a, fecha_hora_evento)
            st.success("✊🏽 Evento registrado")
        if check_b:
            registrar_evento(evento_b, fecha_hora_evento)
            st.success("💸 Evento registrado")
        if not check_a and not check_b:
            st.warning("No seleccionaste ningún evento.")

# === SECTION 2: REGISTRAR REFLEXIÓN ===
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

# === STREAKS ===
st.subheader("⏱️ Racha actual")
st_autorefresh(interval=5000, key="auto")  # Refresca cada 5 segundos

col3, col4 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    inicio = obtener_ultimo_evento(nombre_evento)
    if inicio:
        ahora = datetime.now(colombia)
        delta = ahora - inicio
        rdelta = relativedelta(ahora, inicio)
        minutos = int(delta.total_seconds() // 60)
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

# === HISTORIAL TABS ===
st.subheader("📑 Historial")
tab1, tab2, tab3 = st.tabs(["✊🏽 Eventos A", "💸 Eventos B", "🧠 Reflexiones"])

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    rows = []
    for e in eventos:
        fecha_raw = e.get("inicio") or e.get("fecha_hora")
        if not fecha_raw:
            continue
        fecha = fecha_raw.astimezone(colombia)
        rows.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M:%S")
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

with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)

with tab3:
    df_r = obtener_reflexiones()
    for i, row in df_r.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
            st.write(row["Reflexión"])