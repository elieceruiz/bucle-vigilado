import streamlit as st
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
import pytz

# Timezone configuration
colombia = pytz.timezone("America/Bogota")

# MongoDB connection
client = MongoClient(st.secrets["mongo_uri"])
db = client["registro_bucle"]
coleccion = db["eventos"]

# Title of the new tab
st.subheader("🧠 Reflexiones completas y análisis")

# Function to load reflections with text
def traer_solo_reflexiones():
    eventos = list(coleccion.find({"reflexion": {"$exists": True, "$ne": ""}}).sort("fecha_hora", -1))
    filas = []
    for i, e in enumerate(eventos):
        fecha_hora = e["fecha_hora"].astimezone(colombia)
        emociones = ", ".join([f'{emo["emoji"]} {emo["nombre"]}' for emo in e.get("emociones", [])])
        reflexion = e.get("reflexion", "")
        palabras = len(reflexion.strip().split())
        filas.append({
            "N°": len(eventos) - i,
            "Evento": e["evento"],
            "Fecha": fecha_hora.date(),
            "Hora": fecha_hora.strftime("%H:%M"),
            "Emociones": emociones,
            "Reflexión completa": reflexion,
            "Palabras": palabras
        })
    return pd.DataFrame(filas)

# Load reflections with content
df_reflexiones = traer_solo_reflexiones()

# Show total stats above
total_reflexiones = len(df_reflexiones)
total_palabras = df_reflexiones["Palabras"].sum()
st.caption(f"📌 Registros con reflexión: {total_reflexiones} | ✍️ Palabras totales: {total_palabras}")

# Filter by emotion
emociones_unicas = sorted(set(e for sublist in df_reflexiones["Emociones"].str.split(", ") for e in sublist if e))
emocion_filtrada = st.selectbox("🔍 Filtrar por emoción (opcional)", ["Todas"] + emociones_unicas)

if emocion_filtrada != "Todas":
    df_filtrado = df_reflexiones[df_reflexiones["Emociones"].str.contains(emocion_filtrada)]
else:
    df_filtrado = df_reflexiones

# Show reflections in expanders
for _, row in df_filtrado.iterrows():
    with st.expander(f"{row['Fecha']} {row['Hora']} — {row['Evento']} — {row['Emociones']}"):
        st.write(row["Reflexión completa"])
        st.caption(f"📝 Palabras: {row['Palabras']}")

# Export as CSV
st.markdown("---")
csv = df_filtrado.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📄 Descargar reflexiones como CSV",
    data=csv,
    file_name="reflexiones_filtradas.csv",
    mime="text/csv"
)