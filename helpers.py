# helpers.py

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import colombia, dias_semana_3letras, sistema_categorial
from db import coleccion_eventos, coleccion_reflexiones
from openai_client import openai_client


def formatear_delta(rd, incluir_segundos=False):
    partes = []
    if rd.years: partes.append(f"{rd.years}a")
    if rd.months: partes.append(f"{rd.months}m")
    if rd.days: partes.append(f"{rd.days}d")
    if rd.hours: partes.append(f"{rd.hours}h")
    if rd.minutes: partes.append(f"{rd.minutes}m")
    if incluir_segundos and rd.seconds: partes.append(f"{rd.seconds}s")
    return " ".join(partes) if partes else "0m"


def minutos_a_tiempo_humano(minutos):
    ahora = datetime.now(colombia)
    futuro = ahora + timedelta(minutes=minutos)
    rd = relativedelta(futuro, ahora)

    partes = []
    if rd.years: partes.append(f"{rd.years} años")
    if rd.months: partes.append(f"{rd.months} meses")
    if rd.days: partes.append(f"{rd.days} días")
    if rd.hours: partes.append(f"{rd.hours} horas")
    if rd.minutes: partes.append(f"{rd.minutes} minutos")

    return ", ".join(partes) if partes else "0 minutos"


def clasificar_reflexion_openai(texto):
    prompt = f"""Sistema categorial para clasificar reflexiones:

1.1 Organización del tiempo
1.2 Relaciones sociales
1.3 Contextos de intimidad
1.4 Factores emocionales

2.1 Motivaciones
2.2 Prácticas asociadas
2.3 Representaciones
2.4 Efectos en la trayectoria íntima

3.1 Prácticas de autocuidado
3.2 Placer y exploración del cuerpo
3.3 Relación con la intimidad
3.4 Representaciones culturales

Reflexión: \"\"\"{texto}\"\"\"
"""
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
        "reflexion": texto.strip(),
        "categoria_categorial": categoria
    })
    return categoria


def registrar_evento(nombre, fecha):
    coleccion_eventos.insert_one({"evento": nombre, "fecha_hora": fecha})


def obtener_registros(nombre):
    eventos_db = list(coleccion_eventos.find({"evento": nombre}).sort("fecha_hora", -1))
    filas = []

    for i, e in enumerate(eventos_db):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos_db[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos_db) else None
        diff = formatear_delta(relativedelta(fecha, anterior)) if anterior else ""

        filas.append({
            "Día": dias_semana_3letras[fecha.weekday()],
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Intervalo": diff
        })

    df = pd.DataFrame(filas)
    df.index = range(len(df), 0, -1)
    df.index.name = "#"
    return df


def obtener_reflexiones():
    registros = list(coleccion_reflexiones.find().sort("fecha_hora", -1))
    filas = []

    for r in registros:
        fecha = r["fecha_hora"].astimezone(colombia)
        cat_info = sistema_categorial.get(r.get("categoria_categorial", ""), {
            "categoria": "Sin categoría", "subcategoria": "", "descriptor": "", "observable": ""
        })

        filas.append({
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Reflexión": r.get("reflexion", ""),
            "Categoría": cat_info["categoria"],
            "Subcategoría": cat_info["subcategoria"],
            "Descriptor": cat_info.get("descriptor", ""),
            "Observable": cat_info.get("observable", ""),
            "Emociones": " ".join([e["emoji"] for e in r.get("emociones", [])])
        })

    return pd.DataFrame(filas)


def mostrar_racha(nombre_evento, emoji):
    estado = f"cronometro_activo_{nombre_evento}"
    if estado not in st.session_state:
        st.session_state[estado] = False

    st.markdown("### ⏱️ Racha")

    cambiar_estado = st.checkbox("Cronómetro activo",
                                 value=st.session_state[estado],
                                 key=f"chk_{nombre_evento}")

    st.session_state[estado] = cambiar_estado

    if st.session_state[estado]:
        st_autorefresh(interval=1000, key=f"refresh_{nombre_evento}")

    if nombre_evento not in st.session_state:
        st.metric("Duración", "0 min")
        return

    inicio = st.session_state[nombre_evento]
    ahora = datetime.now(colombia)

    delta = ahora - inicio
    rd = relativedelta(ahora, inicio)

    st.metric(
        "Duración",
        f"{int(delta.total_seconds() // 60)} min [COP]",
        formatear_delta(rd, incluir_segundos=True)
    )
