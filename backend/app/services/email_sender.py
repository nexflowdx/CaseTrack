"""
Envio do e-mail institucional pós-aprovação, com o PDF da ficha anexado,
para os três destinatários fixos (diretora, vice-diretora, coordenadora).

Usa smtplib da biblioteca padrão do Python — sem dependência nova, mantendo
o critério de custo zero do projeto.

Enquanto as variáveis de ambiente SMTP_* não estiverem configuradas, o envio
é deliberadamente pulado (não é um erro fatal): a geração do PDF continua
funcionando normalmente, e o chamador recebe um aviso claro de que o e-mail
não foi enviado, em vez de a requisição inteira falhar.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = os.environ.get("SMTP_PORT")
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

# Destinatários fixos (decisão do projeto: sempre os mesmos três).
FIXED_RECIPIENTS_ENV = os.environ.get("SMTP_RECIPIENTS", "")
FIXED_RECIPIENTS = [
    email.strip() for email in FIXED_RECIPIENTS_ENV.split(",") if email.strip()
]


def smtp_is_configured() -> bool:
    """Retorna True só se todas as variáveis necessárias estiverem presentes."""
    return bool(SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD and FIXED_RECIPIENTS)


def send_occurrence_email(ticket: str, student_name: str, pdf_bytes: bytes) -> None:
    """
    Envia o e-mail com o PDF anexado. Lança exceção se algo falhar durante
    o envio em si (falha de conexão SMTP, autenticação, etc.) — mas o
    chamador (rota da API) é responsável por decidir não quebrar a resposta
    HTTP por causa disso, já que o PDF já foi gerado com sucesso a essa altura.
    """
    if not smtp_is_configured():
        raise RuntimeError(
            "SMTP não configurado (SMTP_HOST/PORT/USER/PASSWORD/RECIPIENTS "
            "ausentes nas variáveis de ambiente) — e-mail não enviado."
        )

    msg = EmailMessage()
    msg["Subject"] = f"CaseTrack — Nova ocorrência registrada ({ticket})"
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(FIXED_RECIPIENTS)
    msg.set_content(
        "Uma nova ocorrência escolar foi registrada e aprovada no CaseTrack.\n\n"
        f"Registro nº: {ticket}\n"
        f"Estudante(s): {student_name}\n\n"
        "A ficha completa está anexada a este e-mail em formato PDF.\n\n"
        "Este é um e-mail automático — não é necessário responder."
    )

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"ocorrencia_{ticket}.pdf",
    )

    port = int(SMTP_PORT)
    with smtplib.SMTP(SMTP_HOST, port, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    logger.info(f"E-mail de ocorrência enviado — ticket={ticket} destinatarios={len(FIXED_RECIPIENTS)}")