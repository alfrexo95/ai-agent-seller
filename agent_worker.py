import os
import json
import requests
import pandas as pd
import numpy as np
import tensorflow as tf
from deep_translator import GoogleTranslator
from agentsouk import AgentSouk
from agents_u_cash import AgentsUCash

# --- CONFIGURACIÓN ---
AGENTSOUK_API_KEY = os.environ["AGENTSOUK_API_KEY"]
UCASH_API_KEY = os.environ["UCASH_API_KEY"]
STATE_FILE = "pending_jobs.json"

# Definir los precios por tipo de servicio
PRICES = {
    "translation": 0.40,
    "data_analysis": 1.00,
    "default": 2.00
}

# Forzar CPU y limitar hilos para evitar OOM en GitHub Actions
tf.config.set_visible_devices([], 'GPU')
tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.threading.set_intra_op_parallelism_threads(1)

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
    """Traduce texto usando deep-translator (gratis, sin API Key)."""
    try:
        translated = GoogleTranslator(source='auto', target='es').translate(texto)
        return translated
    except Exception as e:
        print(f"  ⚠️ Error en traducción: {e}")
        return f"[Error de traducción] {texto}"

def analizar_datos_y_senales():
    """Obtiene datos de BTC, calcula indicadores y genera una señal con TensorFlow."""
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7"
        res = requests.get(url, timeout=15)
        data = res.json()
        prices = [p[1] for p in data["prices"]]
        
        df = pd.DataFrame(prices, columns=["close"])
        df["sma_3"] = df["close"].rolling(window=3).mean()
        
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=3).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=3).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))
        
        df = df.dropna()
        if len(df) < 5:
            return "Datos insuficientes para el análisis."
            
        ultimo_cierre = df["close"].iloc[-1]
        ultima_sma = df["sma_3"].iloc[-1]
        ultimo_rsi = df["rsi"].iloc[-1]
        
        X = df["close"].values[-5:].reshape(1, 5)
        y = df["close"].values[-1].reshape(1, 1)
        
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(8, activation='relu', input_shape=(5,)),
            tf.keras.layers.Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        model.fit(X, y, epochs=1, verbose=0)
        
        prediccion = model.predict(X, verbose=0)[0][0]
        
        señal = "MANTENER"
        if ultimo_cierre < ultima_sma and ultimo_rsi < 40 and prediccion > ultimo_cierre:
            señal = "COMPRA 🟢"
        elif ultimo_cierre > ultima_sma and ultimo_rsi > 60 and prediccion < ultimo_cierre:
            señal = "VENTA 🔴"
            
        return f"""
📊 **Análisis de Datos y Señales (BTC)**
- Precio actual: ${ultimo_cierre:.2f}
- SMA (3 días): ${ultima_sma:.2f}
- RSI (3 días): {ultimo_rsi:.2f}
- Predicción TensorFlow (próximo cierre): ${prediccion:.2f}
- **Señal: {señal}**
"""
    except Exception as e:
        return f"Error en el análisis: {e}"

def procesar_trabajo(job_type, input_data):
    if job_type == "translation":
        texto = input_data.get("text", "")
        traduccion = traducir_texto(texto)
        return {"translation": traduccion}
    elif job_type == "data_analysis":
        analisis = analizar_datos_y_senales()
        return {"analysis": analisis}
    else:
        return {"error": "Tipo de trabajo no soportado"}

def main():
    state = load_state()
    
    # 1. Revisar nuevos trabajos
    try:
        inbox = aw.inbox()
        jobs = inbox.get("jobs", [])
    except Exception as e:
        print(f"❌ Error obteniendo inbox: {e}")
        return

    for job in jobs:
        job_id = job["id"]
        if job_id in state:
            continue

        # Determinar el tipo de trabajo (basado en el título del listing)
        title = job.get("listing_title", "").lower()
        if "traducción" in title or "translation" in title:
            job_type = "translation"
        elif "análisis" in title or "analysis" in title:
            job_type = "data_analysis"
        else:
            job_type = "default"
            
        price = PRICES.get(job_type, PRICES["default"])
        
        print(f"📥 Nuevo trabajo: {job_id} | Tipo: {job_type} | Precio: ${price:.2f}")

        try:
            # Crear recurso de pago con el precio dinámico
            res = ucash.create_resource(amount=price)
            res_id = res["res_id"]
            payment_url = f"https://agents.u.cash/r/{res_id}"
            
            # Enviar enlace de pago
            aw.jobs.message(job_id, f"Por favor paga ${price:.2f} USD aquí: {payment_url}")
            
            state[job_id] = {
                "res_id": res_id,
                "price": price,
                "job_type": job_type,
                "payment_url": payment_url,
                "status": "pending_payment"
            }
            print(f"  ✅ Enlace de pago enviado: {payment_url}")
        except Exception as e:
            print(f"  ❌ Error generando pago: {e}")

    # 2. Revisar pagos completados y entregar
    try:
        settlements = ucash.get_settlements()
        
        # Asegurarnos de que sea una lista. Si la API devuelve un dict o un string, lo manejamos.
        if isinstance(settlements, dict):
            # A veces la API devuelve {'data': [...]} o {'settlements': [...]}
            settlements = settlements.get("data", settlements.get("settlements", []))
        
        if not isinstance(settlements, list):
            print(f"ℹ️ No hay pagos pendientes o el formato de respuesta no es una lista (Recibido: {type(settlements)}).")
            settlements = []

        for settlement in settlements:
            if isinstance(settlement, dict) and settlement.get("status") == "settled":
                for job_id, data in list(state.items()):
                    if data.get("res_id") == settlement.get("res_id") and data.get("status") == "pending_payment":
                        print(f"💰 Pago confirmado para el trabajo {job_id}")
                        
                        try:
                            job_details = aw.jobs.get(job_id)
                            input_data = job_details.get("input", {})
                            
                            # Procesar y entregar
                            output = procesar_trabajo(data["job_type"], input_data)
                            aw.jobs.deliver(job_id, output=output)
                            
                            data["status"] = "paid"
                            print(f"  ✅ Trabajo {job_id} entregado con éxito.")
                        except Exception as e:
                            print(f"  ❌ Error entregando trabajo: {e}")
    except Exception as e:
        print(f"⚠️ Error revisando pagos: {e}")

    save_state(state)
    print("🏁 Ciclo completado.")

if __name__ == "__main__":
    main()
