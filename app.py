import streamlit as st
from datetime import datetime, timedelta
from pymongo import MongoClient
import pytz
import pandas as pd
from dateutil.relativedelta import relativedelta
from streamlit_autorefresh import st_autorefresh
from openai import OpenAI

# Configuración
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

# Sistema categorial extendido con descriptores y observables
sistema_categorial = {
    "1.1": {
        "categoria": "Dinámicas cotidianas",
        "subcategoria": "Organización del tiempo",
        "descriptor": "Manejo de rutinas y distribución del día",
        "observable": "Relatos sobre horarios de trabajo, estudio, momentos de ocio, tiempo dedicado a la intimidad."
    },
    "1.2": {
        "categoria": "Dinámicas cotidianas",
        "subcategoria": "Relaciones sociales",
        "descriptor": "Interacciones que influyen en la vida íntima.",
        "observable": "Narraciones sobre pareja, amigos, familia; menciones de aprobación o desaprobación social."
    },
    "1.3": {
        "categoria": "Dinámicas cotidianas",
        "subcategoria": "Contextos de intimidad",
        "descriptor": "Espacios físicos y virtuales donde se desarrollan las prácticas.",
        "observable": "Lugares mencionados (casa, moteles, internet, calle), dispositivos usados, condiciones de privacidad."
    },
    "1.4": {
        "categoria": "Dinámicas cotidianas",
        "subcategoria": "Factores emocionales",
        "descriptor": "Estados afectivos vinculados al ejercicio de la sexualidad.",
        "observable": "Expresiones de soledad, ansiedad, deseo, satisfacción o culpa."
    },
    "2.1": {
        "categoria": "Consumo de sexo pago",
        "subcategoria": "Motivaciones",
        "descriptor": "Razones personales y sociales para pagar por sexo.",
        "observable": "Relatos de búsqueda de placer, compañía, evasión, curiosidad, necesidad de afecto."
    },
    "2.2": {
        "categoria": "Consumo de sexo pago",
        "subcategoria": "Prácticas asociadas",
        "descriptor": "Formas de acceder y realizar el consumo.",
        "observable": "Lugares (bares, calles, plataformas digitales), frecuencia, monto pagado, modalidades de encuentro."
    },
    "2.3": {
        "categoria": "Consumo de sexo pago",
        "subcategoria": "Representaciones",
        "descriptor": "Significados culturales y personales del sexo pago.",
        "observable": "Uso de términos como tabú, normal, peligroso, necesario, transgresión; narrativas de estigma o aceptación."
    },
    "2.4": {
        "categoria": "Consumo de sexo pago",
        "subcategoria": "Efectos en la trayectoria íntima",
        "descriptor": "Impacto en la experiencia personal y en la memoria íntima.",
        "observable": "Relatos de aprendizaje, arrepentimiento, culpa, gratificación, comparación con otras prácticas sexuales."
    },
    "3.1": {
        "categoria": "Masturbación",
        "subcategoria": "Prácticas de autocuidado",
        "descriptor": "Uso de la masturbación como estrategia de bienestar.",
        "observable": "Relatos sobre relajación, control del estrés, conciliación del sueño, cuidado de la salud sexual."
    },
    "3.2": {
        "categoria": "Masturbación",
        "subcategoria": "Placer y exploración del cuerpo",
        "descriptor": "Búsqueda de satisfacción personal y autoconocimiento.",
        "observable": "Narrativas sobre fantasías, técnicas usadas, experimentación, referencias a placer físico."
    },
    "3.3": {
        "categoria": "Masturbación",
        "subcategoria": "Relación con la intimidad",
        "descriptor": "Vínculo entre la masturbación y la privacidad del sujeto.",
        "observable": "Relatos de momentos en soledad, rituales íntimos, ocultamiento frente a otros."
    },
    "3.4": {
        "categoria": "Masturbación",
        "subcategoria": "Representaciones culturales",
        "descriptor": "Significados sociales y personales atribuidos a la masturbación.",
        "observable": "Expresiones de libertad, vergüenza, culpa, normalización; uso de términos religiosos o morales."
    }
}

def clasificar_reflexion_openai(texto_reflexion: str) -> str:
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

Por favor indica el código de la categoría/subcategoría que mejor describe esta reflexión:

Reflexión: \"\"\"{texto_reflexion}\"\"\"
Respuesta sólo con el código, ejemplo: 1.4
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5
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

def clasificar_reflexiones_pendientes():
    pendientes = list(coleccion_reflexiones.find({"categoria_categorial": {"$exists": False}}))
    if not pendientes:
        st.info("No hay reflexiones pendientes de clasificación.")
        return

    st.info(f"Procesando {len(pendientes)} reflexiones pendientes...")
    for doc in pendientes:
        _id = doc["_id"]
        texto = doc.get("reflexion", "").strip()
        if texto:
            try:
                cat = clasificar_reflexion_openai(texto)
                coleccion_reflexiones.update_one({"_id": _id}, {"$set": {"categoria_categorial": cat}})
                st.success(f"Reflexión {_id} categorizada como {cat}")
            except Exception as e:
                st.error(f"Error clasificando reflexión {_id}: {str(e)}")
        else:
            st.warning(f"Reflexión {_id} vacía, no clasificada.")

def obtener_registros(nombre_evento):
    eventos = list(coleccion_eventos.find({"evento": nombre_evento}).sort("fecha_hora", -1))
    filas = []
    total = len(eventos)
    for i, e in enumerate(eventos):
        fecha = e["fecha_hora"].astimezone(colombia)
        anterior = eventos[i + 1]["fecha_hora"].astimezone(colombia) if i + 1 < len(eventos) else None
        diferencia = ""
        if anterior:
            detalle = relativedelta(fecha, anterior)
            diferencia = f"{detalle.years}a {detalle.months}m {detalle.days}d {detalle.hours}h {detalle.minutes}m"
        filas.append({
            "N°": total - i,
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Hora": fecha.strftime("%H:%M"),
            "Duración sin caer": diferencia
        })
    return pd.DataFrame(filas)

def obtener_reflexiones():
    docs = list(coleccion_reflexiones.find({}).sort("fecha_hora", -1))
    rows = []
    for d in docs:
        fecha = d["fecha_hora"].astimezone(colombia)
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
            "Emociones": emociones,
            "Categoría": info_cat["categoria"],
            "Subcategoría": info_cat["subcategoria"],
            "Descriptor": info_cat.get("descriptor", ""),
            "Observable": info_cat.get("observable", ""),
            "Reflexión": d.get("reflexion", "")
        })
    return pd.DataFrame(rows)

# UI principal
st.title("Reinicia")
seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

if opcion != "reflexion":
    for key in ["texto_reflexion", "emociones_reflexion", "limpiar_reflexion", "📝 Guardar reflexión"]:
        st.session_state.pop(key, None)

if opcion in [evento_a, evento_b]:
    st.header(f"📍 Registro de evento: {seleccion}")
    fecha_hora_evento = datetime.now(colombia)
    if st.button("☠️ ¿Registrar?"):
        coleccion_eventos.insert_one({"evento": opcion, "fecha_hora": fecha_hora_evento})
        st.session_state[opcion] = fecha_hora_evento
        st.success(f"Evento '{seleccion}' registrado a las {fecha_hora_evento.strftime('%H:%M:%S')}")
    mostrar_racha(opcion, seleccion.split()[0])

elif opcion == "reflexion":
    st.header("🧠 Registrar reflexión")
    if "texto_reflexion" not in st.session_state:
        st.session_state["texto_reflexion"] = ""
    if "emociones_reflexion" not in st.session_state:
        st.session_state["emociones_reflexion"] = []
    if "limpiar_reflexion" not in st.session_state:
        st.session_state["limpiar_reflexion"] = False
    if st.session_state["limpiar_reflexion"]:
        st.session_state["texto_reflexion"] = ""
        st.session_state["emociones_reflexion"] = []
        st.session_state["limpiar_reflexion"] = False
    ultima = coleccion_reflexiones.find_one({}, sort=[("fecha_hora", -1)])
    if ultima:
        fecha = ultima["fecha_hora"].astimezone(colombia)
        st.caption(f"📌 Última registrada: {fecha.strftime('%Y-%m-%d %H:%M:%S')}")
    fecha_hora_reflexion = datetime.now(colombia)
    emociones_opciones = [
        "😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido",
        "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"
    ]
    emociones = st.multiselect("¿Cómo te sentías?", emociones_opciones, key="emociones_reflexion")
    texto_reflexion = st.text_area("¿Querés dejar algo escrito?", height=150, key="texto_reflexion")
    puede_guardar = texto_reflexion.strip() or emociones
    if puede_guardar:
        if st.button("📝 Guardar reflexión"):
            categoria_asignada = guardar_reflexion(fecha_hora_reflexion, emociones, texto_reflexion)
            st.success(f"Reflexión guardada con categoría: {categoria_asignada}")
            st.session_state["limpiar_reflexion"] = True
    st.markdown("<div style='margin-bottom: 300px;'></div>", unsafe_allow_html=True)

elif opcion == "historial":
    st.header("📑 Historial completo")
    tabs = st.tabs(["🧠 Reflexiones", "✊🏽", "💸"])
    with tabs[0]:
        st.subheader("📍 Historial de reflexiones")
        df_r = obtener_reflexiones()
        for i, row in df_r.iterrows():
            with st.expander(f"{row['Fecha']} {row['Hora']} - {row['Categoría']} / {row['Subcategoría']}"):
                st.write(f"**Emociones:** {row['Emociones']}")
                st.write(f"**Reflexión:** {row['Reflexión']}")
                if row['Descriptor']:
                    st.markdown(f"**Descriptor:** {row['Descriptor']}")
                if row['Observable']:
                    st.markdown(f"**Observable:** {row['Observable']}")
        if st.button("Clasificar todas las reflexiones pendientes"):
            clasificar_reflexiones_pendientes()
    def mostrar_tabla_eventos(nombre_evento):
        st.subheader(f"📍 Registros de {nombre_evento}")
        mostrar = st.checkbox("Ver/Ocultar registros", value=False, key=f"mostrar_{nombre_evento}")
        df = obtener_registros(nombre_evento)
        if mostrar:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            df_oculto = df.copy()
            df_oculto["Fecha"] = "••••-••-••"
            df_oculto["Hora"] = "••:••"
            df_oculto["Duración sin caer"] = "••a ••m ••d ••h ••m"
            st.dataframe(df_oculto, use_container_width=True, hide_index=True)
            st.caption("🔒 Registros ocultos. Activá el check para visualizar.")
    with tabs[1]:
        mostrar_tabla_eventos(evento_a)
    with tabs[2]:
        mostrar_tabla_eventos(evento_b)
