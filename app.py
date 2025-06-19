import streamlit as st
st.set_page_config(page_title="BucleVigiladoApp", layout="centered")

from datetime import datetime
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh

# Zona horaria
colombia = pytz.timezone("America/Bogota")

# Recarga automática cada segundo
st_autorefresh(interval=1000, key="refresh")

# Conexión MongoDB
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion = db["eventos"]

# Eventos
evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

# Inicializar sesión
for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# Función para registrar evento
def registrar_evento(nombre_evento, fecha_hora):
    coleccion.insert_one({
        "evento": nombre_evento,
        "fecha_hora": fecha_hora
    })
    st.session_state[nombre_evento] = fecha_hora

# Interfaz
st.title("BucleVigilado")

# Sección de registro
st.subheader("Registrar evento")

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

# Métricas
st.subheader("⏱️ Racha actual")
col3, col4 = st.columns(2)

def mostrar_racha(nombre_evento, emoji):
    if nombre_evento in st.session_state:
        ahora = datetime.now(colombia)
        ultimo = st.session_state[nombre_evento]
        delta = ahora - ultimo
        minutos = int(delta.total_seconds() // 60)
        rdelta = relativedelta(ahora, ultimo)
        detalle = f"{rdelta.years} años, {rdelta.months} meses, {rdelta.days} días, {rdelta.hours} h, {rdelta.minutes} min, {rdelta.seconds} s"
        st.metric(emoji, f"{minutos} minutos")
        st.caption(detalle)
    else:
        st.metric(emoji, "0 minutos")
        st.caption("0 años, 0 meses, 0 días, 0 h, 0 min, 0 s")

with col3:
    mostrar_racha(evento_a, "✊🏽")
with col4:
    mostrar_racha(evento_b, "💸")

# Historial
st.subheader("📑 Historial de registros")
tab1, tab2 = st.tabs(["✊🏽", "💸"])

def obtener_registros(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{"N°": total - i, "Fecha": f.date(), "Hora": f.strftime("%H:%M")} for i, f in enumerate(fechas)])

with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)

with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)