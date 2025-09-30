import os, requests, streamlit as st
from datetime import datetime

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Chat + Turnos + Pago", layout="wide")
tab_chat, tab_res, tab_pago = st.tabs(["💬 Chat", "📅 Turnos", "💳 Pago"])

with tab_chat:
    st.title("Asistente (HF)")
    if "hist" not in st.session_state: st.session_state.hist=[]
    for r,t in st.session_state.hist: st.chat_message(r).markdown(t)
    m = st.chat_input("Escribí tu mensaje...")
    if m:
        st.session_state.hist.append(("user", m))
        r = requests.post(f"{BACKEND}/chat", json={"message": m}, timeout=60).json()
        ans = r.get("answer","(sin respuesta)")
        st.session_state.hist.append(("assistant", ans))
        st.chat_message("assistant").markdown(ans)

with tab_res:
    st.title("Disponibilidad (Cal.com)")
    days = st.slider("Días a mostrar", 1, 14, 7)
    sl = requests.get(f"{BACKEND}/slots", params={"days": days}, timeout=30).json()
    # Cal.com v2/slots devuelve slots agrupados; aplanamos rápido:
    flat=[]
    for day,slots in sl.get("slots", {}).items():
        for s in slots:
            flat.append({"start": s["start"], "end": s["end"]})
    if flat:
        choice = st.selectbox("Elegí un slot", [f'{i["start"]} → {i["end"]}' for i in flat])
        email = st.text_input("Email")
        nombre = st.text_input("Nombre", value="")
        if st.button("Reservar"):
            start, end = choice.split(" → ")
            b = {
                "start": start, "end": end,
                "email": email, "name": nombre or email
            }
            r = requests.post(f"{BACKEND}/book", json=b, timeout=30).json()
            st.success(r)

with tab_pago:
    st.title("Crear link de pago (MP)")
    booking_id = st.text_input("Booking ID")
    title = st.text_input("Concepto", "Reserva")
    amount = st.number_input("Monto (ARS)", min_value=0.0, value=20000.0, step=1000.0)
    if st.button("Generar link"):
        r = requests.post(f"{BACKEND}/pay/create",
                          json={"booking_id": booking_id, "title": title, "amount": amount, "currency": "ARS"},
                          timeout=30).json()
        if r.get("ok"):
            st.success("Checkout creado")
            st.markdown(f"[Pagar ahora]({r['checkout_url']})")
        else:
            st.error(r)
