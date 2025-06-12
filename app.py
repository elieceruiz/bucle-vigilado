import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz

# Configuración general de la app
st.set_page_config(layout="centered", page_title="bucle-vigilado", initial_sidebar_state="collapsed")
st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)

# Conectar a MongoDB Atlas
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["bucle_vigilado"]
collection = db["eventos"]

# Zona horaria Colombia
colombia = pytz.timezone("America/Bogota")

# Función para calcular la racha en días
def calcular_racha(tipo_evento):
    eventos = list(collection.find({"tipo": tipo_evento}).sort("fecha", -1))
    if not eventos:
        return "—"
    ultimo = eventos[0]["fecha"].replace(tzinfo=pytz.UTC).astimezone(colombia)
    ahora = datetime.now(colombia)
    diferencia = (ahora - ultimo).days
    return f"{diferencia} día(s)"

# Registro de eventos
st.subheader("Registrar evento")

tipo_evento = st.selectbox("Tipo de evento", ["Tal Pago", "La Iniciativa Aquella"])
monto = st.number_input("Monto (si aplica)", min_value=0, step=1000)

usar_manual = st.checkbox("Ingresar fecha y hora manualmente")

if usar_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora = st.time_input("Hora", datetime.now(colombia).time(), step=60)
    fecha_completa = datetime.combine(fecha, hora)
    fecha_colombia = colombia.localize(fecha_completa)
else:
    fecha_colombia = datetime.now(colombia)

if st.button("Guardar evento"):
    nuevo_evento = {
        "tipo": tipo_evento,
        "fecha": fecha_colombia,
        "monto": monto if monto > 0 else None
    }
    collection.insert_one(nuevo_evento)
    st.success("✅ Evento guardado exitosamente")

# Visualización de rachas
st.subheader("Rachas activas")

col1, col2 = st.columns(2)

with col1:
    st.metric("💸 Tal Pago", calcular_racha("Tal Pago"))

with col2:
    st.metric("🌒 La Iniciativa Aquella", calcular_racha("La Iniciativa Aquella"))
