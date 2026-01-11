import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI

# =========================
# CONFIGURACIÓN GENERAL
# =========================

st.set_page_config(page_title="Reinicia", layout="centered")

colombia = pytz.timezone("America/Bogota")

dias_semana_es = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}

dias_semana_3letras = {
    0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"
}

# =========================
# BASE DE DATOS
# =========================

client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_hitos = db["hitos"]
coleccion_visual = db["log_visual"]

# =========================
# OPENAI
# =========================

openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# =========================
# EVENTOS
# =========================

evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"

eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial": "historial",
    "✊🏽": evento_a,
    "💸": evento_b,
}

# =========================
# SISTEMA CATEGORIAL
# =========================

sistema_categorial = {
    "1.1": {"categoria": "Dinámicas cotidianas", "subcategoria": "Organización del tiempo",
            "descriptor": "Manejo de rutinas y distribución del día",
            "observable": "Relatos sobre horarios de trabajo, estudio, ocio."},
    "1.2": {"categoria": "Dinámicas cotidianas", "subcategoria": "Relaciones sociales",
            "descriptor": "Interacciones sociales.",
            "observable": "Pareja, amigos, familia."},
    "1.3": {"categoria": "Dinámicas cotidianas", "subcategoria": "Contextos de intimidad",
            "descriptor": "Espacios físicos y virtuales.",
            "observable": "Casa, internet, privacidad."},
    "1.4": {"categoria": "Dinámicas cotidianas", "subcategoria": "Factores emocionales",
            "descriptor": "Estados afectivos.",
            "observable": "Ansiedad, deseo, culpa."},
    "2.1": {"categoria": "Consumo de sexo pago", "subcategoria": "Motivaciones",
            "descriptor": "Razones del consumo.",
            "observable": "Placer, compañía."},
    "2.2": {"categoria": "Consumo de sexo pago", "subcategoria": "Prácticas asociadas",
            "descriptor": "Formas de acceso.",
            "observable": "Frecuencia, pago."},
    "2.3": {"categoria": "Consumo de sexo pago", "subcategoria": "Representaciones",
            "descriptor": "Significados.",
            "observable": "Normalización, estigma."},
    "2.4": {"categoria": "Consumo de sexo pago", "subcategoria": "Efectos",
            "descriptor": "Impacto personal.",
            "observable": "Aprendizaje, culpa."},
    "3.1": {"categoria": "Masturbación", "subcategoria": "Autocuidado",
            "descriptor": "Bienestar.",
            "observable": "Relajación."},
    "3.2": {"categoria": "Masturbación", "subcategoria": "Placer",
            "descriptor": "Exploración corporal.",
            "observable": "Satisfacción."},
    "3.3": {"categoria": "Masturbación", "subcategoria": "Intimidad",
            "descriptor": "Privacidad.",
            "observable": "Soledad."},
    "3.4": {"categoria": "Masturbación", "subcategoria": "Representaciones",
            "descriptor": "Sentido cultural.",
            "observable": "Vergüenza, normalización."},
}

# =========================
# CARGA ESTADO INICIAL
# =========================

for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

# =========================
# FUNCIONES
# =========================

def clasificar_reflexion_openai(texto):
    prompt = f"""Clasificá la reflexión según el sistema categorial.
Reflexión: \"\"\"{texto}\"\"\""""
    r = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5
    )
    return r.choices[0].message.content.strip()

def guardar_reflexion(fecha, emociones, texto):
    categoria = clasificar_reflexion_openai(texto)
    coleccion_reflexiones.insert_one({
        "fecha_hora": fecha,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": texto,
        "categoria_categorial": categoria
    })
    return categoria

def registrar_evento(nombre, fecha):
    coleccion_eventos.insert_one({"evento": nombre, "fecha_hora": fecha})
    st.session_state[nombre] = fecha
    st.rerun()

def obtener_registros(nombre):
    eventos = list(coleccion_eventos.find({"evento": nombre}).sort("fecha_hora", -1))
    filas = []
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos[i+1]["fecha_hora"].astimezone(colombia) if i+1 < len(eventos) else None
        diff = ""
        if anterior:
            d = relativedelta(fecha, anterior)
            diff = f"{d.days}d {d.hours}h {d.minutes}m"
        filas.append({
            "Día": dias_semana_3letras[fecha.weekday()],
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Sin recaída": diff
        })
    return pd.DataFrame(filas)

# =========================
# 🔧 CRONÓMETRO CORREGIDO
# =========================

def mostrar_racha(nombre_evento, emoji):
    estado = f"cronometro_activo_{nombre_evento}"
    if estado not in st.session_state:
        st.session_state[estado] = False

    st.markdown("### ⏱️ Racha")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Activar cronómetro" if not st.session_state[estado] else "⏸️ Pausar cronómetro"):
            st.session_state[estado] = not st.session_state[estado]
            st.rerun()

    if not st.session_state.get(nombre_evento):
        st.metric("Duración", "0 min")
        return

    if st.session_state[estado]:
        st_autorefresh(interval=1000, key=f"refresh_{nombre_evento}")

    ultimo = st.session_state[nombre_evento]
    ahora = datetime.now(colombia)
    delta = ahora - ultimo
    d = relativedelta(ahora, ultimo)

    st.metric(
        "Duración",
        f"{int(delta.total_seconds()//60)} min",
        f"{d.days}d {d.hours}h {d.minutes}m {d.seconds}s"
    )

# =========================
# INTERFAZ PRINCIPAL
# =========================

st.title("Reinicia")

seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

if opcion in [evento_a, evento_b]:
    if st.button("☠️ ¿Registrar?"):
        registrar_evento(opcion, datetime.now(colombia))
    mostrar_racha(opcion, seleccion)

elif opcion == "reflexion":
    emociones = st.multiselect("¿Cómo te sentías?", [
        "😰 Ansioso", "😡 Irritado", "💪 Firme",
        "😌 Tranquilo", "😓 Culpable", "😔 Triste"
    ])
    texto = st.text_area("¿Querés dejar algo escrito?")
    if texto or emociones:
        if st.button("📝 Guardar reflexión"):
            cat = guardar_reflexion(datetime.now(colombia), emociones, texto)
            st.success(f"Guardado ({cat})")
            st.rerun()

elif opcion == "historial":
    tabs = st.tabs(["🧠", "✊🏽", "💸"])
    with tabs[0]:
        df = obtener_reflexiones()
        for _, r in df.iterrows():
            with st.expander(f"{r['Fecha']} {r['Hora']}"):
                st.write(r["Reflexión"])
    with tabs[1]:
        st.dataframe(obtener_registros(evento_a))
    with tabs[2]:
        st.dataframe(obtener_registros(evento_b))