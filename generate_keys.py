import os
import subprocess
from agentsouk import AgentSouk
from agents_u_cash import AgentsUCash

print("🚀 Generando nuevas API Keys desde Termux...")

# --- 1. Agentsouk ---
print("\n📝 Registrando nuevo agente en Agentsouk...")
try:
    reg = AgentSouk.register(
        name="Cuban Freedom Bot v2",
        description="Traducción automática y análisis de datos/señales para agentes de IA.",
        capabilities=["translation", "data_analysis"]
    )
    agentsouk_key = reg["api_keys"]["live"]
    print(f"✅ Agentsouk API Key generada: {agentsouk_key[:10]}...")
except Exception as e:
    print(f"❌ Error en Agentsouk: {e}")
    agentsouk_key = None

# --- 2. Agents-u-cash ---
print("\n📝 Creando cuenta en Agents-u-cash...")
email = input("Introduce un email para U-cash (ej. tunombre@ejemplo.com): ")
password = input("Introduce una contraseña para U-cash (mín. 8 caracteres): ")

try:
    ucash_signup = AgentsUCash().signup(email=email, password=password)
    ucash_key = ucash_signup["api_key"]
    print(f"✅ U-cash API Key generada: {ucash_key[:10]}...")
except Exception as e:
    print(f"❌ Error en U-cash: {e}")
    ucash_key = None

# --- 3. Guardar en GitHub ---
if agentsouk_key and ucash_key:
    print("\n💾 Guardando claves en los secretos de GitHub...")
    repo = "alfrexo95/ai-agent-seller"
    
    subprocess.run(f'gh secret set AGENTSOUK_API_KEY -R {repo} --body "{agentsouk_key}"', shell=True, check=True)
    subprocess.run(f'gh secret set UCASH_API_KEY -R {repo} --body "{ucash_key}"', shell=True, check=True)
    
    print("✅ ¡Claves guardadas exitosamente!")
    print("\n🔍 Verificando secretos:")
    subprocess.run(f'gh secret list -R {repo}', shell=True)
else:
    print("\n❌ No se pudieron generar todas las claves. Revisa los errores.")
