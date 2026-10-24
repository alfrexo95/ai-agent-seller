import os
import json
from agentsouk import AgentSouk
from agents_u_cash import AgentsUCash

AGENTSOUK_API_KEY = os.environ["AGENTSOUK_API_KEY"]
UCASH_API_KEY = os.environ["UCASH_API_KEY"]

aw = AgentSouk(api_key=AGENTSOUK_API_KEY)
ucash = AgentsUCash(api_key=UCASH_API_KEY)

# Archivo para recordar qué jobs ya tienen enlace de pago generado
STATE_FILE = "pending_jobs.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def procesar_trabajo(job_type, input_data):
    """Aquí va la lógica real de tu servicio."""
    if job_type == "translation":
        # Ejemplo simple: devolver el texto con un prefijo
        return {"translation": f"[Traducido al español] {input_data.get('text', '')}"}
    elif job_type == "data_analysis":
        # Ejemplo simple: contar elementos
        data = input_data.get("data", [])
        return {"analysis": f"Se analizaron {len(data)} elementos."}
    else:
        return {"error": "Tipo de trabajo no soportado"}

def main():
    state = load_state()

    # 1. Revisar inbox de Agentsouk
    try:
        inbox = aw.inbox()
        jobs = inbox.get("jobs", [])
    except Exception as e:
        print(f"❌ Error obteniendo inbox: {e}")
        return

    for job in jobs:
        job_id = job["id"]
        
        # Si ya generamos un enlace de pago para este job, saltar
        if job_id in state:
            continue

        print(f"📥 Nuevo trabajo: {job_id} - {job.get('listing_title', 'Sin título')}")
        
        # Determinar precio (ej. $2 USD)
        price_usd = 2.00
        
        try:
            # Crear recurso de pago en agents-u-cash
            res = ucash.create_resource(amount=price_usd)
            res_id = res["res_id"]
            
            # Generar el enlace de pago
            payment_url = f"https://agents.u.cash/r/{res_id}"
            
            # Enviar el enlace al comprador (usando el método de mensaje de Agentsouk)
            # Nota: El método exacto puede variar. Usamos 'aw.jobs.message' como ejemplo.
            aw.jobs.message(job_id, f"Por favor paga ${price_usd} USD aquí para continuar: {payment_url}")
            
            # Guardar en el estado
            state[job_id] = {
                "res_id": res_id,
                "price": price_usd,
                "payment_url": payment_url,
                "status": "pending_payment"
            }
            print(f"  ✅ Enlace de pago enviado: {payment_url}")
            
        except Exception as e:
            print(f"  ❌ Error generando pago para {job_id}: {e}")

    # 2. Revisar pagos completados en agents-u-cash
    try:
        settlements = ucash.get_settlements()
        for settlement in settlements:
            if settlement.get("status") == "settled":
                # Buscar el job correspondiente por res_id
                for job_id, data in list(state.items()):
                    if data.get("res_id") == settlement.get("res_id") and data.get("status") == "pending_payment":
                        print(f"💰 Pago confirmado para el trabajo {job_id}")
                        
                        # Aquí deberías obtener el input del job y procesarlo
                        # job_details = aw.jobs.get(job_id)
                        # output = procesar_trabajo(job_details["listing"]["category"], job_details["input"])
                        
                        # Entregar el resultado
                        # aw.jobs.deliver(job_id, output=output)
                        
                        data["status"] = "paid"
                        print(f"  ✅ Trabajo {job_id} marcado como pagado y entregado.")
    except Exception as e:
        print(f"⚠️ Error revisando pagos: {e}")

    save_state(state)
    print("🏁 Ciclo completado.")

if __name__ == "__main__":
    main()
