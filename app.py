import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import re
from streamlit_extras.st_autorefresh import st_autorefresh

# === CONFIG ===
st.set_page_config(page_title="BucleVigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")
st_autorefresh(interval=1000, key="refresh")  # Refresca cada segundo

# === DB CONNECTION ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === EVENTOS ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === LOAD ÚLTIMOS EVENTOS ===
def obtener_ultimo_evento(nombre_evento):
    return coleccion_eventos.find_one({"evento": nombre_evento}, sort=[("fecha_hora", -1)])

st.session_state[evento_a] = obtener_ultimo_evento(evento_a)
st.session_state[evento_b] = obtener_ultimo_evento(evento_b)

# === FUNCIONES ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[nombre_evento] = {"fecha_hora": fecha_hora}

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === UI ===
st.title("🧠 BucleVigilado")

# === REGISTRO DE EVENTO ===
st.header("📍 Registrar evento")
tipo_evento = st.selectbox("Selecciona tipo de evento:", ["Masturbación", "Pago por sexo"])
usar_manual = st.checkbox("Ingresar fecha y hora manualmente")

if usar_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora_texto = st.text_input("Hora (HH:MM)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora_evento = colombia.localize(datetime.combine(fecha, hora))
    except ValueError:
        st.error("Formato de hora inválido.")
        fecha_hora_evento = None
else:
    fecha_hora_evento = datetime.now(colombia)

if st.button("✅ Registrar evento"):
    if fecha_hora_evento:
        if tipo_evento == "Masturbación":
            registrar_evento(evento_a, fecha_hora_evento)
            st.success("✊🏽 Evento registrado")
        elif tipo_evento == "Pago por sexo":
            registrar_evento(evento_b, fecha_hora_evento)
            st.success("💸 Evento registrado")

# === REGISTRO DE REFLEXIÓN ===
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

# === STREAKS CON FORMATO ===
st.subheader("⏱️ Racha actual")
col1, col2 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    evento = st.session_state.get(nombre_evento)
    if evento:
        ahora = datetime.now(colombia)
        inicio = evento["fecha_hora"].astimezone(colombia)
        delta = ahora - inicio
        minutos = int(delta.total_seconds() // 60)
        rdelta = relativedelta(ahora, inicio)
        detalle = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"
        st.metric(emoji, f"{minutos:,}".replace(",", "."))  # puntos como miles
        st.caption(detalle)
    else:
        st.metric(emoji, "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")

with col1:
    mostrar_racha(evento_a, "✊🏽")
with col2:
    mostrar_racha(evento_b, "💸")

# === HISTORIAL ===
st.subheader("📑 Historial")
tab1, tab2, tab3 = st.tabs(["✊🏽 Eventos A", "💸 Eventos B", "🧠 Reflexiones"])

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{"N°": total - i, "Fecha": f.date(), "Hora": f.strftime("%H:%M")} for i, f in enumerate(fechas)])

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        emociones = " ".join(f'{e["emoji"]} {e["nombre"]}' for e in d.get("emociones", []))
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
    for _, row in df_r.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
            st.write(row["Reflexión"])