# backend/main.py
# backend/main.py
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict
import uuid
from datetime import datetime
import httpx
import io
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth, firestore
from firebase_admin.exceptions import FirebaseError
import json
import os
import asyncio

# Importação do novo módulo de serviço de pagamento
from payment_service import create_mercadopago_subscription_preference, PLANS

# Envio de email e variáveis de ambiente
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from dotenv import load_dotenv
import smtplib

# NOVO: Módulos para validação de webhook
import hmac
import hashlib
import logging

# Importação dos templates de email (se existirem)
# Certifique-se de que email_templates.py existe e possui as funções get_monitoring_active_email_html e get_occurrence_found_email_html
import email_templates

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = FastAPI(
    title="API Conecta Edital",
    description="Backend para gerenciar monitoramentos de editais e concursos.",
    version="0.1.0"
)

# Configuração do CORS
# Em produção, substitua "*" pelo domínio real do seu frontend, ex: ["https://conectaedital.com.br"]
# IMPORTANTE: Adicionado o domínio do seu frontend local para o CORS
origins = ["http://127.0.0.1:5500", "http://localhost:5500", "*" "https://conecta-edital-backend.onrender.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOVO: Configurar um logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização do Firebase Admin SDK
try:
    firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if firebase_credentials_json:
        cred_dict = json.loads(firebase_credentials_json)
        cred = credentials.Certificate(cred_dict)
        print("Firebase Admin SDK inicializado com sucesso da variável de ambiente!")
    else:
        # Assumindo que 'chave-firebase.json' está na raiz do backend para desenvolvimento
        if os.path.exists("chave-firebase.json"):
            cred = credentials.Certificate("chave-firebase.json")
            print("Firebase Admin SDK inicializado com sucesso do arquivo local!")
        else:
            raise ValueError("Nenhum arquivo 'chave-firebase.json' ou variável de ambiente 'FIREBASE_CREDENTIALS_JSON' encontrado.")
            
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK inicializado com sucesso!")
except Exception as e:
    print(f"ERRO ao inicializar Firebase Admin SDK: {e}")
    print("Verifique se o arquivo 'chave-firebase.2json' está na raiz do seu projeto backend OU se a variável de ambiente 'FIREBASE_CREDENTIALS_JSON' está configurada.")
    # Considerar encerrar a aplicação se o Firebase for crítico
    # raise SystemExit(f"Não foi possível iniciar o servidor: {e}")

# Credenciais de E-mail (Carregadas do .env)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if not all([SMTP_HOST, EMAIL_ADDRESS, EMAIL_PASSWORD]):
    print("ALERTA: Variáveis de ambiente de e-mail não configuradas. O envio de e-mails não funcionará.")
    print("Verifique seu arquivo .env com SMTP_HOST, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD.")

# NOVO: Variáveis de ambiente do Mercado Pago
MERCADOPAGO_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")

# Dependência de Autenticação Firebase
async def get_current_user_uid(request: Request) -> str:
    """
    Dependência FastAPI para verificar o token de autenticação Firebase.
    Retorna o UID do usuário autenticado.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=401, detail="Token de autenticação não fornecido"
        )

    token = auth_header.split("Bearer ")[1] if "Bearer " in auth_header else None
    if not token:
        raise HTTPException(
            status_code=401, detail="Formato de token inválido (esperado 'Bearer <token>')"
        )

    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]
        print(f"Token Firebase verificado com sucesso para UID: {uid}")
        return uid
    except FirebaseError as e:
        print(f"ERRO: Falha na verificação do token Firebase: {e}")
        raise HTTPException(
            status_code=401, detail=f"Token Firebase inválido ou expirado: {e}"
        )
    except Exception as e:
        print(f"ERRO: Erro inesperado ao processar token: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")

# Função para obter o email do usuário do Firestore
async def get_user_email_from_firestore(uid: str) -> Optional[str]:
    db_firestore_client = firestore.client()
    user_ref = db_firestore_client.collection('users').document(uid)
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        return user_data.get('email')
    print(f"ALERTA: Documento de usuário não encontrado no Firestore para UID: {uid}")
    return None

# Função para obter o tipo de plano do usuário do Firestore
async def get_user_plan_from_firestore(uid: str) -> str:
    db_firestore_client = firestore.client()
    user_ref = db_firestore_client.collection('users').document(uid)
    user_doc = user_ref.get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        return user_data.get('plan_type', 'gratuito')
    print(f"ALERTA: Documento de usuário não encontrado no Firestore para UID: {uid}. Retornando plano 'gratuito'.")
    return 'gratuito'

# Função para determinar o número máximo de slots com base no plano
def get_max_slots_by_plan(plan_type: str) -> int:
    if plan_type == 'premium':
        return 10  # Exemplo: premium tem 10 slots
    elif plan_type == 'basico':
        return 5   # Exemplo: básico tem 5 slots
    else: # 'gratuito' ou qualquer outro
        return 3   # Exemplo: gratuito tem 3 slots

# Modelos Pydantic
class NewPersonalMonitoring(BaseModel):
    link_diario: HttpUrl
    id_edital: str
    nome_completo: str

class NewRadarMonitoring(BaseModel):
    link_diario: HttpUrl
    id_edital: str

class Monitoring(BaseModel):
    id: str
    monitoring_type: str
    official_gazette_link: HttpUrl
    edital_identifier: str
    candidate_name: Optional[str] = None
    cpf: Optional[str] = None
    keywords: str
    last_checked_at: datetime
    last_pdf_hash: Optional[str] = None
    occurrences: int = 0
    status: str = "inactive"
    created_at: datetime
    user_uid: str
    user_email: str

# NOVO MODELO: Para a requisição de criação de preferência de pagamento
class CreatePreferenceRequest(BaseModel):
    plan_id: str # Ex: 'premium_plan', 'basic_plan'
    user_email: str # Para associar a preferência ao usuário (obtido do frontend)

# Simulação de Banco de Dados (em memória) - Para uso temporário ou mock.
mock_db: Dict[str, List[Monitoring]] = {}

# Funções de Lógica de Negócio (existentes)
async def fetch_content(url: HttpUrl) -> Optional[httpx.Response]:
    """Baixa o conteúdo de uma URL e retorna o objeto httpx.Response."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(str(url), follow_redirects=True, timeout=20)
            response.raise_for_status()
            return response
    except httpx.RequestError as exc:
        print(f"ERRO: Não foi possível acessar {url} - {exc}")
        return None
    except Exception as e:
        print(f"ERRO: Inesperado ao baixar conteúdo de {url}: {e}")
        return None

async def find_pdf_in_html(html_content: bytes, base_url: HttpUrl) -> Optional[HttpUrl]:
    """Tenta encontrar um link para PDF dentro de um conteúdo HTML."""
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_links_found = []
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        link_text = a_tag.get_text().lower()

        if href.lower().endswith('.pdf'):
            if not href.startswith(('http://', 'https://')):
                full_pdf_url = urljoin(str(base_url), href)
            else:
                full_pdf_url = href
            
            try:
                pdf_url_obj = HttpUrl(full_pdf_url)
                if "edital" in link_text or "anexo" in link_text or "completo" in link_text or "gabarito" in link_text or "resultado" in link_text or "aviso" in link_text:
                    pdf_links_found.insert(0, pdf_url_obj)
                else:
                    pdf_links_found.append(pdf_url_obj)
                
                print(f"DEBUG: Link PDF encontrado no HTML: {pdf_url_obj} (Texto: '{link_text}')")
            except Exception as e:
                print(f"ALERTA: Link inválido encontrado no HTML: {full_pdf_url} - {e}")
                
    if pdf_links_found:
        return pdf_links_found[0]
    
    return None

async def get_pdf_content_from_url(url: HttpUrl) -> Optional[bytes]:
    """Tenta obter o conteúdo PDF diretamente ou encontrando um link PDF em uma página HTML."""
    print(f"DEBUG: Tentando obter conteúdo de: {url}")
    
    response = await fetch_content(url)
    if not response:
        return None

    content_type = response.headers.get('Content-Type', '').lower()
    
    if 'application/pdf' in content_type:
        print(f"DEBUG: URL {url} é um PDF direto.")
        return response.content
    
    if 'text/html' in content_type:
        print(f"DEBUG: URL {url} é uma página HTML. Procurando links PDF dentro dela...")
        pdf_url_in_html = await find_pdf_in_html(response.content, url)
        if pdf_url_in_html:
            print(f"DEBUG: Encontrado link PDF dentro do HTML: {pdf_url_in_html}. Baixando este PDF...")
            pdf_response = await fetch_content(pdf_url_in_html)
            if pdf_response and 'application/pdf' in pdf_response.headers.get('Content-Type', '').lower():
                return pdf_response.content
            else:
                print(f"ALERTA: O link encontrado no HTML ({pdf_url_in_html}) não resultou em um PDF válido.")
        else:
            print(f"ALERTA: Não foi possível encontrar um link PDF na página HTML: {url}")
    else:
        print(f"ALERTA: Tipo de conteúdo inesperado para {url}: {content_type}. Esperado PDF ou HTML.")
    
    return None

async def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extrai texto de conteúdo PDF binário."""
    try:
        reader = PdfReader(io.BytesIO(pdf_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"ERRO: Ao extrair texto do PDF: {e}")
        return ""

def send_email_notification(
    monitoramento: Monitoring,
    template_type: str, # Tipo de template ('monitoring_active' ou 'occurrence_found')
    to_email: str,
    found_keywords: Optional[List[str]] = None # Opcional, usado apenas para 'occurrence_found'
):
    """
    Envia uma notificação por e-mail com base no template especificado.
    """
    if not all([SMTP_HOST, EMAIL_ADDRESS, EMAIL_PASSWORD, to_email]):
        print("ERRO: Credenciais de e-mail ou destinatário ausentes. Não é possível enviar e-mail.")
        return

    html_content = ""
    subject = ""
    user_full_name_from_monitoramento = ""
    # Tenta buscar o fullName do Firestore para o e-mail
    try:
        db_firestore_client = firestore.client()
        user_doc_ref = db_firestore_client.collection('users').document(monitoramento.user_uid)
        user_doc = user_doc_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_full_name_from_monitoramento = user_data.get('fullName', monitoramento.user_email.split('@')[0])
        else:
            user_full_name_from_monitoramento = monitoramento.user_email.split('@')[0]
    except Exception as e:
        print(f"ALERTA: Não foi possível buscar fullName do Firestore para email. Usando parte do email. Erro: {e}")
        user_full_name_from_monitoramento = monitoramento.user_email.split('@')[0] # Fallback

    if template_type == 'monitoring_active':
        html_content = email_templates.get_monitoring_active_email_html(
            user_full_name=user_full_name_from_monitoramento,
            monitoring_type=monitoramento.monitoring_type,
            official_gazette_link=str(monitoramento.official_gazette_link),
            edital_identifier=monitoramento.edital_identifier,
            candidate_name=monitoramento.candidate_name,
            keywords=monitoramento.keywords
        )
        subject = f"Conecta Edital: Seu Monitoramento para '{monitoramento.edital_identifier}' está Ativo!"
    elif template_type == 'occurrence_found':
        if not found_keywords:
            print("ALERTA: found_keywords é necessário para o template 'occurrence_found'.")
            return

        html_content = email_templates.get_occurrence_found_email_html(
            user_full_name=user_full_name_from_monitoramento,
            edital_identifier=monitoramento.edital_identifier,
            official_gazette_link=str(monitoramento.official_gazette_link),
            found_keywords=found_keywords
        )
        subject = f"Conecta Edital: Nova Ocorrência Encontrada no Edital '{monitoramento.edital_identifier}'"
    else:
        print(f"ERRO: Tipo de template de email desconhecido: {template_type}")
        return

    msg = MIMEText(html_content, 'html', 'utf-8')
    
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = formataddr((str(Header('Conecta Edital', 'utf-8')), EMAIL_ADDRESS))
    msg['To'] = to_email

    try:
        if SMTP_PORT == 465: # SSL
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
        else: # TLS (geralmente porta 587)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
        print(f"E-mail de notificação ENVIADO com sucesso para {to_email} (Tipo: {template_type}).")
    except smtplib.SMTPAuthenticationError:
        print("ERRO: Falha de autenticação SMTP. Verifique seu EMAIL_ADDRESS e EMAIL_PASSWORD/App Password.")
    except smtplib.SMTPConnectError as e:
        print(f"ERRO: Falha ao conectar ao servidor SMTP {SMTP_HOST}:{SMTP_PORT} - {e}. Verifique o HOST e a PORTA.")
    except Exception as e:
        print(f"ERRO: Erro inesperado ao enviar e-mail: {e}")

async def perform_monitoring_check(monitoramento: Monitoring):
    """
    Executa a verificação para um monitoramento específico.
    Dispara o envio de email se uma ocorrência for encontrada.
    """
    print(f"\n--- Iniciando verificação para monitoramento {monitoramento.id} ({monitoramento.monitoring_type}) do usuário {monitoramento.user_uid} ---")
    
    pdf_content = await get_pdf_content_from_url(monitoramento.official_gazette_link)
    if not pdf_content:
        print(f"Verificação para {monitoramento.id} falhou: Não foi possível obter o PDF.")
        return

    current_pdf_hash = str(hash(pdf_content))

    if monitoramento.last_pdf_hash and monitoramento.last_pdf_hash == current_pdf_hash:
        print(f"PDF para {monitoramento.id} não mudou desde a última verificação. Nenhuma notificação necessária.")
        for mon in mock_db.get(monitoramento.user_uid, []):
            if mon.id == monitoramento.id:
                mon.last_checked_at = datetime.now()
                break
        return

    monitoramento.last_pdf_hash = current_pdf_hash
    monitoramento.last_checked_at = datetime.now()
    for i, mon in enumerate(mock_db.get(monitoramento.user_uid, [])):
        if mon.id == monitoramento.id:
            mock_db[monitoramento.user_uid][i] = monitoramento
            break

    print(f"DEBUG: PDF para {monitoramento.id} é NOVO ou MODIFICADO. Prosseguindo com a análise.")
    
    pdf_text = await extract_text_from_pdf(pdf_content)
    
    found_keywords = []
    keywords_to_search = [monitoramento.edital_identifier]
    if monitoramento.monitoring_type == 'personal' and monitoramento.candidate_name:
        keywords_to_search.append(monitoramento.candidate_name)
    
    try:
        parsed_url = urlparse(str(monitoramento.official_gazette_link))
        file_name = parsed_url.path.split('/')[-1]
    except Exception:
        file_name = ""

    pdf_text_lower = pdf_text.lower()
    file_name_lower = file_name.lower()

    for keyword in keywords_to_search:
        keyword_lower = keyword.lower()
        if keyword_lower in pdf_text_lower or keyword_lower in file_name_lower:
            found_keywords.append(keyword)

    if found_keywords:
        monitoramento.occurrences += 1
        for i, mon in enumerate(mock_db.get(monitoramento.user_uid, [])):
            if mon.id == monitoramento.id:
                mock_db[monitoramento.user_uid][i] = monitoramento
                break

        print(f"✅ Ocorrência ENCONTRADA para {monitoramento.id}! Palavras-chave: {', '.join(found_keywords)}")
        send_email_notification(
            monitoramento=monitoramento,
            template_type='occurrence_found',
            to_email=monitoramento.user_email,
            found_keywords=found_keywords
        )
    else:
        print(f"❌ Nenhuma ocorrência encontrada para {monitoramento.id}.")
    print(f"--- Verificação para {monitoramento.id} Concluída ---\n")

# Agendador simples em background para verificações recorrentes
async def periodic_monitoring_task():
    await asyncio.sleep(5)
    while True:
        print(f"\nIniciando rodada de verificações periódicas para TODOS os usuários...")
        for user_uid, user_monitorings in list(mock_db.items()):
            for mon in list(user_monitorings):
                if mon.status == "active":
                    await perform_monitoring_check(mon)
        print(f"Rodada de verificações periódicas concluída. Próxima em 30 segundos.")
        await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_monitoring_task())
    print("Tarefa de monitoramento periódico iniciada.")

# Endpoints da API
@app.get("/")
async def read_root():
    return {"message": "Bem-vindo à API Conecta Edital!"}

@app.post("/api/monitoramentos/pessoal", response_model=Monitoring, status_code=201)
async def create_personal_monitoramento(
    monitoramento_data: NewPersonalMonitoring,
    background_tasks: BackgroundTasks,
    user_uid: str = Depends(get_current_user_uid)
):
    user_monitorings = mock_db.get(user_uid, [])
    
    user_plan_for_creation = await get_user_plan_from_firestore(user_uid)
    max_slots = get_max_slots_by_plan(user_plan_for_creation)

    if len(user_monitorings) >= max_slots:
        raise HTTPException(
            status_code=403,
            detail="Limite de slots de monitoramento atingido. Faça upgrade do seu plano para adicionar mais!"
        )
    
    user_email = await get_user_email_from_firestore(user_uid)
    if not user_email:
        raise HTTPException(
            status_code=404, detail="E-mail do usuário não encontrado no Firestore."
        )

    new_id = f"mon-{str(uuid.uuid4())[:8]}-personal"
    new_monitoring = Monitoring(
        id=new_id,
        monitoring_type='personal',
        official_gazette_link=monitoramento_data.link_diario,
        edital_identifier=monitoramento_data.id_edital,
        candidate_name=monitoramento_data.nome_completo,
        keywords=f"{monitoramento_data.nome_completo}, {monitoramento_data.id_edital}",
        last_checked_at=datetime.now(),
        created_at=datetime.now(),
        status="active",
        user_uid=user_uid,
        user_email=user_email
    )
    
    if user_uid not in mock_db:
        mock_db[user_uid] = []
    mock_db[user_uid].append(new_monitoring)
    
    background_tasks.add_task(
        send_email_notification,
        monitoramento=new_monitoring,
        template_type='monitoring_active',
        to_email=new_monitoring.user_email
    )
    background_tasks.add_task(perform_monitoring_check, new_monitoring)
    
    print(f"Novo Monitoramento Pessoal criado para UID {user_uid}: {new_monitoring.dict()}")
    return new_monitoring

@app.post("/api/monitoramentos/radar", response_model=Monitoring, status_code=201)
async def create_radar_monitoramento(
    monitoramento_data: NewRadarMonitoring,
    background_tasks: BackgroundTasks,
    user_uid: str = Depends(get_current_user_uid)
):
    user_monitorings = mock_db.get(user_uid, [])
    
    user_plan_for_creation = await get_user_plan_from_firestore(user_uid)
    max_slots = get_max_slots_by_plan(user_plan_for_creation)

    if len(user_monitorings) >= max_slots:
        raise HTTPException(
            status_code=403,
            detail="Limite de slots de monitoramento atingido. Faça upgrade do seu plano para adicionar mais!"
        )

    user_email = await get_user_email_from_firestore(user_uid)
    if not user_email:
        raise HTTPException(
            status_code=404, detail="E-mail do usuário não encontrado no Firestore."
        )

    new_id = f"mon-{str(uuid.uuid4())[:8]}-radar"
    new_monitoring = Monitoring(
        id=new_id,
        monitoring_type='radar',
        official_gazette_link=monitoramento_data.link_diario,
        edital_identifier=monitoramento_data.id_edital,
        keywords=monitoramento_data.id_edital,
        last_checked_at=datetime.now(),
        created_at=datetime.now(),
        status="active",
        user_uid=user_uid,
        user_email=user_email
    )
    
    if user_uid not in mock_db:
        mock_db[user_uid] = []
    mock_db[user_uid].append(new_monitoring)

    background_tasks.add_task(
        send_email_notification,
        monitoramento=new_monitoring,
        template_type='monitoring_active',
        to_email=new_monitoring.user_email
    )
    background_tasks.add_task(perform_monitoring_check, new_monitoring)

    print(f"Novo Monitoramento Radar criado para UID {user_uid}: {new_monitoring.dict()}")
    return new_monitoring

# Endpoint para Gerar Preferência de Pagamento
@app.post("/api/create_preference")
async def create_preference(
    request_data: CreatePreferenceRequest,
    user_uid: str = Depends(get_current_user_uid)
):
    # A preferência de pagamento será criada na função create_mercadopago_preference
    
    try:
        # A função create_mercadopago_subscription_preference agora espera o ID de plano correto
        checkout_url = await create_mercadopago_subscription_preference(
            plan_id=request_data.plan_id,
            user_email=request_data.user_email,
            user_id=user_uid
        )
        if not checkout_url:
            raise HTTPException(status_code=500, detail="Erro ao criar preferência de pagamento com Mercado Pago.")
        
        return {"checkout_url": checkout_url}
    
    except Exception as e:
        print(f"ERRO GERAL ao criar preferência de pagamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro geral ao criar preferência de pagamento: {e}")

# NOVO ENDPOINT: Para receber notificações de webhook do Mercado Pago
@app.post("/api/mercadopago_webhook")
async def mercadopago_webhook(request: Request):
    """
    Endpoint para receber e processar notificações de webhook do Mercado Pago.
    """
    logger.info("Webhook do Mercado Pago recebido.")

    # 1. Verificação da Assinatura do Webhook para Segurança
    mp_signature_hash = request.headers.get("x-signature")
    if not mp_signature_hash:
        logger.warning("Cabeçalho de assinatura do Mercado Pago ausente. Rejeitando a requisição.")
        raise HTTPException(status_code=401, detail="Assinatura de webhook ausente.")
    
    # Extrai o "ts" e "v1" da assinatura
    try:
        signature_parts = mp_signature_hash.split(",")
        signature_dict = {part.split("=")[0]: part.split("=")[1] for part in signature_parts}
        ts = signature_dict.get("ts")
        v1 = signature_dict.get("v1")

        if not ts or not v1:
            logger.error("Assinatura do Mercado Pago em formato inválido.")
            raise HTTPException(status_code=401, detail="Assinatura de webhook em formato inválido.")
    except Exception as e:
        logger.error(f"Erro ao analisar a assinatura do Mercado Pago: {e}")
        raise HTTPException(status_code=401, detail="Erro ao analisar a assinatura de webhook.")

    if not MERCADOPAGO_WEBHOOK_SECRET:
        logger.error("Variável de ambiente MERCADOPAGO_WEBHOOK_SECRET não configurada.")
        # Em produção, você deve considerar encerrar a aplicação se isso acontecer.
        raise HTTPException(status_code=500, detail="Configuração de webhook do servidor ausente.")

    body = await request.body()
    data_to_hash = f"id:{request.headers.get('x-request-id')};ts:{ts};{body.decode('utf-8')}".encode('utf-8')
    calculated_v1 = hmac.new(
        MERCADOPAGO_WEBHOOK_SECRET.encode('utf-8'),
        data_to_hash,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(v1, calculated_v1):
        logger.warning("Falha na validação da assinatura do webhook do Mercado Pago. Rejeitando requisição.")
        raise HTTPException(status_code=401, detail="Assinatura de webhook inválida.")
    
    # Fim da verificação de segurança. A requisição é legítima.

    try:
        notification_data = json.loads(body)
        logger.info(f"Dados da notificação: {notification_data}")
        
        resource_id = notification_data.get("data", {}).get("id")
        topic = notification_data.get("topic")

        if not resource_id or not topic:
            logger.warning("Dados da notificação incompletos.")
            return {"status": "ok"} # Retorna OK para evitar reenvios.

        # 2. Busca os detalhes da assinatura no Mercado Pago
        if topic == "preapproval":
            # Usar a biblioteca httpx para buscar detalhes da assinatura
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}"
                }
                response = await client.get(
                    f"https://api.mercadopago.com/preapproval/{resource_id}",
                    headers=headers
                )
                response.raise_for_status()
                preapproval_data = response.json()
                
            # Extrai o user_id e o plano associado do preapproval
            user_id = preapproval_data.get("external_reference")
            status = preapproval_data.get("status")
            plan_id = preapproval_data.get("preapproval_plan_id")
            
            logger.info(f"Preapproval ID: {resource_id}, Status: {status}, User ID: {user_id}, Plan ID: {plan_id}")

            if status == "authorized" and user_id and plan_id:
                # Mapeia o ID do plano do Mercado Pago para o tipo de plano do seu sistema
                plan_type_mapping = {
                    PLANS.get('premium_plan').get('plan_id'): 'premium',
                    PLANS.get('basic_plan').get('plan_id'): 'basico',
                    # Adicione outros planos se houver
                }
                new_plan_type = plan_type_mapping.get(plan_id)

                if new_plan_type:
                    # 3. Atualiza o plano do usuário no Firestore
                    db_firestore_client = firestore.client()
                    user_ref = db_firestore_client.collection('users').document(user_id)
                    user_ref.update({"plan_type": new_plan_type})
                    logger.info(f"Plano do usuário {user_id} atualizado para '{new_plan_type}' no Firestore.")
                else:
                    logger.warning(f"Plano do Mercado Pago ID '{plan_id}' não mapeado para um tipo de plano conhecido.")

        return {"status": "ok"}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro ao buscar detalhes do recurso no Mercado Pago: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar notificação do Mercado Pago: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado no endpoint de webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Erro inesperado no processamento do webhook: {e}")


@app.get("/api/monitoramentos", response_model=List[Monitoring])
async def get_all_monitoramentos(user_uid: str = Depends(get_current_user_uid)):
    return mock_db.get(user_uid, [])

@app.get("/api/status")
async def get_status(user_uid: str = Depends(get_current_user_uid)):
    user_monitorings = mock_db.get(user_uid, [])
    total_monitoramentos = len(user_monitorings)
    ativos = sum(1 for m in user_monitorings if m.status == 'active')
    
    user_plan = await get_user_plan_from_firestore(user_uid)
    current_total_slots = get_max_slots_by_plan(user_plan)

    slots_livres = current_total_slots - total_monitoramentos
    if slots_livres < 0:
        slots_livres = 0

    return {
        "total_slots": current_total_slots,
        "slots_disponiveis": slots_livres,
        "slots_livres": slots_livres,
        "total_monitoramentos": total_monitoramentos,
        "monitoramentos_ativos": ativos,
        "user_plan": user_plan
    }

@app.delete("/api/monitoramentos/{monitoring_id}", status_code=204)
async def delete_monitoring(monitoring_id: str, user_uid: str = Depends(get_current_user_uid)):
    global mock_db
    user_monitorings = mock_db.get(user_uid, [])
    
    initial_len = len(user_monitorings)
    mock_db[user_uid] = [mon for mon in user_monitorings if mon.id != monitoring_id]
    
    if len(mock_db[user_uid]) == initial_len:
        raise HTTPException(status_code=404, detail="Monitoramento não encontrado ou não pertence a este usuário.")
    print(f"Monitoramento {monitoring_id} excluído para UID {user_uid}.")
    return

@app.post("/api/monitoramentos/{monitoring_id}/test", response_model=Monitoring)
async def test_monitoring(monitoring_id: str, background_tasks: BackgroundTasks, user_uid: str = Depends(get_current_user_uid)):
    user_monitorings = mock_db.get(user_uid, [])
    monitoramento = next((mon for mon in user_monitorings if mon.id == monitoring_id), None)
    if not monitoramento:
        raise HTTPException(status_code=404, detail="Monitoramento não encontrado ou não pertence a este usuário.")
    
    print(f"Executando TESTE IMEDIATO para monitoramento {monitoring_id} do UID {user_uid}...")
    background_tasks.add_task(perform_monitoring_check, monitoramento)
    
    return monitoramento

@app.patch("/api/monitoramentos/{monitoring_id}/status", response_model=Monitoring)
async def update_monitoring_status(monitoring_id: str, status_update: Dict[str, bool], user_uid: str = Depends(get_current_user_uid)):
    user_monitorings = mock_db.get(user_uid, [])
    monitoramento = next((mon for mon in user_monitorings if mon.id == monitoring_id), None)
    if not monitoramento:
        raise HTTPException(status_code=404, detail="Monitoramento não encontrado ou não pertence a este usuário.")

    is_active = status_update.get('active')
    if is_active is None:
        raise HTTPException(status_code=400, detail="Campo 'active' é obrigatório.")

    monitoramento.status = "active" if is_active else "inactive"
    print(f"Monitoramento {monitoring_id} status alterado para {monitoramento.status} para UID {user_uid}")
    return monitoramento