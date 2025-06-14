import streamlit as st
st.set_page_config(page_title="🛡️ bucle-vigilado", layout="centered")

from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh

# Configuración de zona horaria
colombia = pytz.timezone("America/Bogota")

# Refrescar cada segundo
st_autorefresh(interval=1000, key="refresh")

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

# Calcular racha actual
def calcular_racha_detallada(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    if not eventos:
        return "0 minutos", "0 años, 0 meses, 0 días, 0 horas, 0 minutos, 0 segundos"
    ultimo = eventos[0]["fecha_hora"].astimezone(colombia)
    ahora = datetime.now(colombia)
    delta = ahora - ultimo
    total_minutos = int(delta.total_seconds() // 60)

    rdelta = relativedelta(ahora, ultimo)
    tiempo_detallado = f"{rdelta.years} años, {rdelta.months} meses, {rdelta.days} días, {rdelta.hours} horas, {rdelta.minutes} minutos, {rdelta.seconds} segundos"
    return f"{total_minutos} minutos", tiempo_detallado

# Obtener historial
def obtener_registros(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{"N°": total - i, "Fecha": f.date(), "Hora": f.strftime("%H:%M")} for i, f in enumerate(fechas)])

# Interfaz principal
st.title("🛡️ bucle-vigilado")

# Sección de registro
st.subheader("Registrar evento")
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽", value=False)
with col2:
    check_b = st.checkbox("💸", value=False)

usar_fecha_hora_manual = st.checkbox("Ingresar fecha y hora manualmente")
fecha_hora = None

if usar_fecha_hora_manual:
    fecha = st.date_input("Fecha", datetime.now(colombia).date())
    hora_texto = st.text_input("Hora (HH:MM, formato 24h)", value=datetime.now(colombia).strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora = datetime.combine(fecha, hora)
        fecha_hora = colombia.localize(fecha_hora)
    except ValueError:
        st.error("Formato de hora no válido. Usa HH:MM en formato 24h.")
else:
    fecha_hora = datetime.now(colombia)

if st.button("Registrar"):
    if fecha_hora:
        if check_a:
            registrar_evento(evento_a, fecha_hora)
            st.success("✊🏽 Evento registrado")
        if check_b:
            registrar_evento(evento_b, fecha_hora)
            st.success("💸 Evento registrado")
        if not check_a and not check_b:
            st.warning("Selecciona al menos un evento para registrar.")

# ⏱️ Racha actual
st.subheader("⏱️ Racha actual")

# Mostrar tabla sin encabezado ni índice
eventos = [evento_a, evento_b]
emojis = ["✊🏽", "💸"]
data = []

for nombre, emoji in zip(eventos, emojis):
    minutos, detalle = calcular_racha_detallada(nombre)
    data.append([emoji, minutos, detalle])

df_racha = pd.DataFrame(data, columns=["", "", ""])
st.dataframe(df_racha, hide_index=True, use_container_width=True)

# Historial de registros
st.subheader("📑 Historial de registros")
tab1, tab2 = st.tabs(["✊🏽", "💸"])

with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)