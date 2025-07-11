
BucleVigilado
Seleccioná qué registrar o consultar:

🧠 Reflexión
🧠 Registrar reflexión
📌 Última registrada: 2025-07-11 14:52:57

¿Cómo te sentías?

💪 Firme / Decidido
¿Querés dejar algo escrito?

Casi que no queda funcional. Es probar y corregir errores, pero vale cadas segundo invertido. 

🧠 Reflexión guardada a las 15:25:02

👇 Última reflexión registrada:

Casi que no queda funcional. Es probar y corregir errores, pero vale cadas segundo invertido.

streamlit.errors.StreamlitAPIException: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).

Traceback:
File "/mount/src/bucle-vigilado/app.py", line 151, in <module>
    st.session_state.texto_reflexion = ""
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/metrics_util.py", line 443, in wrapped_func
    result = non_optional_func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/state/session_state_proxy.py", line 136, in __setattr__
    self[key] = value
    ~~~~^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/metrics_util.py", line 443, in wrapped_func
    result = non_optional_func(*args, **kwargs)
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/state/session_state_proxy.py", line 114, in __setitem__
    get_session_state()[key] = value
    ~~~~~~~~~~~~~~~~~~~^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/state/safe_session_state.py", line 101, in __setitem__
    self._state[key] = value
    ~~~~~~~~~~~^^^^^
File "/home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/state/session_state.py", line 527, in __setitem__
    raise StreamlitAPIException(
    ...<2 lines>...
    )