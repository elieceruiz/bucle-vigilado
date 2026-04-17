# openai_client.py

from openai import OpenAI
import streamlit as st

openai_client = OpenAI(api_key=st.secrets["openai_api_key"])
