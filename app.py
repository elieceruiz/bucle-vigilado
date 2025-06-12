import streamlit as st
from datetime import datetime, time
from pymongo import MongoClient
import pytz
import pandas as pd

# Configuración de zona horaria
colombia = pytz.timezone("America/Bogota")

# Conexión a MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion = db["eventos"]

# Función para registrar eventos
def registrar_evento(nombre_evento, fecha_hora):
    coleccion.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })

# Función para calcular la racha en minutos
def calcular_racha(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    if not eventos:
        return 0
    ultimo = eventos[0]["fecha_hora"].replace(tzinfo=colombia)
    ahora = datetime.now(colombia)
    diferencia = ahora - ultimo
    return int(diferencia.total_seconds() // 60)

# Función para obtener registros
def obtener_registros(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    return pd.DataFrame([{
        "N°": i + 1,
        "Fecha": f.date(),
        "Hora": f.time()
    } for i, f in enumerate(fechas)])

# Interfaz
st.set_page_config(page_title="🛡️ bucle-vigilado", layout="centered")
st.title("🛡️ bucle-vigilado")

# Sección de registro
st.subheader("Registrar evento")
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("🪞 A", value=False)
with col2:
    check_b = st.checkbox("💰 B", value=False)

usar_fecha_hora_manual = st.checkbox("Ingresar fecha y hora manualmente")

fecha_hora = None  # Inicializamos

if usar_fecha_hora_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora = st.time_input("Hora", datetime.now(colombia).time())
    try:
        fecha_hora = colombia.localize(datetime.combine(fecha, hora))
    except Exception as e:
        st.error(f"Error al combinar fecha y hora: {e}")
else:
    fecha_hora = datetime.now(colombia)

if st.button("Registrar"):
    if fecha_hora is None:
        st.warning("Fecha y hora inválidas. Corrige los campos.")
    else:
        if check_a:
            registrar_evento(evento_a, fecha_hora)
            st.success("🪞 Evento A registrado")
        if check_b:
            registrar_evento(evento_b, fecha_hora)
            st.success("💰 Evento B registrado")
        if not check_a and not check_b:
            st.warning("Selecciona al menos un evento para registrar.")

# Métricas
st.subheader("⏱️ Racha actual (en minutos)")
col3, col4 = st.columns(2)
with col3:
    st.metric("🪞 A", calcular_racha(evento_a))
with col4:
    st.metric("💰 B", calcular_racha(evento_b))

# Historial
st.subheader("📑 Historial de registros")
tab1, tab2 = st.tabs(["🪞 A", "💰 B"])
with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True)
with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True)
