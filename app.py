import streamlit as st
from datetime import datetime, time
from pymongo import MongoClient
import pytz

# Zona horaria de Colombia
colombia = pytz.timezone("America/Bogota")

# Conexion MongoDB
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["bucle_vigilado"]

st.set_page_config(page_title="bucle-vigilado", layout="centered")
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🪞 A | 💰 B")

# Registro manual
st.subheader("Registrar evento")
evento_A = st.checkbox("Registrar evento A 🪞")
evento_B = st.checkbox("Registrar evento B 💰")

usar_fecha_hora_manual = st.checkbox("Usar fecha y hora manual")
if usar_fecha_hora_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora = st.time_input("Hora", value=datetime.now(colombia).time(), step=60)
    dt = datetime.combine(fecha, hora)
    timestamp = colombia.localize(dt)
else:
    timestamp = datetime.now(colombia)

if st.button("Guardar evento"):
    if evento_A:
        db["La Iniciativa Aquella"].insert_one({"timestamp": timestamp})
        st.success("Evento A registrado")
    if evento_B:
        db["El Intercambio Monetario"].insert_one({"timestamp": timestamp})
        st.success("Evento B registrado")

# Función para calcular racha en minutos
def calcular_racha(evento):
    collection = db[evento]
    ultimo_registro = collection.find_one(sort=[("timestamp", -1)])
    if not ultimo_registro:
        return "—"
    ultimo = ultimo_registro["timestamp"]
    ahora = datetime.now(colombia)
    diferencia = ahora - ultimo
    minutos = int(diferencia.total_seconds() // 60)
    return f"{minutos} min"

# Mostrar rachas
st.subheader("⏱️ Rachas actuales")
st.metric("🪞 A", calcular_racha("La Iniciativa Aquella"))
st.metric("💰 B", calcular_racha("El Intercambio Monetario"))

# Mostrar historial
st.subheader("📖 Historial de eventos")
mostrar_A = st.checkbox("Mostrar historial A 🪞")
mostrar_B = st.checkbox("Mostrar historial B 💰")

def mostrar_historial(evento):
    collection = db[evento]
    registros = list(collection.find().sort("timestamp", -1))
    if not registros:
        st.write("No hay registros.")
        return
    data = [{
        "Fecha": r["timestamp"].astimezone(colombia).strftime("%Y-%m-%d"),
        "Hora": r["timestamp"].astimezone(colombia).strftime("%H:%M")
    } for r in registros]
    st.dataframe(data, use_container_width=True)

if mostrar_A:
    st.write("### 🪞 A")
    mostrar_historial("La Iniciativa Aquella")

if mostrar_B:
    st.write("### 💰 B")
    mostrar_historial("El Intercambio Monetario")
