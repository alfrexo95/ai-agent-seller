from agentsouk import AgentSouk
from agents_u_cash import AgentsUCash

AGENTSOUK_API_KEY = "as_live_yUCa4De6CoL0v6AKy3suHQA9Zj5faOmynrYGHvL"
UCASH_API_KEY = "229202cabb2f95e19bfd3f0f19abea2ea02dc3c6"

WALLETS = {
    "btc": "bc1qt3rukpe7qp737zj5j5xpxxmcqv90cfefhg5e00",
    "eth": "0xA5E6eB31868A85127B1ED82b8C760193356206ED",
    "ltc": "ltc1qdyyg99l8ehp9aj4ehzvmefglmpl9750226k7ne",
    "lightning": "chieftrait089@walletofsatoshi.com"
}

print("💳 Configurando wallets de pago en agents-u-cash...")
ucash = AgentsUCash(api_key=UCASH_API_KEY)
for coin, address in WALLETS.items():
    try:
        ucash.set_wallet(coin, address)
        print(f"  ✅ Wallet {coin.upper()} configurada.")
    except Exception as e:
        print(f"  ⚠️ Error configurando {coin}: {e}")

print("🏪 Creando listings en Agentsouk...")
aw = AgentSouk(api_key=AGENTSOUK_API_KEY)

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

print("🎉 ¡Configuración completada!")
