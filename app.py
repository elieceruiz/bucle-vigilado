import streamlit as st
st.set_page_config(page_title="🛡️ bucle-vigilado", layout="centered")

from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh

# Zona horaria
colombia = pytz.timezone("America/Bogota")
ahora = datetime.now(colombia)

# Autorefresh cada segundo
st_autorefresh(interval=1000, key="refresh")

# Conexión MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion = db["eventos"]

# Eventos
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# Cargar todos los eventos de una vez
eventos_a = list(coleccion.find({"evento": evento_a}).sort("fecha_hora", -1))
eventos_b = list(coleccion.find({"evento": evento_b}).sort("fecha_hora", -1))

# Función para registrar eventos
def registrar_evento(nombre_evento, fecha_hora):
    coleccion.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })

# Calcular racha detallada
def calcular_racha_detallada(eventos, ahora):
    if not eventos:
        return "0 minutos", "0 años, 0 meses, 0 días, 0 horas, 0 minutos, 0 segundos"
    ultimo = eventos[0]["fecha_hora"].astimezone(colombia)
    delta = ahora - ultimo
    total_minutos = int(delta.total_seconds() // 60)
    rdelta = relativedelta(ahora, ultimo)
    tiempo_detallado = f"{rdelta.years} años, {rdelta.months} meses, {rdelta.days} días, {rdelta.hours} horas, {rdelta.minutes} minutos, {rdelta.seconds} segundos"
    return f"{total_minutos} minutos", tiempo_detallado

# Obtener DataFrame de registros
def obtener_registros(eventos):
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{"N°": total - i, "Fecha": f.date(), "Hora": f.strftime("%H:%M")} for i, f in enumerate(fechas)])

# Interfaz
st.title("🛡️ bucle-vigilado")
st.subheader("Registrar evento")

# Controles de registro
col1, col2 = st.columns(2)
with col1:
    check_a = st.checkbox("✊🏽", value=False)
with col2:
    check_b = st.checkbox("💸", value=False)

usar_fecha_hora_manual = st.checkbox("Ingresar fecha y hora manualmente")
fecha_hora = ahora

if usar_fecha_hora_manual:
    fecha = st.date_input("Fecha", ahora.date())
    hora_texto = st.text_input("Hora (HH:MM, formato 24h)", value=ahora.strftime("%H:%M"))
    try:
        hora = datetime.strptime(hora_texto, "%H:%M").time()
        fecha_hora = colombia.localize(datetime.combine(fecha, hora))
    except ValueError:
        st.error("Formato de hora no válido. Usa HH:MM en formato 24h.")

if st.button("Registrar"):
    if check_a:
        registrar_evento(evento_a, fecha_hora)
        st.success("✊🏽 Evento registrado")
    if check_b:
        registrar_evento(evento_b, fecha_hora)
        st.success("💸 Evento registrado")
    if not check_a and not check_b:
        st.warning("Selecciona al menos un evento para registrar.")

# Métricas
st.subheader("⏱️ Racha actual")
col3, col4 = st.columns(2)

with col3:
    minutos_a, detalle_a = calcular_racha_detallada(eventos_a, ahora)
    st.metric("✊🏽", minutos_a)
    st.caption(detalle_a)

with col4:
    minutos_b, detalle_b = calcular_racha_detallada(eventos_b, ahora)
    st.metric("💸", minutos_b)
    st.caption(detalle_b)

# Historial de registros
st.subheader("📑 Historial de registros")
tab1, tab2 = st.tabs(["✊🏽", "💸"])

with tab1:
    with st.expander("Ver historial ✊🏽"):
        df_a = obtener_registros(eventos_a)
        st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    with st.expander("Ver historial 💸"):
        df_b = obtener_registros(eventos_b)
        st.dataframe(df_b, use_container_width=True, hide_index=True)