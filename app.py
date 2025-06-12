import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz

# Configuración regional
colombia = pytz.timezone("America/Bogota")

# Conexión a MongoDB
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["registro_eventos"]
collection = db["eventos"]

st.set_page_config(page_title="Bucle Vigilado", layout="centered")

st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)

st.title("")  # Eliminamos el encabezado visual

# Selección del tipo de evento
evento = st.selectbox("Tipo de evento", ["Pago", "La Iniciativa Aquella"])

# Checkbox para ingreso manual de fecha y hora
use_manual = st.checkbox("Ingresar fecha y hora manualmente")

if use_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora = st.time_input("Hora", datetime.now(colombia).time(), step=1)
    timestamp = colombia.localize(datetime.combine(fecha, hora))
else:
    timestamp = datetime.now(colombia)

# Campo para el monto (solo si es "Pago")
monto = None
if evento == "Pago":
    monto = st.number_input("Monto (opcional)", min_value=0.0, format="%.2f")

# Botón para registrar el evento
if st.button("Registrar"):
    registro = {
        "evento": evento,
        "timestamp": timestamp,
    }
    if monto is not None:
        registro["monto"] = monto
    collection.insert_one(registro)
    st.success("✅ Evento registrado exitosamente")

# Función para calcular racha desde el último evento
def calcular_racha(nombre_evento):
    registros = list(collection.find({"evento": nombre_evento}).sort("timestamp", -1))
    if not registros:
        return "Sin datos"
    ultimo = registros[0]["timestamp"]
    now = datetime.now(pytz.utc)
    diferencia = (now - ultimo).days
    return f"{diferencia} día(s)"

# Mostrar las rachas
col1, col2 = st.columns(2)
with col1:
    st.metric("💰 Pago", calcular_racha("Pago"))
with col2:
    st.metric("🌒 La Iniciativa Aquella", calcular_racha("La Iniciativa Aquella"))
