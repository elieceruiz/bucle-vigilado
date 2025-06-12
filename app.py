import streamlit as st
from datetime import datetime, time
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
import time as t

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

# Función para calcular la racha completa
def calcular_racha_completa(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    if not eventos:
        return {
            "minutos": 0,
            "años": 0,
            "meses": 0,
            "días": 0,
            "horas": 0,
            "minutos_restantes": 0,
            "segundos": 0
        }

    ultimo = eventos[0]["fecha_hora"].replace(tzinfo=colombia)
    ahora = datetime.now(colombia)
    diferencia = ahora - ultimo
    total_minutos = int(diferencia.total_seconds() // 60)
    total_segundos = int(diferencia.total_seconds())

    rdelta = relativedelta(ahora, ultimo)
    return {
        "minutos": total_minutos,
        "años": rdelta.years,
        "meses": rdelta.months,
        "días": rdelta.days,
        "horas": rdelta.hours,
        "minutos_restantes": rdelta.minutes,
        "segundos": rdelta.seconds
    }

# Función para obtener registros
def obtener_registros(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    fechas = [e["fecha_hora"].astimezone(colombia) for e in eventos]
    total = len(fechas)
    return pd.DataFrame([{"N°": total - i, "Fecha": f.date(), "Hora": f.time()} for i, f in enumerate(fechas)])

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

fecha_hora = None  # Inicializamos la variable

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
            st.success("🪞 Evento A registrado")
        if check_b:
            registrar_evento(evento_b, fecha_hora)
            st.success("💰 Evento B registrado")
        if not check_a and not check_b:
            st.warning("Selecciona al menos un evento para registrar.")

# Métricas en vivo
st.subheader("⏱️ Racha actual (en vivo)")

def mostrar_racha(nombre_evento, emoji):
    racha = calcular_racha_completa(nombre_evento)
    with st.container():
        st.markdown(f"### {emoji} {nombre_evento}")
        st.metric("Minutos", racha["minutos"])
        st.write(f"{racha['años']} años, {racha['meses']} meses, {racha['días']} días, {racha['horas']} horas, {racha['minutos_restantes']} minutos y {racha['segundos']} segundos")

col3, col4 = st.columns(2)
with col3:
    mostrar_racha(evento_a, "🪞")
with col4:
    mostrar_racha(evento_b, "💰")

# Historial
st.subheader("📑 Historial de registros")
tab1, tab2 = st.tabs(["🪞 A", "💰 B"])
with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)
with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)
