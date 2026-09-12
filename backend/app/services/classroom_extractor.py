"""
Extração automática (best-effort) de identificador de turma a partir de
texto livre — ex: "Izaac 1B, João Kaleb 1B, Noah 1B" → sugestão "1B".

Isto é apenas uma SUGESTÃO. Por decisão do projeto, o valor extraído aqui
NUNCA deve ir direto para o PDF sem confirmação humana antes — o funcionário
sempre vê e pode corrigir esse valor na tela de confirmação de impressão.
"""

import re
from collections import Counter

# Padrões comuns de turma em escolas municipais de SP: "1A", "3B", "5º A",
# "1º ano A", etc. Mantido simples de propósito — é sugestão, não fonte de verdade.
CLASSROOM_PATTERN = re.compile(
    r"\b(\d{1,2})\s*[ºo°]?\s*([A-Za-z])\b"
)


def suggest_classroom(text: str) -> str | None:
    """
    Procura padrões de turma no texto e retorna o mais frequente.
    Retorna None se nada for encontrado (o campo fica em branco para
    preenchimento manual, em vez de arriscar um palpite ruim).
    """
    if not text:
        return None

    matches = CLASSROOM_PATTERN.findall(text)
    if not matches:
        return None

    normalized = [f"{numero}{letra.upper()}" for numero, letra in matches]
    most_common, count = Counter(normalized).most_common(1)[0]
    return most_common