import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz

# Conexión a MongoDB
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["bucle_vigilado"]

# Zona horaria de Colombia
colombia = pytz.timezone("America/Bogota")

st.set_page_config(layout="centered")

st.markdown("## Registro de Eventos")
evento = st.selectbox("¿Qué vas a registrar?", ["Pago", "La Iniciativa Aquella"])

# Opción automática o manual
modo = st.radio("¿Cómo querés registrar el evento?", ["Automático (ahora)", "Manual (fecha y hora pasadas)"])

# Registro manual
if modo == "Manual (fecha y hora pasadas)":
    fecha = st.date_input("Fecha")
    hora = st.time_input("Hora")
    timestamp = colombia.localize(datetime.combine(fecha, hora))
else:
    timestamp = datetime.now(colombia)

# Campo para el monto solo si es "Pago"
monto = None
if evento == "Pago":
    monto = st.number_input("¿Cuánto fue el monto?", min_value=0.0, format="%.2f")

if st.button("Guardar evento"):
    data = {"timestamp": timestamp}
    if monto is not None:
        data["monto"] = monto

    db[evento].insert_one(data)
    st.success(f"✅ Evento registrado para: {evento}")

# Función para calcular racha
def calcular_racha(nombre_evento):
    coleccion = db[nombre_evento]
    ultimo_evento = coleccion.find_one(sort=[("timestamp", -1)])
    
    if not ultimo_evento:
        return "Sin registros"

    ultimo = ultimo_evento["timestamp"]
    if isinstance(ultimo, str):
        try:
            ultimo = datetime.fromisoformat(ultimo)
        except ValueError:
            return "Fecha inválida"

    now = datetime.now(colombia)
    diferencia = (now - ultimo).days
    return f"{diferencia} días desde el último evento"

# Mostrar rachas
st.markdown("## Rachas actuales")
col1, col2 = st.columns(2)

with col1:
    st.metric("📆 Pago", calcular_racha("Pago"))
with col2:
    st.metric("🌒 La Iniciativa Aquella", calcular_racha("La Iniciativa Aquella"))
