# backend/login.py

from flask import Flask, request, jsonify, session, redirect, url_for
from google.oauth2 import id_token
from google.auth.transport import requests
from flask_cors import CORS
import os

app = Flask(__name__)

# --- Configuração de Segurança (MUITO IMPORTANTE!) ---
# 1. Chave Secreta para as Sessões Flask:
# Esta chave é usada para assinar os cookies de sessão.
# EM PRODUÇÃO: NUNCA coloque sua chave secreta diretamente no código.
# Use uma variável de ambiente, por exemplo:
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_chave_secreta_super_segura_e_longa_aqui_em_desenvolvimento')
# Se você for testar localmente sem configurar variáveis de ambiente, a string padrão será usada.
# Para gerar uma chave forte: import os; os.urandom(24)

# 2. Configuração CORS:
# Permite que seu frontend (que pode estar em uma porta diferente) se comunique com este backend.
# EM PRODUÇÃO: Seja o mais específico possível. Não use "*" (todos os domínios)
# Por exemplo: CORS(app, resources={r"/api/*": {"origins": "https://seusite.com"}})
CORS(app)

# --- Configuração do Google OAuth ---
# MUITO IMPORTANTE: Substitua pelo seu Client ID real do Google Cloud Console.
# Deve ser o MESMO Client ID que você usou no seu auth.js.
GOOGLE_CLIENT_ID = "704602888829-rhdt9b0f683msil1r5h7q35ckrtqj8l4.apps.googleusercontent.com" # <--- SUBSTITUA AQUI!

# Lista de Client IDs autorizados para verificar o token.
# Geralmente, é apenas o seu GOOGLE_CLIENT_ID para aplicativos web.
CLIENT_IDS = [GOOGLE_CLIENT_ID]

# --- Rotas da API ---

@app.route('/')
def index():
    """Rota inicial para verificar se o backend está rodando."""
    return "Backend do Conecta Edital está rodando! Acesse /api/google-login para autenticação."

@app.route('/api/google-login', methods=['POST'])
def google_login():
    """
    Endpoint para receber o ID Token do Google do frontend,
    verificá-lo e autenticar o usuário.
    """
    data = request.get_json()
    if not data or 'id_token' not in data:
        return jsonify({"error": "Token de ID não fornecido."}), 400

    id_token_from_frontend = data['id_token']

    try:
        # 1. Verificar o token de ID com o Google
        # Esta função decodifica o JWT e verifica sua validade, assinatura e emissor.
        idinfo = id_token.verify_oauth2_token(
            id_token_from_frontend, requests.Request(), GOOGLE_CLIENT_ID
        )

        # 2. Verificar o 'aud' (audience - público) do token
        # Isso garante que o token foi emitido para o SEU aplicativo.
        if idinfo['aud'] not in CLIENT_IDS:
            raise ValueError('Could not verify audience.')

        # 3. Extrair informações do usuário do token
        # 'sub' é o ID único do usuário Google (sub = subject)
        user_id = idinfo['sub']
        user_email = idinfo['email']
        user_name = idinfo.get('name', 'Usuário Google') # Usa .get para evitar KeyError se 'name' não existir
        user_picture = idinfo.get('picture', None) # URL da imagem do perfil

        print(f"✅ Login bem-sucedido para o usuário: {user_email} (ID: {user_id})")

        # 4. Gerenciar a sessão do usuário no seu backend
        # Armazena as informações essenciais na sessão Flask.
        # A sessão é armazenada em um cookie assinado, que o navegador envia automaticamente.
        session['google_id'] = user_id
        session['email'] = user_email
        session['name'] = user_name
        session['logged_in'] = True # Sinaliza que o usuário está logado

        # 5. Retornar uma resposta de sucesso ao frontend
        return jsonify({
            "message": "Login com Google bem-sucedido!",
            "user": {
                "id": user_id,
                "email": user_email,
                "name": user_name,
                "picture": user_picture
            }
        }), 200

    except ValueError as e:
        # Erro na verificação do token (token inválido, expirado, etc.)
        print(f"❌ Erro na verificação do token: {e}")
        return jsonify({"error": f"Token de ID inválido: {e}"}), 401
    except Exception as e:
        # Captura outros erros inesperados durante o processo
        print(f"🔥 Erro inesperado no backend: {e}")
        return jsonify({"error": f"Erro interno do servidor: {e}"}), 500

@app.route('/dashboard')
def dashboard():
    """
    Exemplo de rota protegida que só pode ser acessada por usuários logados.
    No frontend, após o login, você redirecionaria para esta página.
    """
    if 'logged_in' in session and session['logged_in']:
        return f"""
        <h1>Bem-vindo ao Dashboard, {session.get('name', 'Usuário')}!</h1>
        <p>Seu e-mail: {session.get('email')}</p>
        <p><a href="/api/logout">Sair</a></p>
        """
    return redirect(url_for('index')) # Redireciona para a página inicial se não estiver logado

@app.route('/api/logout')
def logout():
    """Endpoint para deslogar o usuário, limpando a sessão."""
    session.pop('google_id', None)
    session.pop('email', None)
    session.pop('name', None)
    session.pop('logged_in', None)
    print("Usuário deslogado com sucesso.")
    return jsonify({"message": "Logout bem-sucedido!"}), 200

# --- Execução do Servidor Flask ---
if __name__ == '__main__':
    # Para desenvolvimento, rode o Flask em modo debug.
    # NUNCA use debug=True em produção! Isso expõe informações sensíveis.
    # host='0.0.0.0' permite que o servidor seja acessível de qualquer IP na sua rede.
    # host='127.0.0.1' ou 'localhost' restringe o acesso apenas à sua máquina.
    app.run(debug=True, host='127.0.0.1', port=5000)