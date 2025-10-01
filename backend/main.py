from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from huggingface_hub import InferenceClient
from datetime import datetime, timedelta
import requests

app = FastAPI()

from backend.settings import (
    HF_ENDPOINT, HF_TOKEN, CAL_API_KEY, CAL_EVENT_TYPE_ID, CAL_USERNAME,
    CAL_EVENT_TYPE_SLUG, CAL_TZ, MP_TOKEN, PUBLIC_BASE
)

hf = InferenceClient(base_url=HF_ENDPOINT, token=HF_TOKEN)

class ChatIn(BaseModel):
    message: str

# ------------ LLM (chat orquestador) ------------
@app.post("/chat")
def chat(body: ChatIn):
    sys = ("Eres un asistente para reservas y pagos. "
           "Si el usuario pide horarios, usá la herramienta turnera; "
           "si confirma, reservá; si quiere pagar, generá link. "
           "Pedí confirmación antes de ejecutar acciones.")
    prompt = f"{sys}\nUsuario: {body.message}\nAsistente:"
    # respuesta simple; si querés LangChain, podes usar tools explícitas
    out = hf.text_generation(prompt, max_new_tokens=350, temperature=0.2)
    return {"answer": out}

# ------------ TURNERA (Cal.com v2) ------------
def _cal_headers():
    return {"Authorization": f"Bearer {CAL_API_KEY}", "cal-api-version": "2024-06-01"}

@app.get("/slots")
def get_slots(days: int = 7):
    start = datetime.utcnow().date().isoformat()
    end   = (datetime.utcnow().date() + timedelta(days=days)).isoformat()

    params = {"start": start, "end": end, "timeZone": CAL_TZ}
    if CAL_EVENT_TYPE_ID:
        params["eventTypeId"] = CAL_EVENT_TYPE_ID
    else:
        params["username"] = CAL_USERNAME
        params["eventTypeSlug"] = CAL_EVENT_TYPE_SLUG

    r = requests.get("https://api.cal.com/v2/slots", headers=_cal_headers(), params=params, timeout=30)
    if r.status_code >= 300:
        raise HTTPException(r.status_code, r.text)
    return r.json()

class BookIn(BaseModel):
    start: str  # ISO 8601 (ej. "2025-10-02T18:00:00")
    end:   str
    email: str
    name:  str | None = None
    language: str = "es"

@app.post("/book")
def book_slot(b: BookIn):
    payload = {
        "start": b.start,
        "end": b.end,
        "timeZone": CAL_TZ,
        "language": b.language,
        "attendees": [{"email": b.email, "name": b.name or b.email}],
        "metadata": {"source": "streamlit"}
    }
    
    # Manejo correcto de eventTypeId vs slug+username
    if CAL_EVENT_TYPE_ID:
        payload["eventTypeId"] = int(CAL_EVENT_TYPE_ID)
    else:
        payload["eventTypeSlug"] = CAL_EVENT_TYPE_SLUG
        payload["username"] = CAL_USERNAME

    r = requests.post("https://api.cal.com/v2/bookings", headers=_cal_headers(), json=payload, timeout=30)
    if r.status_code >= 300:
        raise HTTPException(r.status_code, r.text)
    return r.json()

# ------------ PAGOS (Mercado Pago Checkout Pro) ------------
class PayIn(BaseModel):
    booking_id: str
    title: str = "Reserva"
    amount: float = 20000.0
    currency: str = "ARS"

@app.post("/pay/create")
def pay_create(p: PayIn):
    if not MP_TOKEN:
        raise HTTPException(400, "Configura MP_ACCESS_TOKEN")
    pref = {
        "items": [{
            "title": p.title,
            "quantity": 1,
            "currency_id": p.currency.upper(),
            "unit_price": p.amount
        }],
        "metadata": {"booking_id": p.booking_id},
        "back_urls": {
            "success": f"{PUBLIC_BASE}/pay/success",
            "failure": f"{PUBLIC_BASE}/pay/failure",
            "pending": f"{PUBLIC_BASE}/pay/pending"
        },
        "auto_return": "approved",
        "notification_url": f"{PUBLIC_BASE}/pay/webhook"
    }
    r = requests.post("https://api.mercadopago.com/checkout/preferences",
                      json=pref, headers={"Authorization": f"Bearer {MP_TOKEN}"},
                      timeout=30)
    if r.status_code >= 300:
        raise HTTPException(r.status_code, r.text)
    data = r.json()
    return {"ok": True, "preference_id": data["id"], "checkout_url": data.get("init_point")}

@app.post("/pay/webhook")
async def pay_webhook(request: Request):
    body = await request.json()
    # Sugerido: leer 'type' y 'data.id' y consultar el pago para confirmar estado
    # Ej.: GET https://api.mercadopago.com/v1/payments/{id} con Bearer token
    # (implementar según tu flujo)
    return {"received": True}