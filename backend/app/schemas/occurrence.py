from typing import Literal, Optional

from pydantic import BaseModel

FIELD_LABELS = [
    ("1. Data", "occurrence_date"),
    ("2. Horário", "occurrence_time"),
    ("3. Local", "location"),
    ("4. Estudante(s) envolvido(s)", "students_involved"),
    ("5. Servidores envolvidos/presentes", "staff_involved"),
    ("6. Descrição objetiva e cronológica dos fatos", "facts_description"),
    ("7. Condutas adotadas pelo ATE", "ate_actions"),
    ("8. Comunicações realizadas", "communications_made"),
    ("9. Resultado/encerramento da ocorrência", "resolution"),
    ("10. Observações relevantes", "notes"),
    ("11. Identificação do servidor responsável", "responsible_staff"),
]


class OccurrenceRequest(BaseModel):
    mode: Literal["revisao_simples", "formal_juridico"]
    occurrence_date: str
    occurrence_time: str
    location: str
    students_involved: str
    staff_involved: str
    facts_description: str
    ate_actions: str
    communications_made: str
    resolution: Optional[str] = None
    notes: Optional[str] = None
    responsible_staff: str

    def fields(self) -> list[tuple[str, str]]:
        result = []
        for label, attr_name in FIELD_LABELS:
            value = getattr(self, attr_name)
            if value:
                result.append((label, value))
        return result

    def to_formatted_text(self) -> str:
        return "\n".join(f"{label}: {value}" for label, value in self.fields())