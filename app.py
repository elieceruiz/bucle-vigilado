import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import pandas as pd

# Configurar zona horaria Colombia
colombia = pytz.timezone("America/Bogota")

# Conexión a MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["bucle_vigilado"]
coleccion = db["eventos"]

# Estética
st.set_page_config(page_title="bucle-vigilado", layout="centered")
st.markdown("## 🛡️ Centinela activo")

# Tabs principales
tab1, tab2 = st.tabs(["📝 Registro", "📊 Historial"])

with tab1:
    st.markdown("### Registrar evento")

    evento_A = st.checkbox("Registrar 🪞 A (aquello)")
    evento_B = st.checkbox("Registrar 💰 B (pago)")

    usar_manual = st.checkbox("Ingresar fecha y hora manualmente")

    if usar_manual:
        fecha = st.date_input("Fecha", datetime.now(colombia).date())
        hora = st.time_input("Hora", datetime.now(colombia).time(), step=timedelta(minutes=1))
        fecha_hora = datetime.combine(fecha, hora)
        fecha_hora = colombia.localize(fecha_hora)
    else:
        fecha_hora = datetime.now(colombia)

    if st.button("Guardar registro"):
        if evento_A or evento_B:
            if evento_A:
                coleccion.insert_one({
                    "evento": "La Iniciativa Aquella",
                    "timestamp": fecha_hora
                })
            if evento_B:
                coleccion.insert_one({
                    "evento": "Pago por sexo",
                    "timestamp": fecha_hora
                })
            st.success("Registro guardado correctamente.")
        else:
            st.warning("Selecciona al menos un evento para registrar.")

    st.divider()

    # Métricas de racha en minutos
    def calcular_racha(evento):
        registros = list(coleccion.find({"evento": evento}).sort("timestamp", -1))
        if not registros:
            return "—"
        ultimo = registros[0]["timestamp"]
        ahora = datetime.now(colombia)
        diferencia = ahora - ultimo
        minutos = int(diferencia.total_seconds() // 60)
        return f"{minutos} min"

    col1, col2 = st.columns(2)
    with col1:
        st.metric("🪞 A", calcular_racha("La Iniciativa Aquella"))
    with col2:
        st.metric("💰 B", calcular_racha("Pago por sexo"))

with tab2:
    st.markdown("### Historial de eventos")

    registros = list(coleccion.find().sort("timestamp", -1))
    if registros:
        df = pd.DataFrame(registros)
        df["timestamp"] = df["timestamp"].dt.tz_convert(colombia)
        df["fecha"] = df["timestamp"].dt.strftime("%Y-%m-%d")
        df["hora"] = df["timestamp"].dt.strftime("%H:%M")
        df = df[["evento", "fecha", "hora"]]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🪞 A")
            st.dataframe(df[df["evento"] == "La Iniciativa Aquella"].reset_index(drop=True))
        with col2:
            st.markdown("#### 💰 B")
            st.dataframe(df[df["evento"] == "Pago por sexo"].reset_index(drop=True))
    else:
        st.info("No hay registros aún.")
