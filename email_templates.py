# backend/email_templates.py
from typing import Optional, List # <-- ESTA LINHA FOI ADICIONADA PARA RESOLVER O NAMERROR

def get_monitoring_active_email_html(user_full_name: str, monitoring_type: str, official_gazette_link: str, edital_identifier: str, candidate_name: Optional[str] = None, keywords: str = "") -> str:
    """
    Retorna o HTML para o e-mail de 'Monitoramento Ativo'.
    """
    candidate_section = ""
    if monitoring_type == "personal" and candidate_name:
        candidate_section = f"""
            <tr>
                <td align="left" style="font-family: Arial, sans-serif; font-size: 14px; line-height: 20px; color: #555555; padding-bottom: 5px;">
                    <strong>Candidato(a):</strong>
                </td>
            </tr>
            <tr>
                <td align="left" style="font-family: Arial, sans-serif; font-size: 16px; line-height: 24px; color: #333333; padding-bottom: 15px;">
                    {candidate_name}
                </td>
            </tr>
        """

    keywords_section = ""
    if keywords:
        keywords_section = f"""
            <tr>
                <td align="left" style="font-family: Arial, sans-serif; font-size: 14px; line-height: 20px; color: #555555; padding-bottom: 5px;">
                    <strong>Palavras-chaves monitoradas:</strong>
                </td>
            </tr>
            <tr>
                <td align="left" style="font-family: Arial, sans-serif; font-size: 16px; line-height: 24px; color: #333333; padding-bottom: 15px;">
                    {keywords}
                </td>
            </tr>
        """

    return f"""
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
         <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
        <title>Monitoramento Ativo - Conecta Edital</title>
        <style type="text/css">
            body {{margin: 0; padding: 0;}}
            table {{border-collapse: collapse;}}
            .main-table {{width: 100%; max-width: 600px; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);}}
            .header-banner {{background: linear-gradient(135deg, #105afa, #001f85); color: #ffffff; font-family: Arial, sans-serif; font-size: 24px; font-weight: bold; padding: 20px 0; text-align: center; border-radius: 8px 8px 0 0;}}
            .content-area {{padding: 20px 30px; font-family: Arial, sans-serif; color: #333333;}}
            .logo-container {{text-align: center; padding: 20px 0;}}
            .logo {{max-width: 150px;}}
            .greeting {{font-size: 18px; font-weight: bold; margin-bottom: 10px;}}
            .subtitle {{font-size: 16px; line-height: 24px; margin-bottom: 20px;}}
            .details-box {{background-color: #f8f8f8; border: 1px solid #eeeeee; border-radius: 8px; padding: 20px; margin-bottom: 25px;}}
            .details-box p {{margin: 0 0 10px 0;}}
            .details-box a {{color: #007bff; text-decoration: none; font-weight: bold;}}
            .details-box a:hover {{text-decoration: underline;}}
            .info-text {{font-size: 16px; line-height: 24px; margin-bottom: 30px;}}
            .footer-section {{background-color: #f1f1f1; padding: 20px 30px; border-radius: 0 0 8px 8px;}}
            .footer-text {{font-size: 14px; color: #777777; text-align: center;}}
            .support-buttons {{display: flex; justify-content: center; gap: 15px; margin-top: 20px;}}
            .support-button {{background-color: #28a745; color: #ffffff; text-decoration: none; padding: 10px 15px; border-radius: 5px; font-size: 14px; font-weight: bold;}}
            .support-button.email {{background-color: #007bff;}}
            .support-button:hover {{opacity: 0.9;}}
            .important-note {{font-size: 14px; color: #888888; text-align: center; margin-top: 20px;}}
            .email-tag {{background-color: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 5px; font-size: 0.8em; font-weight: bold;}}
            @media (prefers-color-scheme: dark) {{body{{backgound-color: white}}}}
              .logo-container{{background-color:white}}
            
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
            <tr>
                <td style="padding: 20px 0 30px 0;">
                    <table class="main-table" align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="border-collapse: collapse;">
                        <tr>
                            <td class="logo-container"  style="background-color: white;">
                               <img src="https://i.ibb.co/vvDLtC6P/logo-png.png" alt="Conecta Edital Logo" class="logo" style="display: block; margin: 0 auto; max-width: 150px; height: auto;">
                            </td>
                        </tr>
                        <tr>
                            <td align="center" bgcolor="#007bff" class="header-banner" style="border-radius: 8px 8px 0 0;">
                                MONITORAMENTO ATIVO
                            </td>
                        </tr>
                        <tr>
                            <td class="content-area">
                                <p class="greeting">Olá, {user_full_name}!</p>
                                <p class="subtitle">Perfeito! Agora você conta com nosso sistema para monitorar todas as atualizações de forma automatizada.</p>
                                
                                <table border="0" cellpadding="0" cellspacing="0" width="100%" class="details-box">
                                    <tr>
                                        <td align="left" style="font-family: Arial, sans-serif; font-size: 14px; line-height: 20px; color: #555555; padding-bottom: 5px;">
                                            <strong>Diário oficial monitorado:</strong>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="left" style="font-family: Arial, sans-serif; font-size: 16px; line-height: 24px; color: #333333; padding-bottom: 15px;">
                                            <a href="{official_gazette_link}" target="_blank">{official_gazette_link}</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="left" style="font-family: Arial, sans-serif; font-size: 14px; line-height: 20px; color: #555555; padding-bottom: 5px;">
                                            <strong>ID do Edital / Concurso:</strong>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="left" style="font-family: Arial, sans-serif; font-size: 16px; line-height: 24px; color: #333333; padding-bottom: 15px;">
                                            {edital_identifier}
                                        </td>
                                    </tr>
                                    {candidate_section}
                                    {keywords_section}
                                </table>

                                <p class="info-text">Você não precisa fazer mais nada. A partir de agora, enviaremos notificações por e-mail sempre que encontrarmos novidades sobre seu concurso.</p>

                                <p class="footer-text" style="font-weight: bold; margin-bottom: 10px;">Precisa de ajuda?</p>
                                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                    <tr>
                                        <td align="center" style="padding-bottom: 20px;">
                                            <table border="0" cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <td>
                                                        <a href="https://wa.me/55SEUNUMERO" target="_blank" style="background-color: #28a745; color: #ffffff; text-decoration: none; padding: 10px 15px; border-radius: 5px; font-size: 14px; font-weight: bold; margin-right: 10px;">
                                                            <span style="display:inline-block; vertical-align:middle; margin-right: 5px;">📞</span> Nos chame no WhatsApp
                                                        </a>
                                                    </td>
                                                    <td>
                                                        <a href="mailto:suporte@conectaedital.com" target="_blank" style="background-color: #007bff; color: #ffffff; text-decoration: none; padding: 10px 15px; border-radius: 5px; font-size: 14px; font-weight: bold;">
                                                            <span style="display:inline-block; vertical-align:middle; margin-right: 5px;">📧</span> Nos envie um E-mail
                                                        </a>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td bgcolor="#f1f1f1" style="padding: 20px 30px; border-radius: 0 0 8px 8px;">
                                <p class="footer-text">Este é um e-mail automático. Por favor, não responda.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

def get_occurrence_found_email_html(user_full_name: str, edital_identifier: str, official_gazette_link: str, found_keywords: List[str]) -> str:
    """
    Retorna o HTML para o e-mail de 'Ocorrência Encontrada - Parabéns!'.
    """
    keywords_display = ", ".join(found_keywords)

    return f"""
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>Parabéns! Nova Ocorrência Encontrada - Conecta Edital</title>
        <style type="text/css">
            body {{margin: 0; padding: 0;}}
            table {{border-collapse: collapse;}}
            .main-table {{width: 100%; max-width: 600px; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);}}
            .header-banner {{background: linear-gradient(135deg, #14d870, #00823c); color: #ffffff; font-family: Arial, sans-serif; font-size: 24px; font-weight: bold; padding: 20px 0; text-align: center; border-radius: 8px 8px 0 0;}}
            .content-area {{padding: 20px 30px; font-family: Arial, sans-serif; color: #333333;}}
            .logo-container {{text-align: center; padding: 20px 0;}}
            .logo {{max-width: 150px;}}
            .greeting {{font-size: 18px; font-weight: bold; margin-bottom: 10px;}}
            .subtitle {{font-size: 16px; line-height: 24px; margin-bottom: 20px;}}
            .keyword-tag {{background-color: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 5px; font-size: 0.9em; font-weight: bold; display: inline-block; margin: 0 5px 5px 0;}}
            .access-button {{background-color: #28a745; color: #ffffff; text-decoration: none; padding: 12px 25px; border-radius: 8px; font-size: 18px; font-weight: bold; display: inline-block; margin-top: 20px;}}
            .access-button:hover {{opacity: 0.9;}}
            .footer-text {{font-size: 14px; color: #777777; text-align: center; margin-top: 30px;}}
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
        <table border="0" cellpadding="0" cellspacing="0" width="100%">
            <tr>
                <td style="padding: 20px 0 30px 0;">
                    <table class="main-table" align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="border-collapse: collapse;">
                        <tr>
                            <td class="logo-container" style="background-color: white;">
                               <img src="https://i.ibb.co/vvDLtC6P/logo-png.png" alt="Conecta Edital Logo" class="logo" style="display: block; margin: 0 auto; max-width: 150px; height: auto;">
                            </td>
                        </tr>
                        <tr>
                            <td align="center" bgcolor="#28a745" class="header-banner" style="border-radius: 8px 8px 0 0;">
                                PARABÉNS! 🥳
                            </td>
                        </tr>
                        <tr>
                            <td class="content-area">
                                <p class="greeting">Olá, {user_full_name}!</p>
                                <p class="subtitle">Encontramos uma atualização relevante no seu monitoramento para o edital <strong>{edital_identifier}</strong>. Recomendamos que confira o quanto antes.</p>
                                
                                <p style="font-family: Arial, sans-serif; font-size: 14px; line-height: 20px; color: #555555; padding-bottom: 5px; text-align: center;">
                                    <strong>Palavras-chave monitoradas:</strong>
                                </p>
                                <p style="text-align: center; margin-bottom: 25px;">
                                    <span class="keyword-tag">{keywords_display}</span>
                                </p>

                                <p style="font-family: Arial, sans-serif; font-size: 16px; line-height: 24px; color: #333333; margin-bottom: 25px; text-align: center;">
                                    Quer todos os detalhes da ocorrência? Clique no botão abaixo:
                                </p>
                                <table border="0" cellpadding="0" cellspacing="0" width="100%">
                                    <tr>
                                        <td align="center">
                                            <a href="{official_gazette_link}" target="_blank" class="access-button" style="color: white">
                                                ACESSAR EDITAL
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td bgcolor="#f1f1f1" style="padding: 20px 30px; border-radius: 0 0 8px 8px;">
                                <p class="footer-text">Este é um e-mail automático. Por favor, não responda.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """