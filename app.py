import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import time
import re

# === CONFIG ===
st.set_page_config(page_title="BucleVigilado", layout="centered")
colombia = pytz.timezone("America/Bogota")

# === DATABASE CONNECTION ===
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# === EVENT DEFINITIONS ===
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# === UI ===
st.title("BucleVigilado")
st.header("📍 Registrar evento con cronómetro")

col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽 La Iniciativa Aquella")
with col2:
    check_b = st.checkbox("💸 La Iniciativa de Pago")

if st.button("🚀 Iniciar evento"):
    ahora = datetime.now(colombia)

    if check_a:
        anterior_a = coleccion_eventos.find_one({"evento": evento_a, "fin": {"$exists": False}}, sort=[("fecha_hora", -1)])
        if anterior_a:
            coleccion_eventos.update_one({"_id": anterior_a["_id"]}, {"$set": {"fin": ahora}})
        coleccion_eventos.insert_one({"evento": evento_a, "fecha_hora": ahora})
        st.success("✊🏽 Evento A iniciado")

    if check_b:
        anterior_b = coleccion_eventos.find_one({"evento": evento_b, "fin": {"$exists": False}}, sort=[("fecha_hora", -1)])
        if anterior_b:
            coleccion_eventos.update_one({"_id": anterior_b["_id"]}, {"$set": {"fin": ahora}})
        coleccion_eventos.insert_one({"evento": evento_b, "fecha_hora": ahora})
        st.success("💸 Evento B iniciado")

    if not check_a and not check_b:
        st.warning("Seleccioná al menos un evento para iniciar.")

# === MOSTRAR ESTADO DE CADA EVENTO ===
st.subheader("⏱️ Estado actual de eventos")

def mostrar_estado_evento(nombre_evento, emoji):
    ultimo_evento = coleccion_eventos.find_one({"evento": nombre_evento}, sort=[("fecha_hora", -1)])

    if ultimo_evento and "fecha_hora" in ultimo_evento:
        inicio = ultimo_evento["fecha_hora"].astimezone(colombia)
        ahora = datetime.now(colombia)

        if "fin" not in ultimo_evento:
            segundos_transcurridos = int((ahora - inicio).total_seconds())
            st.success(f"{emoji} Evento activo desde el {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
            cronometro = st.empty()
            stop_button = st.button(f"⏹️ Detener {emoji}")

            for i in range(segundos_transcurridos, segundos_transcurridos + 100000):
                if stop_button:
                    coleccion_eventos.update_one(
                        {"_id": ultimo_evento["_id"]},
                        {"$set": {"fin": ahora}}
                    )
                    st.success(f"{emoji} Evento finalizado")
                    st.rerun()

                duracion = str(timedelta(seconds=i))
                cronometro.markdown(f"### ⏱️ Duración: {duracion}")
                time.sleep(1)
        else:
            delta = ahora - inicio
            minutos = int(delta.total_seconds() // 60)
            detalle = str(timedelta(seconds=int(delta.total_seconds())))
            st.metric(f"{emoji} Racha sin evento", f"{minutos} min")
            st.caption(f"Último hace: {detalle}")
    else:
        st.metric(f"{emoji} Racha sin evento", "0 min")
        st.caption("Sin eventos válidos con campo 'fecha_hora'")

col3, col4 = st.columns(2)
with col3:
    mostrar_estado_evento(evento_a, "✊🏽")
with col4:
    mostrar_estado_evento(evento_b, "💸")

# === SECCIÓN: REFLEXIONES ===
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

# === HISTORIAL DE EVENTOS FINALIZADOS ===
st.subheader("📑 Historial de eventos")

def obtener_historial(evento_nombre):
    docs = list(coleccion_eventos.find({"evento": evento_nombre, "fin": {"$exists": True}}).sort("fecha_hora", -1))
    data = []
    for d in docs:
        inicio = d.get("fecha_hora", None)
        fin = d.get("fin", None)
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
    st.dataframe(obtener_historial(evento_a), use_container_width=True)
with tab2:
    st.dataframe(obtener_historial(evento_b), use_container_width=True)

# === HISTORIAL DE REFLEXIONES ===
st.subheader("📖 Reflexiones previas")
docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
for d in docs:
    fecha = d["fecha_hora"].astimezone(colombia)
    emociones = " ".join(e["emoji"] for e in d.get("emociones", []))
    texto = d.get("reflexion", "")
    with st.expander(f"{fecha.strftime('%Y-%m-%d %H:%M')} — {emociones}"):
        st.write(texto)