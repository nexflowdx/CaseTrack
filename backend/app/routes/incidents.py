import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.schemas.occurrence import OccurrenceRequest
from app.services.anonymization import anonymize, deanonymize, UnresolvedIdentifierError
from app.services.llm import revise_text
from app.services.auth import get_current_employee
import re
import hashlib
import os
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
    estudante: str
    turma: str
    data: str
    responsavel: str | None = None
    texto_final: str


class ApprovalResponse(BaseModel):
    ticket: str
    approved_at: str


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

    student_hash = hashlib.sha256((AUDIT_SALT + request.estudante).encode()).hexdigest()
    employee_label = current_employee.get("nome") or current_employee.get("email") or "desconhecido"
    approved_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"Aprovação registrada — aluno_hash={student_hash} turma={request.turma} "
        f"func={employee_label} em={approved_at}"
    )

    return ApprovalResponse(
        ticket=f"{request.turma}-{approved_at}",
        approved_at=approved_at
    )