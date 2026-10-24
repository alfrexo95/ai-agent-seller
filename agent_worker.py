import os
import json
import time
import requests
import pandas as pd
import numpy as np
from deep_translator import GoogleTranslator
from agentsouk import AgentSouk
from agents_u_cash import AgentsUCash

AGENTSOUK_API_KEY = os.environ["AGENTSOUK_API_KEY"]
UCASH_API_KEY = os.environ["UCASH_API_KEY"]
STATE_FILE = "pending_jobs.json"
PRICES = {"translation": 0.40, "data_analysis": 1.00, "default": 2.00}

# Tiempo que el bot se queda despierto en cada ciclo (en segundos)
AWAKE_TIME = 10 * 60  # 10 minutos
CHECK_INTERVAL = 60   # Revisar cada 60 segundos

aw = AgentSouk(api_key=AGENTSOUK_API_KEY)
ucash = AgentsUCash(api_key=UCASH_API_KEY)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def traducir_texto(texto):
    try:
        return GoogleTranslator(source='auto', target='es').translate(texto)
    except Exception as e:
        return f"[Error de traducción] {texto}"

def analizar_datos_y_senales():
    """Análisis rápido con NumPy (sin TensorFlow)"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7"
        res = requests.get(url, timeout=15).json()
        prices = [p[1] for p in res["prices"]]
        
        df = pd.DataFrame(prices, columns=["close"])
        df["sma_3"] = df["close"].rolling(window=3).mean()
        
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=3).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=3).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        df = df.dropna()
        
        if len(df) < 5: return "Datos insuficientes."
            
        c = df["close"].iloc[-1]
        sma = df["sma_3"].iloc[-1]
        rsi = df["rsi"].iloc[-1]
        
        # Predicción rápida usando regresión lineal (NumPy)
        y = df["close"].values[-5:]
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        prediccion = slope * len(y) + intercept
        
        señal = "MANTENER"
        if c < sma and rsi < 40 and prediccion > c: señal = "COMPRA 🟢"
        elif c > sma and rsi > 60 and prediccion < c: señal = "VENTA 🔴"
            
        return f"""
📊 **Análisis BTC**
- Precio: ${c:.2f}
- SMA (3d): ${sma:.2f}
- RSI (3d): {rsi:.2f}
- Predicción NumPy: ${prediccion:.2f}
- **Señal: {señal}**"""
    except Exception as e:
        return f"Error: {e}"

def procesar_trabajo(job_type, input_data):
    if job_type == "translation":
        return {"translation": traducir_texto(input_data.get("text", ""))}
    elif job_type == "data_analysis":
        return {"analysis": analizar_datos_y_senales()}
    return {"error": "No soportado"}

def revisar_inbox_y_pagos(state):
    # 1. Revisar Inbox
    try:
        inbox = aw.inbox()
        for job in inbox.get("jobs", []):
            job_id = job["id"]
            if job_id in state: continue

            title = job.get("listing_title", "").lower()
            job_type = "translation" if "traducción" in title or "translation" in title else "data_analysis" if "análisis" in title else "default"
            price = PRICES.get(job_type, PRICES["default"])
            
            print(f"📥 Nuevo trabajo: {job_id} | Tipo: {job_type} | Precio: ${price:.2f}")
            res = ucash.create_resource(amount=price)
            payment_url = f"https://agents.u.cash/r/{res['res_id']}"
            
            aw.jobs.message(job_id, f"Por favor paga ${price:.2f} USD aquí: {payment_url}")
            state[job_id] = {"res_id": res['res_id'], "price": price, "job_type": job_type, "status": "pending_payment"}
            print(f"  ✅ Enlace enviado: {payment_url}")
    except Exception as e:
        print(f"❌ Error en Inbox: {e}")

    # 2. Revisar Pagos
    try:
        settlements = ucash.get_settlements()
        if isinstance(settlements, dict):
            settlements = settlements.get("data", settlements.get("settlements", []))
        if not isinstance(settlements, list): settlements = []

        for settlement in settlements:
            if isinstance(settlement, dict) and settlement.get("status") == "settled":
                for job_id, data in list(state.items()):
                    if data.get("res_id") == settlement.get("res_id") and data.get("status") == "pending_payment":
                        print(f"💰 Pago confirmado: {job_id}")
                        job_details = aw.jobs.get(job_id)
                        output = procesar_trabajo(data["job_type"], job_details.get("input", {}))
                        aw.jobs.deliver(job_id, output=output)
                        data["status"] = "paid"
                        print(f"  ✅ Trabajo entregado.")
    except Exception as e:
        print(f"⚠️ Error en pagos: {e}")

    save_state(state)

def main():
    print("🚀 Bot encendido. Iniciando ventana de trabajo continuo...")
    start_time = time.time()
    
    # Bucle de trabajo continuo: se mantiene despierto revisando cada 60 segundos
    while time.time() - start_time < AWAKE_TIME:
        print(f"\n⏰ Revisando a las {time.strftime('%H:%M:%S')}...")
        state = load_state()
        revisar_inbox_y_pagos(state)
        time.sleep(CHECK_INTERVAL)
        
    print("\n🛑 Ventana de trabajo terminada. El bot se apagará hasta el próximo ciclo.")

if __name__ == "__main__":
    main()
