import mercadopago
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio
from typing import Optional

# Carrega as variáveis de ambiente do arquivo .env
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

# Planos disponíveis para assinatura
PLANS = {
    "basic_plan": {
        "title": "Plano Essencial",
        "description": "Até 3 monitoramentos simultâneos, verificação diária.",
        "price": 19.90,  
        "currency_id": "BRL",
        "plan_id": "894e4340e63b462fbf74c4f365b5b04e" # ID do Plano Essencial
    },
    "premium_plan": {
        "title": "Plano Premium",
        "description": "Monitoramentos ilimitados, verificação em tempo real, todas as notificações.",
        "price": 1.00,   
        "currency_id": "BRL",
        "plan_id": "af9730cd58924cf1837a1fe8bcf04616" # ID do Plano Premium
    }
}


async def create_mercadopago_subscription_preference(plan_id: str, user_email: str, user_id: str) -> Optional[str]:
    """
    Cria uma preferência de assinatura (preapproval) no Mercado Pago, vinculando-a a um plano existente.
    Retorna a URL (init_point) para o usuário completar o checkout.
    """
    if not sdk:
        print("Erro: SDK do Mercado Pago não inicializado.")
        return None

    plan_details = PLANS.get(plan_id)
    if not plan_details:
        print(f"Erro: plano '{plan_id}' não encontrado nas configurações locais.")
        return None

    mercadopago_plan_id = plan_details.get("plan_id")
    if not mercadopago_plan_id or mercadopago_plan_id.startswith("YOUR_MERCADOPAGO_"):
        print(f"Erro: ID do plano do Mercado Pago não configurado para '{plan_id}'.")
        return None

    FRONTEND_PUBLIC_URL = "http://127.0.0.1:5500/front"

    preapproval_data = {
        "preapproval_plan_id": mercadopago_plan_id,
        "reason": plan_details["title"],
        "payer_email": user_email,
        "external_reference": user_id,
        "back_url": FRONTEND_PUBLIC_URL + "/payment-success",
        "status": "pending"
    }

    try:
        response = await asyncio.to_thread(sdk.preapproval().create, preapproval_data)

        if not response or response.get("status") != 201:
            error_message = response.get('response', {}).get('message', 'Erro desconhecido')
            print(f"Erro ao criar assinatura no Mercado Pago: {error_message}")
            print(f"Resposta completa do MP: {response}")
            return None

        init_point = response["response"].get("init_point")
        if not init_point:
            print("Erro: 'init_point' não encontrado na resposta de criação de assinatura do Mercado Pago.")
            return None

        return init_point

    except Exception as e:
        print(f"Erro inesperado ao criar assinatura no Mercado Pago: {e}")
        return None