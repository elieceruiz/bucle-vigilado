import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import pytz

# Configurar zona horaria
tz = pytz.timezone("America/Bogota")
now = datetime.now(tz).replace(microsecond=0)

# Conexión a MongoDB Atlas desde secrets
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["centinela"]
coleccion_eventos = db["eventos"]

# Configuración de página
st.set_page_config(page_title="Centinela del Bucle", layout="centered")

st.title("🛡️ Centinela del Bucle")
st.write("Monitorea tu proceso y mantén la vigilancia del bucle.")

# Opciones de registro
evento = st.selectbox("¿Qué deseas registrar?", [
    "Selecciona una opción...",
    "La Iniciativa Aquella",
    "Intercambio sexual con pago"
])

# Función para calcular la racha
def calcular_racha(tipo_evento):
    eventos = list(coleccion_eventos.find({"tipo_evento": tipo_evento}).sort("timestamp", -1))
    if eventos:
        ultimo = eventos[0]["timestamp"]
        diferencia = (now - ultimo).days
        return diferencia
    return "Sin registros previos"

if evento != "Selecciona una opción...":
    st.markdown("### Registro")

    if evento == "Intercambio sexual con pago":
        monto = st.number_input("Monto aproximado (COP)", min_value=0, step=1000)
        metodo_pago = st.selectbox("Método de pago", ["Efectivo", "Transferencia", "Otro"])
        lugar = st.text_input("Lugar o zona aproximada")

    if st.button("Registrar evento"):
        registro = {
            "tipo_evento": evento,
            "timestamp": now,
            "registrado_en": now
        }

        if evento == "Intercambio sexual con pago":
            registro.update({
                "monto": monto,
                "metodo_pago": metodo_pago,
                "lugar": lugar
            })

        coleccion_eventos.insert_one(registro)
        st.success("✅ Evento registrado con éxito.")

    # Mostrar racha
    dias = calcular_racha(evento)
    st.info(f"📅 Han pasado **{dias} días** desde el último evento de tipo: **{evento}**.")

# Mostrar rachas acumuladas
st.markdown("---")
st.markdown("### 🧭 Estado actual")
col1, col2 = st.columns(2)

with col1:
    racha_aquella = calcular_racha("La Iniciativa Aquella")
    st.metric(label="🌀 La Iniciativa Aquella", value=f"{racha_aquella} días")

with col2:
    racha_pago = calcular_racha("Intercambio sexual con pago")
    st.metric(label="💸 Intercambio con pago", value=f"{racha_pago} días")
