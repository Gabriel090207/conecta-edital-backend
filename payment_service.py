import mercadopago
import os

from dotenv import load_dotenv
from datetime import datetime
import asyncio
from typing import Optional

# Carrega variáveis de ambiente
load_dotenv()

# --- Configuração do Mercado Pago ---
MP_ACCESS_TOKEN = os.getenv('MP_ACCESS_TOKEN')

sdk = None
if not MP_ACCESS_TOKEN:
    print("ATENÇÃO: MP_ACCESS_TOKEN não está configurado no seu arquivo .env. O Mercado Pago não funcionará.")
else:
    try:
        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        print("SDK do Mercado Pago inicializado com sucesso.")
    except Exception as e:
        print(f"Erro ao inicializar o SDK do Mercado Pago: {e}. Verifique seu MP_ACCESS_TOKEN.")
        sdk = None
        
# Planos disponíveis
PLANS = {
    "basic_plan": {
        "title": "Plano Essencial",
        "description": "Até 3 monitoramentos simultâneos, verificação diária.",
        "price": 19.90,
        "currency_id": "BRL",
        "plan_id": "acfb870d3be545b4b2b66fcd225274c1"
    },
    "premium_plan": {
        "title": "Plano Premium",
        "description": "Monitoramentos ilimitados, verificação em tempo real, todas as notificações.",
        "price": 1.00,
        "currency_id": "BRL",
        "plan_id": "b8754e354096452e99c46519f061d10c"
    }
}

async def create_mercadopago_subscription_preference(plan_id: str, user_email: str, user_id: str) -> Optional[str]:
    """
    Cria uma preferência de assinatura (preapproval) no Mercado Pago, vinculando-a a um plano.
    Retorna a URL de checkout (init_point) para o usuário completar a assinatura.
    """
    if not sdk:
        print("❌ SDK do Mercado Pago não está inicializado.")
        return None

    plan_details = PLANS.get(plan_id)
    if not plan_details:
        print(f"❌ Plano '{plan_id}' não encontrado.")
        return None

    mercadopago_plan_id = plan_details.get("plan_id")
    if not mercadopago_plan_id or mercadopago_plan_id.startswith("YOUR_MERCADOPAGO_"):
        print(f"❌ ID do plano do Mercado Pago não configurado corretamente para '{plan_id}'.")
        return None

    # URL para redirecionamento após o pagamento (ajuste se necessário)
    FRONTEND_PUBLIC_URL = "https://gentle-cucurucho-5f9e84.netlify.app/"  # Substitua pela URL do seu frontend
    back_url = f"{FRONTEND_PUBLIC_URL}/payment-success"

    preapproval_data = {
        "preapproval_plan_id": mercadopago_plan_id,
        "reason": plan_details["title"],
        "payer_email": user_email,
        "external_reference": user_id,
        "back_url": back_url,
        "status": "pending"
    }

    try:
        # Executa a criação do preapproval em thread separada (não bloqueia o async)
        response = await asyncio.to_thread(sdk.preapproval().create, preapproval_data)

        if not response or response.get("status") != 201:
            error_message = response.get('response', {}).get('message', 'Erro desconhecido')
            print(f"❌ Erro ao criar assinatura: {error_message}")
            print(f"🔍 Resposta completa: {response}")
            return None

        init_point = response["response"].get("init_point")
        if not init_point:
            print("❌ 'init_point' não encontrado na resposta da assinatura.")
            return None

        return init_point

    except Exception as e:
        print(f"❌ Erro inesperado ao criar assinatura: {e}")
        return None
