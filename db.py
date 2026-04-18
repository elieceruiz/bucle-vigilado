from pymongo import MongoClient
import os

# intentar primero Streamlit (cloud)
try:
    import streamlit as st
    MONGO_URI = st.secrets["mongo_uri"]
except:
    # fallback local (.env)
    from dotenv import load_dotenv
    load_dotenv()
    MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("No se encontró MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["registro_bucle"]
coleccion_eventos = db["eventos"]
coleccion_capital_b = db["capitalizacion_b"]