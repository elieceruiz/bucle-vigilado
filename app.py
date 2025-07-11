import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import time

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
eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial completo": "historial",
    f"✊🏽 {evento_a}": evento_a,
    f"💸 {evento_b}": evento_b,
}

# === STATE ===
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# === FUNCIONES ===
def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[nombre_evento] = fecha_hora

def guardar_reflexion(fecha_hora, emociones, reflexion):
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip()
    }
    coleccion_reflexiones.insert_one(doc)

def mostrar_racha(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ultimo = st.session_state[nombre_evento]
        cronometro = st.empty()
        st.caption(f"🔴 Última recaída: {ultimo.strftime('%Y-%m-%d %H:%M:%S')}")
        while True:
            ahora = datetime.now(colombia)
            delta = ahora - ultimo
            detalle = relativedelta(ahora, ultimo)
            minutos = int(delta.total_seconds() // 60)
            tiempo = f"{detalle.years}a {detalle.months}m {detalle.days}d {detalle.hours}h {detalle.minutes}m {detalle.seconds}s"
            cronometro.metric("⏱️ Racha", f"{minutos:,} min", tiempo)
            time.sleep(1)
    else:
        st.metric("⏱️ Racha", "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    total = len(eventos)
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos) else None
        diferencia = ""
        if anterior:
            delta = fecha - anterior
            detalle = relativedelta(fecha, anterior)
            diferencia = f"{detalle.years}a {detalle.months}m {detalle.days}d {detalle.hours}h {detalle.minutes}m"
        filas.append({
            "N°": total - i,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Duración sin caer": diferencia
        })
    return pd.DataFrame(filas)

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
        emociones = ", ".join([e["nombre"] for e in d.get("emociones", [])])
        rows.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Emociones": emociones,
            "Reflexión": d.get("reflexion", "")
        })
    return pd.DataFrame(rows)

def contar_palabras():
    texto = st.session_state.reflexion or ""
    palabras = [p for p in texto.strip().split() if p.strip(",.?!¡¿")]
    st.session_state.palabras = len(palabras)

# === UI PRINCIPAL ===
st.title("BucleVigilado")
seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

# === MÓDULO EVENTO ===
if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento: {seleccion}")
    fecha_hora_evento = datetime.now(colombia)

    if st.button("✅ Registrar evento"):
        registrar_evento(opcion, fecha_hora_evento)
        st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")

    mostrar_racha(opcion, seleccion.split()[0])

# === MÓDULO REFLEXIÓN ===
elif opcion == "reflexion":
    st.header("🧠 Registrar reflexión")
    fecha_hora_reflexion = datetime.now(colombia)
    emociones_opciones = [
        "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
        "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
    ]
    emociones = st.multiselect("¿Cómo te sentías?", emociones_opciones)
    texto_reflexion = st.text_area("¿Querés dejar algo escrito?", height=150, key="reflexion")

    if st.button("🔍 Contar palabras", disabled=not texto_reflexion.strip()):
        contar_palabras()

    if "palabras" in st.session_state:
        st.caption(f"📄 Palabras: {st.session_state.palabras}")

    if st.button("📝 Guardar reflexión"):
        if texto_reflexion.strip() or emociones:
            guardar_reflexion(fecha_hora_reflexion, emociones, texto_reflexion)
            st.success("🧠 Reflexión guardada")
        else:
            st.warning("Escribí algo o seleccioná al menos una emoción.")

# === MÓDULO HISTORIAL COMPLETO ===
elif opcion == "historial":
    st.header("📑 Historial completo")
    tabs = st.tabs(["✊🏽 Iniciativa Aquella", "💸 Iniciativa de Pago", "🧠 Reflexiones"])

    with tabs[0]:
        st.subheader(f"📍 Registros de {evento_a}")
        st.dataframe(obtener_registros(evento_a), use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader(f"📍 Registros de {evento_b}")
        st.dataframe(obtener_registros(evento_b), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.subheader("📍 Historial de reflexiones")
        df_r = obtener_reflexiones()
        for i, row in df_r.iterrows():
            with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Emociones']}"):
                st.write(row["Reflexión"])