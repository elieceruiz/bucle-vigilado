import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import pandas as pd

st.set_page_config(page_title="Bucle Vigilado", layout="centered", initial_sidebar_state="collapsed")
st.markdown("## Vigilancia en Curso")
st.markdown("Una app de monitoreo personal.")

# Conexión a MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["bucle"]
col = db["eventos"]

colombia = pytz.timezone("America/Bogota")

# =====================
# FUNCIONES
# =====================

def obtener_registros(evento):
    registros = list(col.find({"evento": evento}).sort("fecha", -1))
    return registros

def calcular_racha(evento):
    registros = obtener_registros(evento)
    if not registros:
        return "—"

    ultimo = registros[0]["fecha"]
    ahora = datetime.now(colombia)
    diferencia = ahora - ultimo
    return f"{int(diferencia.total_seconds() // 60)} min"

def registrar_evento(evento, fecha_hora):
    doc = {
        "evento": evento,
        "fecha": fecha_hora
    }
    col.insert_one(doc)
    st.success("✅ Registro guardado")

# =====================
# REGISTRO NUEVO
# =====================

st.markdown("### 📌 Nuevo Registro")

evento_a = st.checkbox("🪞 A")
evento_b = st.checkbox("💸 B")

usar_manual = st.checkbox("⏰ Registrar manualmente")

if usar_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora = st.time_input("Hora", datetime.now(colombia).time())
    fecha_hora = colombia.localize(datetime.combine(fecha, hora))
else:
    fecha_hora = datetime.now(colombia)

if st.button("Registrar"):
    if evento_a:
        registrar_evento("La Iniciativa Aquella", fecha_hora)
    if evento_b:
        registrar_evento("Pago por Sexo", fecha_hora)
    if not evento_a and not evento_b:
        st.warning("Seleccioná al menos un evento.")

# =====================
# RACHAS
# =====================

st.markdown("### 📈 Rachas actuales")

col1, col2 = st.columns(2)

with col1:
    st.metric("🪞 A", calcular_racha("La Iniciativa Aquella"))

with col2:
    st.metric("💸 B", calcular_racha("Pago por Sexo"))

# =====================
# HISTORIAL EN TABS
# =====================

st.markdown("### 📜 Historial")

tabs = st.tabs(["🪞 A", "💸 B"])

for i, evento in enumerate(["La Iniciativa Aquella", "Pago por Sexo"]):
    with tabs[i]:
        registros = obtener_registros(evento)
        if registros:
            fechas = [r["fecha"].astimezone(colombia) for r in registros]
            data = pd.DataFrame({
                "Fecha": [f.date() for f in fechas],
                "Hora": [f.strftime("%H:%M") for f in fechas]
            })
            st.dataframe(data, use_container_width=True)
        else:
            st.info("No hay registros aún.")
