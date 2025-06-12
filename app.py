import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz

# Conexión a MongoDB
MONGO_URI = st.secrets["mongo_uri"]
client = MongoClient(MONGO_URI)
db = client["bucle"]
coleccion = db["eventos"]

# Zona horaria Colombia
colombia = pytz.timezone("America/Bogota")

# Función para registrar evento
def registrar_evento(tipo, fecha_hora):
    coleccion.insert_one({
        "tipo": tipo,
        "fecha_hora": fecha_hora
    })

# Función para calcular racha
def calcular_racha(tipo):
    registros = list(coleccion.find({"tipo": tipo}).sort("fecha_hora", -1))
    if not registros:
        return "–"
    ultimo = registros[0]["fecha_hora"].astimezone(colombia)
    now = datetime.now(colombia)
    diferencia = (now - ultimo).days
    return f"{diferencia} días"

# Función para mostrar historial
def mostrar_historial(tipo, titulo):
    st.subheader(titulo)
    registros = list(coleccion.find({"tipo": tipo}).sort("fecha_hora", -1))
    if not registros:
        st.info("No hay datos disponibles.")
    else:
        for r in registros:
            fecha_local = r["fecha_hora"].astimezone(colombia)
            st.markdown(f"- {fecha_local.strftime('%Y-%m-%d %H:%M')}")

# Interfaz
st.set_page_config(page_title="Registro de Ciclos", layout="centered")
st.markdown("## ⏳ Registro de Ciclos")

tabs = st.tabs(["🗓️ Nuevo Registro", "📚 Historial"])

# --- TAB REGISTRO ---
with tabs[0]:
    st.markdown("### Registrar un nuevo ciclo")
    tipo_a = st.checkbox("🪞 Ciclo A")
    tipo_b = st.checkbox("💸 Ciclo B")

    usar_ahora = st.checkbox("Usar hora actual", value=True)

    if usar_ahora:
        fecha_colombia = datetime.now(colombia)
    else:
        fecha = st.date_input("Fecha", datetime.now(colombia).date())
        hora_str = st.text_input("Hora (formato HH:MM)", value="00:00")
        try:
            hora = datetime.strptime(hora_str, "%H:%M").time()
            fecha_completa = datetime.combine(fecha, hora)
            fecha_colombia = colombia.localize(fecha_completa)
        except ValueError:
            st.error("❌ Hora inválida. Formato esperado: HH:MM (ej: 14:30)")
            st.stop()

    if tipo_a or tipo_b:
        if st.button("Guardar"):
            if tipo_a:
                registrar_evento("La Iniciativa Aquella", fecha_colombia)
                st.success("🪞 Ciclo A registrado")
            if tipo_b:
                registrar_evento("Pago por sexo", fecha_colombia)
                st.success("💸 Ciclo B registrado")

# Métricas
col1, col2 = st.columns(2)
with col1:
    st.metric("🪞 Ciclo A", calcular_racha("La Iniciativa Aquella"))
with col2:
    st.metric("💸 Ciclo B", calcular_racha("Pago por sexo"))

# --- TAB HISTORIAL ---
with tabs[1]:
    col1, col2 = st.columns(2)
    with col1:
        mostrar_historial("La Iniciativa Aquella", "📖 Ciclo A")
    with col2:
        mostrar_historial("Pago por sexo", "📘 Ciclo B")
