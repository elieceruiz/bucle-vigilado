import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI

st.set_page_config(page_title="Reinicia", layout="centered")
colombia = pytz.timezone("America/Bogota")

client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_hitos = db["hitos"]
coleccion_visual = db["log_visual"]

openai_client = OpenAI(api_key=st.secrets["openai_api_key"])

evento_a = "La Iniciativa Aquella"
evento_b = "La Iniciativa de Pago"
eventos = {
    "🧠 Reflexión": "reflexion",
    "📑 Historial completo": "historial",
    "✊🏽": evento_a,
    "💸": evento_b,
}

dias_semana = {
    0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue",
    4: "Vie", 5: "Sáb", 6: "Dom"
}

sistema_categorial = {
    # Igual que antes
}

for key in [evento_a, evento_b]:
    if key not in st.session_state:
        evento = coleccion_eventos.find_one({"evento": key}, sort=[("fecha_hora", -1)])
        if evento:
            st.session_state[key] = evento["fecha_hora"].astimezone(colombia)

def clasificar_reflexion_openai(texto_reflexion: str) -> str:
    prompt = f"""Sistema categorial para clasificar reflexiones:
    ..."""  # Igual que antes
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5,
    )
    return response.choices[0].message.content.strip()

def guardar_reflexion(fecha_hora, emociones, reflexion):
    categoria_auto = clasificar_reflexion_openai(reflexion)
    doc = {
        "fecha_hora": fecha_hora,
        "emociones": [{"emoji": e.split()[0], "nombre": " ".join(e.split()[1:])} for e in emociones],
        "reflexion": reflexion.strip(),
        "categoria_categorial": categoria_auto if categoria_auto else ""
    }
    coleccion_reflexiones.insert_one(doc)
    return categoria_auto

def registrar_evento(nombre_evento, fecha_hora):
    coleccion_eventos.insert_one({"evento": nombre_evento, "fecha_hora": fecha_hora})
    st.session_state[nombre_evento] = fecha_hora

def validar_y_registrar_hitos():
    registros = list(coleccion_eventos.find({"evento": evento_a}).sort("fecha_hora", 1))
    hitos_existentes = list(coleccion_hitos.find({"evento": evento_a}))
    hitos_actuales = {hito.get("desde"): hito.get("hito") for hito in hitos_existentes}
    hitos_agregados = False
    for i in range(1, len(registros)):
        inicio = registros[i-1]["fecha_hora"]
        fin = registros[i]["fecha_hora"]
        dias = (fin - inicio).days
        nuevo_hito = f"{dias} días"
        if inicio not in hitos_actuales or hitos_actuales.get(inicio) != nuevo_hito:
            coleccion_hitos.replace_one(
                {"evento": evento_a, "desde": inicio},
                {"evento": evento_a, "hito": nuevo_hito, "desde": inicio, "fecha_registro": fin},
                upsert=True
            )
            hitos_agregados = True
    if hitos_agregados:
        st.experimental_rerun()

def mostrar_racha(nombre_evento, emoji):
    clave_estado = f"mostrar_racha_{nombre_evento}"
    if clave_estado not in st.session_state:
        st.session_state[clave_estado] = False
    mostrar = st.checkbox("Ver/ocultar racha", value=st.session_state[clave_estado], key=f"check_{nombre_evento}")
    st.session_state[clave_estado] = mostrar
    st.markdown("### ⏱️ Racha")
    if nombre_evento in st.session_state:
        st_autorefresh(interval=1000, limit=None, key=f"auto_{nombre_evento}")
        ultimo = st.session_state[nombre_evento]
        ahora = datetime.now(colombia)
        delta = ahora - ultimo
        detalle = relativedelta(ahora, ultimo)
        minutos = int(delta.total_seconds() // 60)
        tiempo = f"{detalle.years}a {detalle.months}m {detalle.days}d {detalle.hours}h {detalle.minutes}m {detalle.seconds}s"
        if mostrar:
            st.metric("Duración", f"{minutos:,} min", tiempo)
            st.caption(f"🔴 Última recaída: {ultimo.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.metric("Duración", "•••••• min", "••a ••m ••d ••h ••m ••s")
            st.caption("🔒 Información sensible oculta. Activá la casilla para visualizar.")
    else:
        st.metric("Duración", "0 min")
        st.caption("0a 0m 0d 0h 0m 0s")

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        dia_sem = dias_semana[fecha.weekday()]
        anterior = eventos[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos) else None
        diferencia = ""
        if anterior:
            detalle = relativedelta(fecha, anterior)
            partes = []
            if detalle.years:
                partes.append(f"{detalle.years}a")
            if detalle.months:
                partes.append(f"{detalle.months}m")
            if detalle.days:
                partes.append(f"{detalle.days}d")
            if detalle.hours:
                partes.append(f"{detalle.hours}h")
            if detalle.minutes:
                partes.append(f"{detalle.minutes}m")
            diferencia = " ".join(partes)
        filas.append({
            "Día": dia_sem,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Sin recaída": diferencia
        })
    return pd.DataFrame(filas)

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
        emojis = " ".join([e["emoji"] for e in d.get("emociones", [])])
        emociones = ", ".join([e["nombre"] for e in d.get("emociones", [])])
        codigo_cat = d.get("categoria_categorial", "")
        info_cat = sistema_categorial.get(codigo_cat, {
            "categoria": "Sin categoría",
            "subcategoria": "",
            "descriptor": "",
            "observable": ""
        })
        rows.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Emojis": emojis,
            "Emociones": emociones,
            "Categoría": info_cat["categoria"],
            "Subcategoría": info_cat["subcategoria"],
            "Descriptor": info_cat.get("descriptor", ""),
            "Observable": info_cat.get("observable", ""),
            "Reflexión": d.get("reflexion", "")
        })
    return pd.DataFrame(rows)

def obtener_hitos():
    docs = list(coleccion_hitos.find({}).sort("fecha_registro", 1))
    filas = []
    for d in docs:
        fecha_inicio = d.get("desde")
        fecha_registro = d.get("fecha_registro")
        hito = d.get("hito", "")
        if fecha_inicio:
            fecha_inicio = fecha_inicio.astimezone(colombia)
        if fecha_registro:
            fecha_registro = fecha_registro.astimezone(colombia)
        filas.append({
            "Inicio": fecha_inicio.strftime("%Y-%m-%d %H:%M") if fecha_inicio else "",
            "Registro": fecha_registro.strftime("%Y-%m-%d %H:%M") if fecha_registro else "",
            "Hito": hito
        })
    return pd.DataFrame(filas)

def mostrar_tabla_eventos(nombre_evento):
    st.subheader(f"📍 Registros")
    mostrar = st.checkbox("Ver/Ocultar registros", value=False, key=f"mostrar_{nombre_evento}")
    df = obtener_registros(nombre_evento)
    if mostrar:
        st.dataframe(df.style.hide(axis="index"), use_container_width=True)
    else:
        df_oculto = df.copy()
        df_oculto["Día"] = "•••"
        df_oculto["Fecha"] = "••••-••-••"
        df_oculto["Hora"] = "••:••"
        df_oculto["Sin recaída"] = "••a ••m ••d ••h ••m"
        st.dataframe(df_oculto.style.hide(axis="index"), use_container_width=True)
        st.caption("🔒 Registros ocultos. Activá la casilla para visualizar.")

def mostrar_tabla_hitos():
    st.subheader("📍 Historial de hitos")
    mostrar = st.checkbox("Ver/Ocultar hitos", value=False, key="mostrar_hitos")
    df_hitos = obtener_hitos().reset_index(drop=True)
    if mostrar:
        st.dataframe(df_hitos.style.hide(axis="index"), use_container_width=True)
    else:
        df_oculto = df_hitos.copy()
        df_oculto["Inicio"] = "••••-••-•• ••:••"
        df_oculto["Registro"] = "••••-••-•• ••:••"
        df_oculto["Hito"] = "•••"
        st.dataframe(df_oculto.style.hide(axis="index"), use_container_width=True)
        st.caption("🔒 Hitos ocultos. Activá la casilla para visualizar")

st.title("Reinicia")
seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

if opcion != "reflexion":
    for key in ["texto_reflexion", "emociones_reflexion", "reset_reflexion"]:
        if key in st.session_state:
            del st.session_state[key]

if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento")
    fecha_hora_evento = datetime.now(colombia)

    if st.button("☠️ ¿Registrar?"):
        registrar_evento(opcion, fecha_hora_evento)
        validar_y_registrar_hitos()
        st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")
        st.rerun()

    mostrar_racha(opcion, seleccion.split()[0])

elif opcion == "reflexion":
    st.header("🧠 Registrar reflexión")

    if st.session_state.get("reset_reflexion", False):
        st.session_state["texto_reflexion"] = ""
        st.session_state["emociones_reflexion"] = []
        st.session_state["reset_reflexion"] = False
        st.rerun()

    ultima = coleccion_reflexiones.find_one({}, sort=[("fecha_hora", -1)])
    if ultima:
        fecha = ultima["fecha_hora"].astimezone(colombia)
        st.caption(f"📌 Última registrada: {fecha.strftime('%Y-%m-%d %H:%M:%S')}")

    fecha_hora_reflexion = datetime.now(colombia)

    emociones_opciones = [
        "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
        "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
    ]

    emociones = st.multiselect(
        "¿Cómo te sentías?",
        emociones_opciones,
        key="emociones_reflexion",
        placeholder="Seleccioná una o varias emociones"
    )
    texto_reflexion = st.text_area("¿Querés dejar algo escrito?", height=150, key="texto_reflexion")

    puede_guardar = texto_reflexion.strip() or emociones

    if puede_guardar:
        if st.button("📝 Guardar reflexión"):
            categoria_asignada = guardar_reflexion(fecha_hora_reflexion, emociones, texto_reflexion)
            st.success(f"Reflexión guardada con categoría: {categoria_asignada}")
            st.session_state["reset_reflexion"] = True
            st.rerun()

elif opcion == "historial":
    st.header("📑 Historial completo")
    tabs = st.tabs(["🧠 Reflexiones", "✊🏽", "💸"])

    with tabs[0]:
        st.subheader("📍 Historial de reflexiones")
        df_r = obtener_reflexiones()
        for i, row in df_r.iterrows():
            with st.expander(f"{row['Fecha']} {row['Emojis']} {row['Hora']}"):
                st.write(row['Reflexión'])
                st.markdown("---")
                st.write(f"**Estados de ánimo:** {row['Emociones']}")
                st.markdown(f"**Categoría:** {row['Categoría']}")
                st.markdown(f"**Subcategoría:** {row['Subcategoría']}")
                if row['Descriptor']:
                    st.markdown(f"**Descriptor:** {row['Descriptor']}")
                if row['Observable']:
                    st.markdown(f"**Observable:** {row['Observable']}")

    with tabs[1]:
        mostrar_tabla_eventos(evento_a)

        st.markdown("---")
        mostrar_tabla_hitos()

    with tabs[2]:
        mostrar_tabla_eventos(evento_b)
