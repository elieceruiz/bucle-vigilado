import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import re

# === CONFIG ===
st.set_page_config(page_title="BucleVigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === DATABASE CONNECTION ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === REGISTRAR NUEVO EVENTO ===
st.title("BucleVigilado")
st.header("📍 Registrar evento")

col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽 La Iniciativa Aquella")
with col2:
    check_b = st.checkbox("💸 La Iniciativa de Pago")

if st.button("🚀 Iniciar evento"):
    ahora = datetime.now(colombia)

    if check_a:
        anterior = coleccion_eventos.find_one({"evento": evento_a, "fin": {"$exists": False}}, sort=[("fecha_hora", -1)])
        if anterior:
            coleccion_eventos.update_one({"_id": anterior["_id"]}, {"$set": {"fin": ahora}})
        coleccion_eventos.insert_one({"evento": evento_a, "fecha_hora": ahora})
        st.success("✊🏽 Evento A registrado")

    if check_b:
        anterior = coleccion_eventos.find_one({"evento": evento_b, "fin": {"$exists": False}}, sort=[("fecha_hora", -1)])
        if anterior:
            coleccion_eventos.update_one({"_id": anterior["_id"]}, {"$set": {"fin": ahora}})
        coleccion_eventos.insert_one({"evento": evento_b, "fecha_hora": ahora})
        st.success("💸 Evento B registrado")

    if not check_a and not check_b:
        st.warning("Seleccioná al menos un evento para iniciar.")

# === ESTADO ACTUAL DE LOS EVENTOS ===
st.subheader("⏱️ Estado actual")

def mostrar_estado(nombre_evento, emoji):
    evento = coleccion_eventos.find_one({"evento": nombre_evento}, sort=[("fecha_hora", -1)])

    if evento and "fecha_hora" in evento:
        inicio = evento["fecha_hora"].astimezone(colombia)
        ahora = datetime.now(colombia)

        if "fin" not in evento:
            segundos = int((ahora - inicio).total_seconds())
            duracion = str(timedelta(seconds=segundos))
            st.success(f"{emoji} Evento activo desde {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
            st.metric("⏱️ Duración", duracion)
        else:
            delta = ahora - inicio
            minutos = int(delta.total_seconds() // 60)
            detalle = str(timedelta(seconds=int(delta.total_seconds())))
            st.metric(f"{emoji} Racha sin evento", f"{minutos} min")
            st.caption(f"Último hace: {detalle}")
    else:
        st.metric(f"{emoji} Racha sin evento", "0 min")
        st.caption("Sin eventos registrados")

col3, col4 = st.columns(2)
with col3:
    mostrar_estado(evento_a, "✊🏽")
with col4:
    mostrar_estado(evento_b, "💸")

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
        coleccion_reflexiones.insert_one({
            "fecha_hora": fecha_hora_reflexion,
            "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
            "reflexion": reflexion.strip()
        })
        st.success("🧠 Reflexión guardada")
    else:
        st.warning("Escribí algo o seleccioná al menos una emoción.")

# === HISTORIAL DE EVENTOS ===
st.subheader("📑 Historial de eventos")

def historial_eventos(nombre_evento):
    docs = list(coleccion_eventos.find({"evento": nombre_evento, "fin": {"$exists": True}}).sort("fecha_hora", -1))
    data = []
    for d in docs:
        inicio = d.get("fecha_hora")
        fin = d.get("fin")
        if inicio and fin:
            duracion = str(fin - inicio)
            data.append({
                "Fecha": inicio.astimezone(colombia).strftime("%Y-%m-%d"),
                "Inicio": inicio.astimezone(colombia).strftime("%H:%M:%S"),
                "Fin": fin.astimezone(colombia).strftime("%H:%M:%S"),
                "Duración": duracion
            })
    return data

tab1, tab2 = st.tabs(["✊🏽 Historial A", "💸 Historial B"])
with tab1:
    st.dataframe(historial_eventos(evento_a), use_container_width=True)
with tab2:
    st.dataframe(historial_eventos(evento_b), use_container_width=True)

# === HISTORIAL DE REFLEXIONES ===
st.subheader("📖 Reflexiones previas")
reflexiones = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))

if reflexiones:
    for r in reflexiones:
        fecha = r["fecha_hora"].astimezone(colombia)
        texto = r.get("reflexion", "")
        emociones = " ".join(e["emoji"] for e in r.get("emociones", []))
        with st.expander(f"{fecha.strftime('%Y-%m-%d %H:%M')} — {emociones}"):
            st.write(texto)
else:
    st.info("Aún no hay reflexiones registradas.")