import asyncio

import httpx

from app.config import GEMINI_API_KEY

GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]
GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

MAX_TENTATIVAS_POR_MODELO = 2
ESPERA_BASE_SEGUNDOS = 2

# ... (mantém LEGAL_CONTEXT, PROMPT_REVISAO_SIMPLES e PROMPT_FORMAL_JURIDICO como estão)

import re


def _remover_numeracao(texto: str) -> str:
    return re.sub(r"^\s*\d+\.\s*", "", texto, flags=re.MULTILINE)

async def _chamar_modelo(model: str, payload: dict) -> httpx.Response | None:
    url = GEMINI_URL_TEMPLATE.format(model=model)
    for tentativa in range(1, MAX_TENTATIVAS_POR_MODELO + 1):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{url}?key={GEMINI_API_KEY}", json=payload)

        if response.status_code in (503, 429):
            espera = ESPERA_BASE_SEGUNDOS * tentativa
            await asyncio.sleep(espera)
            continue

        return response

    return None


async def revise_text(texto: str, mode: str) -> str:
    if mode == "formal_juridico":
        prompt = PROMPT_FORMAL_JURIDICO.format(contexto=LEGAL_CONTEXT, texto=texto)
    else:
        prompt = PROMPT_REVISAO_SIMPLES.format(texto=texto)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"thinkingConfig": {"thinkingLevel": "low"}},
    }

    ultima_resposta = None
    for model in GEMINI_MODELS:
        resposta = await _chamar_modelo(model, payload)
        if resposta is None:
            continue
        if resposta.status_code == 200:
            data = resposta.json()
            texto_bruto = data["candidates"][0]["content"]["parts"][0]["text"]
            return _remover_numeracao(texto_bruto)
        ultima_resposta = resposta

    if ultima_resposta is not None:
        ultima_resposta.raise_for_status()

    raise RuntimeError("Todos os modelos do Gemini falharam ou estão indisponíveis no momento.")

with open("app/resources/legal_context.txt", encoding="utf-8") as f:
    LEGAL_CONTEXT = f.read()

PROMPT_REVISAO_SIMPLES = """Revise a ocorrência escolar estruturada a seguir, campo por campo.
Corrija apenas erros de gramática, ortografia e clareza dentro de cada campo.
Não altere fatos, não adicione informações, não mude o tom, e não mova conteúdo de um campo
para outro.
Não remova nem altere nenhum identificador no formato "Pessoa X" — eles devem permanecer
exatamente como estão no texto original.
Mantenha a mesma numeração e os mesmos rótulos de campo do texto original.
Retorne apenas o texto revisado, sem comentários adicionais.

OCORRÊNCIA ESTRUTURADA:
{texto}
"""

PROMPT_FORMAL_JURIDICO = """Reescreva a ocorrência escolar estruturada abaixo no formato de
ficha oficial, seguindo o padrão de escrita objetivo e formal usado em fichas do sistema SGP
da prefeitura — mas isso é só uma referência de tom e estrutura. NUNCA escreva "SGP",
"Sistema SGP" ou qualquer nome de sistema no texto gerado; o documento não pertence a nenhum
sistema específico. O título do documento deve ser exatamente:

FICHA DE REGISTRO DE OCORRÊNCIA ESCOLAR

A ocorrência já vem estruturada em campos numerados (Data, Horário, Local, Estudantes
envolvidos, Servidores envolvidos, Descrição dos fatos, Condutas do ATE, Comunicações
realizadas, e opcionalmente Resultado e Observações). MANTENHA essa mesma separação de campos
na ficha final, cada um em sua própria seção — não misture o conteúdo de um campo dentro de
outro. Por exemplo, não descreva a conduta do ATE dentro da seção de "Descrição dos fatos", e
não descreva os fatos dentro da seção de "Condutas adotadas".

O relato é escrito em primeira pessoa pelo próprio autor, que exerce o cargo de ATE (Auxiliar
Técnico de Educação). Se o campo "Descrição dos fatos" ou "Servidores envolvidos" indicar que
o autor foi alvo direto de algum fato (ex: "me bateu"), preserve essa relação exata — não
transforme o autor em um mero receptor de informação de terceiros.

Descreva a atuação do autor (ATE) com precisão dentro do que compete a esse cargo, sem ampliar
suas atribuições além do que é próprio da função. Ao mencionar colegas de outros cargos
(professor, AVE, coordenação, etc.), descreva a atuação deles com respeito, sem presumir
atribuições que não são do conhecimento do autor do relato.

Você pode mencionar que o registro está alinhado ao Projeto Político-Pedagógico e às normas
de convivência da unidade escolar, usando o contexto institucional abaixo apenas para guiar o
tom e o vocabulário. NÃO cite artigo, número de lei, número de decreto ou qualquer referência
jurídica específica no texto final — o contexto é só para orientação de estilo e escopo.

Não invente fatos além do que os campos contêm.
Se um campo não foi informado no original, omita-o completamente da ficha final — não escreva
"Não informado" nem invente conteúdo para campos ausentes.
Não remova nem altere nenhum identificador no formato "Pessoa X" — eles devem permanecer
exatamente como estão no texto original.
Retorne apenas o texto final, sem comentários adicionais.

CONTEXTO INSTITUCIONAL (não citar diretamente):
{contexto}

OCORRÊNCIA ESTRUTURADA (campos preenchidos pelo autor/ATE):
{texto}
"""