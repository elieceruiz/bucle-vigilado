import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pytz

# Zona horaria de Colombia
colombia = pytz.timezone("America/Bogota")

# Conexión a MongoDB desde secrets
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["bucle_vigilado"]

st.set_page_config(page_title="Bucle Vigilado", layout="centered")

st.markdown("---")

def calcular_racha(nombre_evento):
    coleccion = db[nombre_evento]
    ultimo_evento = coleccion.find_one(sort=[("timestamp", -1)])
    
    if not ultimo_evento:
        return "Sin registros"

    ultimo = ultimo_evento["timestamp"]

    # Intentar convertir string a datetime
    if isinstance(ultimo, str):
        try:
            ultimo = datetime.fromisoformat(ultimo)
        except ValueError:
            return "Fecha inválida"

    # Forzar zona horaria Colombia
    if isinstance(ultimo, datetime):
        if ultimo.tzinfo is None:
            ultimo = colombia.localize(ultimo)
        else:
            ultimo = ultimo.astimezone(colombia)
    else:
        return "Formato inválido"

    now = datetime.now(colombia)
    diferencia = (now - ultimo).days
    return f"{diferencia} días desde el último evento"

# Registro
st.title("📌 Registro de eventos")
evento = st.radio("Seleccioná tipo de evento:", ["💰 Pago por sexo", "🌒 La Iniciativa Aquella"])
nombre_evento = "Pago" if evento == "💰 Pago por sexo" else "Iniciativa"

modo = st.radio("¿Cómo registrar la hora?", ["🕒 Ahora", "📅 Manual"])

if modo == "📅 Manual":
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora = st.time_input("Hora", datetime.now(colombia).time())
    timestamp = colombia.localize(datetime.combine(fecha, hora))
else:
    timestamp = datetime.now(colombia)

# Campos extra solo para pagos
monto = ""
sitio = ""
if nombre_evento == "Pago":
    monto = st.text_input("💵 Monto pagado (opcional)")
    sitio = st.text_input("📍 Sitio o método (opcional)")

if st.button("Registrar evento"):
    coleccion = db[nombre_evento]
    registro = {"timestamp": timestamp}
    if nombre_evento == "Pago":
        registro["monto"] = monto
        registro["sitio"] = sitio
    coleccion.insert_one(registro)
    st.success("✅ Evento registrado con éxito.")

st.markdown("---")
st.subheader("📊 Racha actual")
col1, col2 = st.columns(2)
col1.metric("💰 Pago por sexo", calcular_racha("Pago"))
col2.metric("🌒 La Iniciativa Aquella", calcular_racha("Iniciativa"))
