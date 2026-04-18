import os
import streamlit as st
from pymongo import MongoClient

uri = st.secrets.get("mongo_uri") or os.getenv("MONGO_URI")

client = MongoClient(uri, serverSelectionTimeoutMS=5000)
client.admin.command("ping")

db = client["registro_bucle"]

coleccion_eventos = db["eventos"]
coleccion_reflexiones = db["reflexiones"]
coleccion_capital_b = db["capitalizacion_b"]