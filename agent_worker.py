import os
import json
import time
import requests
import pandas as pd
import numpy as np
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
from agentsouk import AgentSouk
from agents_u_cash import AgentsUCash

AGENTSOUK_API_KEY = os.environ["AGENTSOUK_API_KEY"]
UCASH_API_KEY = os.environ["UCASH_API_KEY"]
STATE_FILE = "pending_jobs.json"

# NUEVOS PRECIOS
PRICES = {
    "translation": 0.40, 
    "data_analysis": 1.00, 
    "web_scraping": 0.50,
    "default": 2.00
}

# TEXTO PROMOCIONAL
PROMO_TEXT = "\n\n---\n🤖 *Powered by Cuban Freedom Tech.*\nCheck out my other AI services on Agentsouk!\n👉 https://github.com/alfrexo95"

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
    except:
        return f"[Error de traducción] {texto}"

def analizar_datos_y_senales():
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
        y = df["close"].values[-5:]
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        prediccion = slope * len(y) + intercept
        señal = "MANTENER"
        if c < sma and rsi < 40 and prediccion > c: señal = "COMPRA 🟢"
        elif c > sma and rsi > 60 and prediccion < c: señal = "VENTA 🔴"
        return f"📊 **Análisis BTC**\n- Precio: ${c:.2f}\n- SMA: ${sma:.2f}\n- RSI: {rsi:.2f}\n- Predicción: ${prediccion:.2f}\n- **Señal: {señal}**"
    except Exception as e:
        return f"Error: {e}"

def scrape_web(url):
    """Extrae el texto de una URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Eliminar scripts y estilos
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator=' ')
        # Limpiar espacios en blanco
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text[:2000] # Devolver solo los primeros 2000 caracteres para no saturar
    except Exception as e:
        return f"Error extrayendo texto: {e}"

def procesar_trabajo(job_type, input_data):
    result = {}
    if job_type == "translation":
        result["translation"] = traducir_texto(input_data.get("text", ""))
    elif job_type == "data_analysis":
        result["analysis"] = analizar_datos_y_senales()
    elif job_type == "web_scraping":
        result["scraped_text"] = scrape_web(input_data.get("url", ""))
    else:
        result["error"] = "No soportado"
    
    # Añadir el texto promocional al final del resultado
    result["promo"] = PROMO_TEXT
    return result

def revisar_inbox_y_pagos(state):
    # 1. Revisar Inbox
    try:
        inbox = aw.inbox()
        for job in inbox.get("jobs", []):
            job_id = job["id"]
            if job_id in state: continue

            title = job.get("listing_title", "").lower()
            if "traducción" in title or "translation" in title:
                job_type = "translation"
            elif "análisis" in title or "analysis" in title:
                job_type = "data_analysis"
            elif "scraping" in title or "extracción" in title:
                job_type = "web_scraping"
            else:
                job_type = "default"
                
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
        if isinstance(settlements, dict): settlements = settlements.get("data", settlements.get("settlements", []))
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
    print("🚀 Bot encendido (Modo Multi-Servicio + Promoción)...")
    start_time = time.time()
    AWAKE_TIME = 15 * 60
    CHECK_INTERVAL = 60
    
    while time.time() - start_time < AWAKE_TIME:
        print(f"\n⏰ Revisando a las {time.strftime('%H:%M:%S')}...")
        state = load_state()
        revisar_inbox_y_pagos(state)
        time.sleep(CHECK_INTERVAL)
        
    print("\n🛑 Ventana de trabajo terminada.")

if __name__ == "__main__":
    main()
