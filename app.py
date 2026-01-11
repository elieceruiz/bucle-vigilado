import streamlit as st
from datetime import datetime
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

# =========================
# OPENAI
# =========================

openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

# =========================
# EVENTOS
# =========================

EVENTO_A = "La Iniciativa Aquella"
EVENTO_B = "La Iniciativa de Pago"

eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial": "historial",
    "✊🏽": EVENTO_A,
    "💸": EVENTO_B,
}

# =========================
# CARGA ESTADO INICIAL
# =========================

for ev in [EVENTO_A, EVENTO_B]:
    if ev not in st.session_state:
        ultimo = coleccion_eventos.find_one(
            {"evento": ev},
            sort=[("fecha_hora", -1)]
        )
        if ultimo:
            st.session_state[ev] = ultimo["fecha_hora"].astimezone(colombia)

# =========================
# FUNCIONES
# =========================

def clasificar_reflexion_openai(texto):
    prompt = f"""Clasificá la siguiente reflexión usando un código del sistema categorial.
Reflexión: \"\"\"{texto}\"\"\""""
    r = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=6
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
    coleccion_eventos.insert_one({
        "evento": nombre,
        "fecha_hora": fecha
    })
    st.session_state[nombre] = fecha
    st.rerun()

# =========================
# REGISTROS (MESES + ÍNDICE)
# =========================

def obtener_registros(nombre):
    eventos = list(
        coleccion_eventos.find({"evento": nombre}).sort("fecha_hora", -1)
    )

    filas = []
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = (
            eventos[i + 1]["fecha_hora"].astimezone(colombia)
            if i + 1 < len(eventos) else None
        )

        if anterior:
            d = relativedelta(fecha, anterior)
            diff = f"{d.months}m {d.days}d {d.hours}h {d.minutes}m"
        else:
            diff = "0m 0d 0h 0m"

        filas.append({
            "Día": dias_semana_3letras[fecha.weekday()],
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Sin recaída": diff
        })

    df = pd.DataFrame(filas)

    # numeración descendente (más reciente = número más alto)
    df.index = range(len(df), 0, -1)
    df.index.name = "#"

    return df

def obtener_reflexiones():
    registros = list(
        coleccion_reflexiones.find().sort("fecha_hora", -1)
    )

    filas = []
    for r in registros:
        fecha = r["fecha_hora"].astimezone(colombia)
        filas.append({
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Reflexión": r.get("reflexion", ""),
            "Categoría": r.get("categoria_categorial", ""),
            "Emociones": " ".join(
                [e["emoji"] for e in r.get("emociones", [])]
            )
        })

    return pd.DataFrame(filas)

# =========================
# CRONÓMETRO CONTROLADO (FIX PAUSA)
# =========================

def mostrar_racha(nombre_evento, emoji):
    estado = f"cronometro_activo_{nombre_evento}"
    if estado not in st.session_state:
        st.session_state[estado] = False

    st.markdown("### ⏱️ Racha")

    if st.button(
        "▶️ Activar cronómetro" if not st.session_state[estado] else "⏸️ Pausar cronómetro",
        key=f"btn_{nombre_evento}"
    ):
        # ⛔ NO rerun acá (Streamlit ya lo hace)
        st.session_state[estado] = not st.session_state[estado]

    if nombre_evento not in st.session_state:
        st.metric("Duración", "0 min")
        return

    if st.session_state[estado]:
        st_autorefresh(interval=1000, key=f"refresh_{nombre_evento}")

    inicio = st.session_state[nombre_evento]
    ahora = datetime.now(colombia)
    delta = ahora - inicio
    d = relativedelta(ahora, inicio)

    st.metric(
        "Duración",
        f"{int(delta.total_seconds() // 60)} min",
        f"{d.months}m {d.days}d {d.hours}h {d.minutes}m {d.seconds}s"
    )

# =========================
# INTERFAZ PRINCIPAL
# =========================

st.title("Reinicia")

seleccion = st.selectbox(
    "Seleccioná qué registrar o consultar:",
    list(eventos.keys())
)
opcion = eventos[seleccion]

if opcion in [EVENTO_A, EVENTO_B]:
    if st.button("☠️ Registrar evento"):
        registrar_evento(opcion, datetime.now(colombia))

    mostrar_racha(opcion, seleccion)

elif opcion == "reflexion":
    emociones = st.multiselect(
        "¿Cómo te sentías?",
        ["😰 Ansioso", "😡 Irritado", "💪 Firme", "😌 Tranquilo", "😓 Culpable", "😔 Triste"]
    )
    texto = st.text_area("¿Querés dejar algo escrito?")

    if texto or emociones:
        if st.button("📝 Guardar reflexión"):
            categoria = guardar_reflexion(datetime.now(colombia), emociones, texto)
            st.success(f"Reflexión guardada ({categoria})")
            st.rerun()

elif opcion == "historial":
    tabs = st.tabs(["🧠 Reflexiones", "✊🏽 Evento A", "💸 Evento B"])

    with tabs[0]:
        df = obtener_reflexiones()
        for _, r in df.iterrows():
            with st.expander(f"{r['Fecha']} {r['Hora']} {r['Emociones']}"):
                st.write(r["Reflexión"])
                st.caption(f"Categoría: {r['Categoría']}")

    with tabs[1]:
        st.dataframe(
            obtener_registros(EVENTO_A),
            use_container_width=True,
            hide_index=False
        )

    with tabs[2]:
        st.dataframe(
            obtener_registros(EVENTO_B),
            use_container_width=True,
            hide_index=False
        )