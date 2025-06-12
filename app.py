import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
import time
from dateutil.relativedelta import relativedelta

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

# Función para calcular diferencia desde último evento
def obtener_racha_detallada(nombre_evento):
    eventos = list(coleccion.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    if not eventos:
        return None
    ultimo = eventos[0]["fecha_hora"].replace(tzinfo=colombia)
    ahora = datetime.now(colombia)
    delta = relativedelta(ahora, ultimo)
    total_min = int((ahora - ultimo).total_seconds() // 60)
    total_sec = int((ahora - ultimo).total_seconds())
    return {
        "minutos": total_min,
        "segundos": total_sec,
        "años": delta.years,
        "meses": delta.months,
        "días": delta.days,
        "horas": delta.hours,
        "min": delta.minutes,
        "seg": delta.seconds
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

# Sección racha dinámica
st.subheader("⏱️ Racha en vivo")

col5, col6 = st.columns(2)

with col5:
    racha_a = st.empty()
with col6:
    racha_b = st.empty()

for _ in range(1000):  # Puedes ajustar la cantidad de actualizaciones si deseas
    datos_a = obtener_racha_detallada(evento_a)
    datos_b = obtener_racha_detallada(evento_b)

    if datos_a:
        racha_a.markdown(f"""
        ### 🪞 A  
        **{datos_a['minutos']} minutos**  
        ⏳ {datos_a['años']} años, {datos_a['meses']} meses, {datos_a['días']} días,  
        {datos_a['horas']} horas, {datos_a['min']} min, {datos_a['seg']} s
        """)
    else:
        racha_a.markdown("🪞 A: Sin registros.")

    if datos_b:
        racha_b.markdown(f"""
        ### 💰 B  
        **{datos_b['minutos']} minutos**  
        ⏳ {datos_b['años']} años, {datos_b['meses']} meses, {datos_b['días']} días,  
        {datos_b['horas']} horas, {datos_b['min']} min, {datos_b['seg']} s
        """)
    else:
        racha_b.markdown("💰 B: Sin registros.")

    time.sleep(1)

# Historial
st.subheader("📑 Historial de registros")
tab1, tab2 = st.tabs(["🪞 A", "💰 B"])
with tab1:
    df_a = obtener_registros(evento_a)
    st.dataframe(df_a, use_container_width=True, hide_index=True)
with tab2:
    df_b = obtener_registros(evento_b)
    st.dataframe(df_b, use_container_width=True, hide_index=True)
