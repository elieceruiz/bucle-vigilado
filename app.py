import streamlit as st
from datetime import datetime, time
from pymongo import MongoClient
import pytz
import pandas as pd
import time as t  # Para el bucle de actualización en vivo

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

# Función para calcular la racha detallada
def calcular_racha_detallada(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    if not eventos:
        return "0 minutos", (0, 0, 0, 0, 0)
    ultimo = eventos[0]["fecha_hora"].replace(tzinfo=colombia)
    ahora = datetime.now(colombia)
    delta = ahora - ultimo

    total_segundos = int(delta.total_seconds())
    minutos = total_segundos // 60
    segundos = total_segundos % 60
    horas = minutos // 60
    dias = horas // 24
    meses = dias // 30
    años = meses // 12

    return f"{minutos} minutos", (años, meses % 12, dias % 30, horas % 24, minutos % 60, segundos)

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

# Métricas en tiempo real
st.subheader("⏱️ Racha actual en vivo")

placeholder = st.empty()

while True:
    with placeholder.container():
        col3, col4 = st.columns(2)
        with col3:
            label_a, (a_años, a_meses, a_dias, a_horas, a_min, a_seg) = calcular_racha_detallada(evento_a)
            st.metric("🪞 A", label_a)
            st.write(f"**{a_años}** años, **{a_meses}** meses, **{a_dias}** días")
            st.write(f"**{a_horas:02}**h **{a_min:02}**m **{a_seg:02}**s")
        with col4:
            label_b, (b_años, b_meses, b_dias, b_horas, b_min, b_seg) = calcular_racha_detallada(evento_b)
            st.metric("💰 B", label_b)
            st.write(f"**{b_años}** años, **{b_meses}** meses, **{b_dias}** días")
            st.write(f"**{b_horas:02}**h **{b_min:02}**m **{b_seg:02}**s")
    t.sleep(1)
