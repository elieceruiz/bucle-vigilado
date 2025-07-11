import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import re
from streamlit.experimental import st_autorefresh

# === CONFIGURACIÓN GENERAL ===
st.set_page_config(page_title="BucleVigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")
st_autorefresh(interval=1000, key="refresh_bucle")  # ⏱️ Refresca cada segundo

# === CONEXIÓN A MONGO ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === EVENTOS DEFINIDOS ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === FUNCIÓN: cerrar evento anterior y registrar nuevo ===
def registrar_evento(nombre_evento, fecha_hora):
    # Cierra el último evento en curso (si lo hubiera)
    ultimo = coleccion_eventos.find_one({"evento": nombre_evento}, sort=[("fecha_hora", -1)])
    if ultimo and not ultimo.get("fin"):
        coleccion_eventos.update_one(
            {"_id": ultimo["_id"]},
            {"$set": {"fin": fecha_hora}}
        )
    # Registra nuevo evento
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[nombre_evento] = fecha_hora

# === FUNCIÓN: guardar reflexión ===
def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

# === UI ===
st.title("BucleVigilado")

# === SECCIÓN: Registrar evento ===
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

# === SECCIÓN: Reflexiones ===
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

# === FUNCIÓN: mostrar cronómetro desde último evento ===
def mostrar_racha(evento_nombre, emoji):
    ultimo = coleccion_eventos.find_one({"evento": evento_nombre}, sort=[("fecha_hora", -1)])
    if not ultimo:
        st.metric(emoji, "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")
        return

    inicio = ultimo.get("fecha_hora")
    if not inicio:
        st.metric(emoji, "0 min")
        return

    inicio = inicio.astimezone(colombia)
    ahora = datetime.now(colombia)
    delta = ahora - inicio
    rdelta = relativedelta(ahora, inicio)

    minutos = int(delta.total_seconds() // 60)
    duracion_texto = f"{rdelta.years}a {rdelta.months}m {rdelta.days}d {rdelta.hours}h {rdelta.minutes}m {rdelta.seconds}s"

    st.metric(emoji, f"{minutos} min")
    st.caption(duracion_texto)

# === CRONÓMETROS EN VIVO ===
st.subheader("⏱️ Racha actual")
col3, col4 = st.columns(2)
with col3:
    mostrar_racha(evento_a, "✊🏽")
with col4:
    mostrar_racha(evento_b, "💸")

# === HISTORIAL ===
st.subheader("📑 Historial")
tab1, tab2, tab3 = st.tabs(["✊🏽 Eventos A", "💸 Eventos B", "🧠 Reflexiones"])

def obtener_historial(evento):
    eventos = list(coleccion_eventos.find({"evento": evento}).sort("fecha_hora", -1))
    data = []
    total = len(eventos)
    for i, e in enumerate(eventos):
        fecha = e.get("fecha_hora")
        if not fecha:
            continue
        fecha = fecha.astimezone(colombia)
        fila = {
            "N°": total - i,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M")
        }
        data.append(fila)
    return pd.DataFrame(data)

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
    return pd.DataFrame(rows)

with tab1:
    df_a = obtener_historial(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    df_b = obtener_historial(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)

with tab3:
    df_r = obtener_reflexiones()
    for i, row in df_r.iterrows():
        with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
            st.write(row["Reflexión"])