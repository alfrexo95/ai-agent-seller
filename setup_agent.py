import os
from agentsouk import AgentSouk
from agents_u_cash import AgentsUCash

# --- CONFIGURACIÓN (EDITA ESTOS DOS VALORES) ---
U_CASH_EMAIL = "alfredogoodgold@gmail.com"  # <--- PON TU EMAIL
U_CASH_PASSWORD = "Haley2020*" # <--- PON UNA CONTRASEÑA SEGURA
# -----------------------------------------------

AGENTSOUK_API_KEY = "as_live_yUCa4De6CoL0v6AKy3suHQA9Zj5faOmynrYGHvL"

# Tus direcciones de pago
WALLETS = {
    "btc": "bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00",
    "eth": "0xA5E6eB31868A85127B1ED82b8C760193356206ED",
    "ltc": "ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne",
    "lightning": "chieftrait089@walletofsatoshi.com"
}

def main():
    print("🚀 Configurando el agente vendedor...")

    # 1. Registrar en agents-u-cash y obtener API Key
    print("📝 Registrando en agents-u-cash...")
    try:
        ucash_signup = AgentsUCash().signup(email=U_CASH_EMAIL, password=U_CASH_PASSWORD)
        ucash_api_key = ucash_signup["api_key"]
        print(f"✅ API Key de agents-u-cash: {ucash_api_key}")
    except Exception as e:
        print(f"❌ Error en el registro: {e}")
        print("💡 Si ya tienes una cuenta, omite este paso y usa tu API Key existente.")
        return

    # 2. Configurar wallets en agents-u-cash
    print("💳 Configurando wallets de pago...")
    agent_ucash = AgentsUCash(api_key=ucash_api_key)
    for coin, address in WALLETS.items():
        try:
            agent_ucash.set_wallet(coin, address)
            print(f"  ✅ Wallet {coin.upper()} configurada.")
        except Exception as e:
            print(f"  ⚠️ Error configurando {coin}: {e}")

    # 3. Crear listings gratuitos en Agentsouk
    print("🏪 Creando listings en Agentsouk...")
    aw = AgentSouk(api_key=AGENTSOUK_API_KEY)

    # Listing de Traducción
    try:
        aw.listings.create(
            title="Traducción Automática (Español)",
            description="Traduzco cualquier texto al español. Envía {text} y recibe la traducción.",
            category="text",
            price=0,
            input_schema={"type": "object", "required": ["text"]}
        )
        print("  ✅ Listing de Traducción creado.")
    except Exception as e:
        print(f"  ⚠️ Error creando listing de traducción: {e}")

    # Listing de Análisis de Datos
    try:
        aw.listings.create(
            title="Análisis de Datos y Señales",
            description="Analizo datos de mercado y devuelvo señales simples. Envía {data} y recibe el análisis.",
            category="data",
            price=0,
            input_schema={"type": "object", "required": ["data"]}
        )
        print("  ✅ Listing de Análisis creado.")
    except Exception as e:
        print(f"  ⚠️ Error creando listing de análisis: {e}")

    print("\n🎉 ¡Configuración completada!")
    print(f"🔑 Guarda esta API Key de agents-u-cash: {ucash_api_key}")

if __name__ == "__main__":
    main()
