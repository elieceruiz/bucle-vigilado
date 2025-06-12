import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta, time
import pytz
import pandas as pd

# Configuración inicial
st.set_page_config(layout="centered", page_title="bucle-vigilado", page_icon="🛡️")
st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)

# Conexión MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["bucle"]
coleccion = db["eventos"]

# Zona horaria Colombia
colombia = pytz.timezone("America/Bogota")

# Función para calcular la racha en minutos
def calcular_racha(evento):
    registros = list(coleccion.find({"evento": evento}).sort("fecha", -1))
    if registros:
        ultimo = registros[0]["fecha"]
        ahora = datetime.now(colombia)
        diferencia = ahora - ultimo
        return int(diferencia.total_seconds() // 60)
    return 0

# Función para guardar evento
def guardar_evento(evento, fecha):
    coleccion.insert_one({"evento": evento, "fecha": fecha})

# Formulario
st.write("")

col1, col2 = st.columns(2)
eventos = {
    "🪞 A": "La Iniciativa Aquella",
    "💰 B": "El Contacto Pago"
}

for col, (emoji, nombre_evento) in zip([col1, col2], eventos.items()):
    with col:
        st.subheader(emoji)
        if st.checkbox(f"Registrar {emoji}", key=nombre_evento):
            manual = st.checkbox(f"Elegir fecha y hora", key=nombre_evento + "_manual")
            if manual:
                fecha = st.date_input("Fecha", datetime.now(colombia).date(), key=nombre_evento + "_fecha")
                hora = st.time_input("Hora", datetime.now(colombia).time().replace(second=0), step=60, key=nombre_evento + "_hora")
                fecha_hora = datetime.combine(fecha, hora)
                fecha_hora = colombia.localize(fecha_hora)
            else:
                fecha_hora = datetime.now(colombia)
            guardar_evento(nombre_evento, fecha_hora)
            st.success("✅ Registro guardado")

# Métricas de racha
st.markdown("---")
col3, col4 = st.columns(2)
with col3:
    st.metric("🪞 A", f"{calcular_racha('La Iniciativa Aquella')} minutos")
with col4:
    st.metric("💰 B", f"{calcular_racha('El Contacto Pago')} minutos")

# Historial
st.markdown("---")
tabs = st.tabs(["Historial 🪞 A", "Historial 💰 B"])
for tab, (emoji, nombre_evento) in zip(tabs, eventos.items()):
    with tab:
        registros = list(coleccion.find({"evento": nombre_evento}).sort("fecha", -1))
        if registros:
            df = pd.DataFrame(registros)
            df["fecha"] = df["fecha"].dt.tz_convert(colombia)
            df = df[["fecha"]]
            df.columns = ["Fecha y Hora"]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay registros aún.")
