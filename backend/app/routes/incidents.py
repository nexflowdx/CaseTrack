import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.schemas.occurrence import OccurrenceRequest
from app.services.anonymization import anonymize, deanonymize, UnresolvedIdentifierError
from app.services.llm import revise_text
from app.services.auth import get_current_employee
from app.services.pdf_generator import generate_occurrence_pdf
from app.services.email_sender import send_occurrence_email, smtp_is_configured
from app.services.classroom_extractor import suggest_classroom
import re
import hashlib
import os
import base64
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incidents", tags=["incidents"])

AUDIT_SALT = os.environ.get("AUDIT_SALT")
if not AUDIT_SALT:
    raise RuntimeError("AUDIT_SALT não definido no .env — obrigatório para hash de auditoria.")


class OccurrenceResponse(BaseModel):
    revised_text: str
    has_unresolved_reference: bool
    warning: str | None = None


class ApprovalRequest(BaseModel):
    occurrence_date: str
    location: str
    texto_final: str


class ApprovalResponse(BaseModel):
    ticket: str
    approved_at: str


class ClassroomSuggestionRequest(BaseModel):
    students_involved: str


class ClassroomSuggestionResponse(BaseModel):
    suggested_classroom: str | None = None


class DocumentRequest(BaseModel):
    student_name: str
    classroom: str
    occurrence_date: str
    texto_final: str
    responsible_staff: str
    ticket: str


class DocumentResponse(BaseModel):
    pdf_base64: str
    email_sent: bool
    email_error: str | None = None


@router.post("/review", response_model=OccurrenceResponse)
async def review_incident(
    request: OccurrenceRequest,
    current_employee: dict = Depends(get_current_employee)  # Autenticação
):
    name_map = {}
    campos_anonimizados = []

    for rotulo, valor in request.fields():
        valor_anon, name_map = anonymize(valor, name_map)
        campos_anonimizados.append(f"{rotulo}: {valor_anon}")

    texto_anonimizado = "\n".join(campos_anonimizados)
    resultado_llm = await revise_text(texto_anonimizado, request.mode)

    if not resultado_llm or not resultado_llm.strip():
        raise HTTPException(status_code=500, detail="LLM retornou resposta vazia")

    try:
        resultado_final = deanonymize(resultado_llm, name_map)
        return OccurrenceResponse(
            revised_text=resultado_final,
            has_unresolved_reference=False,
            warning=None
        )
    except UnresolvedIdentifierError as e:
        texto_com_marcador = e.partial_text
        for identificador in e.unresolved:
            texto_com_marcador = re.sub(
                rf"\b{re.escape(identificador)}\b",
                f"[[REVISAR: identificador não resolvido — {identificador}]]",
                texto_com_marcador
            )
        logger.warning(f"Alucinação detectada: {e}")
        return OccurrenceResponse(
            revised_text=texto_com_marcador,
            has_unresolved_reference=True,
            warning="A IA gerou um identificador não mapeado. Revisão manual obrigatória."
        )


@router.post("/approve", response_model=ApprovalResponse)
async def approve_incident(
    request: ApprovalRequest,
    current_employee: dict = Depends(get_current_employee)
):
    if "[[REVISAR:" in request.texto_final:
        raise HTTPException(
            status_code=400,
            detail="O texto ainda contém identificador(es) não resolvido(s). Corrija antes de aprovar."
        )

    texto_hash = hashlib.sha256((AUDIT_SALT + request.texto_final).encode()).hexdigest()
    employee_label = current_employee.get("nome") or current_employee.get("email") or "desconhecido"
    approved_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"Aprovação registrada — hash_texto={texto_hash} local={request.location} "
        f"data_ocorrencia={request.occurrence_date} func={employee_label} em={approved_at}"
    )

    return ApprovalResponse(
        ticket=f"{request.location}-{approved_at}",
        approved_at=approved_at
    )


@router.post("/suggest-classroom", response_model=ClassroomSuggestionResponse)
async def suggest_classroom_endpoint(
    request: ClassroomSuggestionRequest,
    current_employee: dict = Depends(get_current_employee)
):
    return ClassroomSuggestionResponse(suggested_classroom=suggest_classroom(request.students_involved))


@router.post("/generate-document", response_model=DocumentResponse)
async def generate_document(
    request: DocumentRequest,
    current_employee: dict = Depends(get_current_employee)
):
    pdf_bytes = generate_occurrence_pdf(
        student_name=request.student_name,
        classroom=request.classroom,
        occurrence_date=request.occurrence_date,
        occurrence_text=request.texto_final,
        responsible_staff=request.responsible_staff,
    )

    email_sent = False
    email_error = None

    if smtp_is_configured():
        try:
            send_occurrence_email(
                ticket=request.ticket,
                student_name=request.student_name,
                pdf_bytes=pdf_bytes,
            )
            email_sent = True
        except Exception as e:
            logger.error(f"Falha ao enviar e-mail da ocorrência {request.ticket}: {e}")
            email_error = str(e)
    else:
        email_error = "SMTP não configurado — e-mail não enviado. O PDF foi gerado normalmente."
        logger.warning(f"Geração de PDF sem envio de e-mail (SMTP não configurado) — ticket={request.ticket}")

    return DocumentResponse(
        pdf_base64=base64.b64encode(pdf_bytes).decode("ascii"),
        email_sent=email_sent,
        email_error=email_error,
    )