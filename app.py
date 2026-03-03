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

dias_semana_3letras = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}

# =========================
# BASE DE DATOS
# =========================
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]

# =========================
# CAPITALIZACIÓN EVENTO B
# =========================
coleccion_capital_b = db["capitalizacion_b"]

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
    "🧭 Viaje en el tiempo": "viaje_tiempo",
}

# =========================
# SISTEMA CATEGORIAL
# =========================
sistema_categorial = {
    "1.1": {"categoria": "Dinámicas cotidianas", "subcategoria": "Organización del tiempo",
            "descriptor": "Manejo de rutinas y distribución del día",
            "observable": "Relatos sobre horarios de trabajo, estudio, momentos de ocio, tiempo dedicado a la intimidad."},
    "1.2": {"categoria": "Dinámicas cotidianas", "subcategoria": "Relaciones sociales",
            "descriptor": "Interacciones que influyen en la vida íntima.",
            "observable": "Narraciones sobre pareja, amigos, familia; menciones de aprobación o desaprobación social."},
    "1.3": {"categoria": "Dinámicas cotidianas", "subcategoria": "Contextos de intimidad",
            "descriptor": "Espacios físicos y virtuales donde se desarrollan las prácticas.",
            "observable": "Lugares mencionados (casa, moteles, internet, calle), dispositivos usados, condiciones de privacidad."},
    "1.4": {"categoria": "Dinámicas cotidianas", "subcategoria": "Factores emocionales",
            "descriptor": "Estados afectivos vinculados al ejercicio de la sexualidad.",
            "observable": "Expresiones de soledad, ansiedad, deseo, satisfacción o culpa."},
    "2.1": {"categoria": "Consumo de sexo pago", "subcategoria": "Motivaciones",
            "descriptor": "Razones personales y sociales para pagar por sexo.",
            "observable": "Relatos de búsqueda de placer, compañía, evasión, curiosidad, necesidad de afecto."},
    "2.2": {"categoria": "Consumo de sexo pago", "subcategoria": "Prácticas asociadas",
            "descriptor": "Formas de acceder y realizar el consumo.",
            "observable": "Lugares (bares, calles, plataformas digitales), frecuencia, monto pagado, modalidades de encuentro."},
    "2.3": {"categoria": "Consumo de sexo pago", "subcategoria": "Representaciones",
            "descriptor": "Significados culturales y personales del sexo pago.",
            "observable": "Uso de términos como tabú, normal, peligroso, necesario, transgresión; narrativas de estigma o aceptación."},
    "2.4": {"categoria": "Consumo de sexo pago", "subcategoria": "Efectos en la trayectoria íntima",
            "descriptor": "Impacto en la experiencia personal y en la memoria íntima.",
            "observable": "Relatos de aprendizaje, arrepentimiento, culpa, gratificación, comparación con otras prácticas sexuales."},
    "3.1": {"categoria": "Masturbación", "subcategoria": "Prácticas de autocuidado",
            "descriptor": "Uso de la masturbación como estrategia de bienestar.",
            "observable": "Relatos sobre relajación, control del estrés, conciliación del sueño, cuidado de la salud sexual."},
    "3.2": {"categoria": "Masturbación", "subcategoria": "Placer y exploración del cuerpo",
            "descriptor": "Búsqueda de satisfacción personal y autoconocimiento.",
            "observable": "Narrativas sobre fantasías, técnicas usadas, experimentación, referencias a placer físico."},
    "3.3": {"categoria": "Masturbación", "subcategoria": "Relación con la intimidad",
            "descriptor": "Vínculo entre la masturbación y la privacidad del sujeto.",
            "observable": "Relatos de momentos en soledad, rituales íntimos, ocultamiento frente a otros."},
    "3.4": {"categoria": "Masturbación", "subcategoria": "Representaciones culturales",
            "descriptor": "Significados sociales y personales atribuidos a la masturbación.",
            "observable": "Expresiones de libertad, vergüenza, culpa, normalización; uso de términos religiosos o morales."},
}

# =========================
# CARGA ESTADO INICIAL
# =========================
for ev in [EVENTO_A, EVENTO_B]:
    if ev not in st.session_state:
        ultimo = coleccion_eventos.find_one({"evento": ev}, sort=[("fecha_hora", -1)])
        if ultimo:
            st.session_state[ev] = ultimo["fecha_hora"].astimezone(colombia)

# =========================
# FUNCIONES AUXILIARES
# =========================
def formatear_delta(rd, incluir_segundos=False):
    partes = []
    if rd.years:
        partes.append(f"{rd.years}a")
    if rd.months:
        partes.append(f"{rd.months}m")
    if rd.days:
        partes.append(f"{rd.days}d")
    if rd.hours:
        partes.append(f"{rd.hours}h")
    if rd.minutes:
        partes.append(f"{rd.minutes}m")
    if incluir_segundos and rd.seconds:
        partes.append(f"{rd.seconds}s")
    return " ".join(partes) if partes else "0m"

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

Por favor indicá solo el código que aplica.

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
    st.session_state[nombre] = fecha
    st.rerun()

# =========================
# REGISTROS
# =========================
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
            "Sin recaída": diff
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
            "categoria":"Sin categoría","subcategoria":"","descriptor":"","observable":""
        })
        filas.append({
            "Fecha": fecha.strftime("%d-%m-%y"),
            "Hora": fecha.strftime("%H:%M"),
            "Reflexión": r.get("reflexion",""),
            "Categoría": cat_info["categoria"],
            "Subcategoría": cat_info["subcategoria"],
            "Descriptor": cat_info.get("descriptor",""),
            "Observable": cat_info.get("observable",""),
            "Emociones": " ".join([e["emoji"] for e in r.get("emociones", [])])
        })
    return pd.DataFrame(filas)

# =========================
# CRONÓMETRO / RACHA
# =========================
def mostrar_racha(nombre_evento, emoji):
    estado = f"cronometro_activo_{nombre_evento}"
    if estado not in st.session_state:
        st.session_state[estado] = False

    st.markdown("### ⏱️ Racha")
    cambiar_estado = st.checkbox("Cronómetro activo", value=st.session_state[estado], key=f"chk_{nombre_evento}")
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

    st.metric("Duración", f"{int(delta.total_seconds()//60)} min", formatear_delta(rd, incluir_segundos=True))

# =========================
# VIAJE EN EL TIEMPO - EVENTO B
# =========================
from datetime import timedelta

def parsear_y_formatear_cop(valor_str):
    limpio = "".join(filter(str.isdigit, valor_str))
    if not limpio:
        return 0.00, "0,00"
    valor = int(limpio) / 100
    formateado = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return valor, formateado

def obtener_minutos_evento_b():
    if EVENTO_B not in st.session_state:
        return 0
    inicio = st.session_state[EVENTO_B]
    ahora = datetime.now(colombia)
    return int((ahora - inicio).total_seconds() // 60)

def obtener_historial_capital_b():
    registros = list(coleccion_capital_b.find().sort("fecha_registro", -1))
    filas = []

    for r in registros:
        fecha_reg = r["fecha_registro"].astimezone(colombia)
        fecha_fut = r["fecha_futura"].astimezone(colombia)

        filas.append({
            "Actual": fecha_reg.strftime("%d-%m-%y %H:%M"),
            "Adelantado": fecha_fut.strftime("%d-%m-%y %H:%M"),
            "COP": f"{r['monto']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        })

    return pd.DataFrame(filas)

# =========================
# INTERFAZ PRINCIPAL
# =========================
st.title("Reinicia")

seleccion = st.selectbox("Seleccioná qué registrar o consultar:", list(eventos.keys()))
opcion = eventos[seleccion]

# ==== EVENTOS ====
if opcion in [EVENTO_A, EVENTO_B]:
    if st.button("☠️ Registrar evento"):
        registrar_evento(opcion, datetime.now(colombia))
    mostrar_racha(opcion, seleccion)

# ==== VIAJE EN EL TIEMPO ====
elif opcion == "viaje_tiempo":

    st.subheader("🧭 Viaje en el tiempo")
    
    # Mostrar confirmación si existe
    if "mensaje_guardado" in st.session_state:
        msg = st.session_state["mensaje_guardado"]
    
        st.success(
            f"✔ Capital registrado: {msg['capital']} COP\n\n"
            f"🕒 Viajas hasta: {msg['fecha_futura']}"
        )
    
        del st.session_state["mensaje_guardado"]

    # =========================
    # INPUT TIPO NU (con on_change)
    # =========================
    def formatear_input_nu():
        raw = st.session_state.get("input_nu", "")
        limpio = "".join(filter(str.isdigit, raw))

        if limpio:
            numero = int(limpio)
            monto_tmp = numero / 100
            formateado = (
                f"{monto_tmp:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            st.session_state["input_nu"] = formateado
        else:
            st.session_state["input_nu"] = ""

    st.text_input(
        "Monto actual en NU (COP)",
        key="input_nu",
        on_change=formatear_input_nu
    )

    raw_final = st.session_state.get("input_nu", "")
    limpio_final = "".join(filter(str.isdigit, raw_final))

    if limpio_final:
        monto = int(limpio_final) / 100
        monto_formateado = raw_final
    else:
        monto = 0.0
        monto_formateado = "0,00"

    
    if monto > 0:
        minutos_actuales = obtener_minutos_evento_b()
        diferencia = int(monto - minutos_actuales)
        ahora = datetime.now(colombia)

        if diferencia > 0:
            fecha_futura = ahora + timedelta(minutes=diferencia)

            st.success("Adelanto detectado")
            st.markdown(f"**Capital:** {monto_formateado} COP")
            st.markdown(f"**Fecha equivalente futura:** {fecha_futura.strftime('%d-%m-%y %H:%M')}")
        else:
            fecha_futura = ahora
            st.info("Sin adelanto aún")

            if st.button("Guardar estado"):
            
                coleccion_capital_b.insert_one({
                    "fecha_registro": ahora,
                    "fecha_futura": fecha_futura,
                    "monto": monto
                })
            
                # Guardamos mensaje en estado
                st.session_state["mensaje_guardado"] = {
                    "capital": monto_formateado,
                    "fecha_futura": fecha_futura.strftime("%d-%m-%y %H:%M")
                }
            
                # Limpiamos el input
                st.session_state["input_nu"] = ""
            
                st.rerun()

# ==== REFLEXIONES ====
elif opcion == "reflexion":
    # 🔹 Limpieza segura de session_state
    if st.session_state.get("limpiar_reflexion", False):
        st.session_state["texto_reflexion"] = ""
        st.session_state["emociones_reflexion"] = []
        st.session_state["limpiar_reflexion"] = False

    emociones = st.multiselect(
        "¿Cómo te sentías?",
        ["😰 Ansioso", "😡 Irritado / Rabia contenida", "💪 Firme / Decidido", 
         "😌 Aliviado / Tranquilo", "😓 Culpable", "🥱 Apático / Cansado", "😔 Triste"],
        key="emociones_reflexion"
    )
    texto = st.text_area("¿Querés dejar algo escrito?", key="texto_reflexion")

    if (texto.strip() or emociones) and st.button("📝 Guardar reflexión"):
        categoria = guardar_reflexion(datetime.now(colombia), emociones, texto)
        info_cat = sistema_categorial.get(categoria, {"categoria":"Sin categoría","subcategoria":"","descriptor":"","observable":""})

        st.markdown("### ✅ Reflexión guardada")
        st.markdown(f"**Reflexión:** {texto.strip()}")
        st.markdown(f"**Categoría:** {info_cat['categoria']}")
        st.markdown(f"**Subcategoría:** {info_cat['subcategoria']}")
        if info_cat.get("descriptor"):
            st.markdown(f"**Descriptor:** {info_cat['descriptor']}")
        if info_cat.get("observable"):
            st.markdown(f"**Observable:** {info_cat['observable']}")

        st.session_state["limpiar_reflexion"] = True
        st.rerun()

# ==== HISTORIAL ====
elif opcion == "historial":
    tabs = st.tabs(["🧠 Reflexiones", "✊🏽 Evento A", "💸 Evento B", "🧭"])

    with tabs[0]:
        df = obtener_reflexiones()
        for _, r in df.iterrows():
            with st.expander(f"{r['Fecha']} {r['Hora']} {r['Emociones']}"):
                st.write(r["Reflexión"])
                st.markdown(f"**Categoría:** {r['Categoría']}")
                st.markdown(f"**Subcategoría:** {r['Subcategoría']}")
                if r["Descriptor"]:
                    st.markdown(f"**Descriptor:** {r['Descriptor']}")
                if r["Observable"]:
                    st.markdown(f"**Observable:** {r['Observable']}")

    with tabs[1]:
        st.dataframe(obtener_registros(EVENTO_A), use_container_width=True, hide_index=False)

    with tabs[2]:
        st.dataframe(obtener_registros(EVENTO_B), use_container_width=True, hide_index=False)
        
    with tabs[3]:
        df_cap = obtener_historial_capital_b()
        if not df_cap.empty:
            st.dataframe(df_cap, use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros aún")
        
