# CaseTrack

Sistema de Registro Inteligente de Ocorrências Escolares — desenvolvido para a **EMEF Assad Abdala**.

Ajuda o funcionário a redigir, revisar e imprimir fichas de ocorrência escolar, usando IA para melhorar a redação do relato **sem expor dados pessoais de alunos, funcionários ou terceiros** a serviços de terceiro.

> Projeto real, em uso na escola (não é apenas um exercício de portfólio). Autorização de execução concedida pela direção da escola.

## Como funciona (visão geral)

```text
Funcionário preenche o formulário (Lovable/frontend)
        ↓
Backend (FastAPI) anonimiza nomes automaticamente (spaCy, local, sem lista fixa)
        ↓
Texto anonimizado é revisado por um LLM gratuito (nunca recebe nome real)
        ↓
Funcionário vê o diff (o que a IA mudou) e aprova ou edita
        ↓
Ficha em PDF é gerada, impressa e enviada por e-mail institucional
        ↓
Log mínimo de aprovação é gravado (sem conteúdo da ocorrência, hash salgado)
```

Login de funcionário é validado via o projeto **[Login API]** (JWT), sem duplicar lógica de autenticação.

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | HTML/CSS/JS simples (sem Lovable em produção — ver decisão no roadmap) |
| Backend | FastAPI (Python) |
| Anonimização | spaCy (`pt_core_news_md`), local, sem custo |
| LLM | provedor com camada gratuita (Gemini/Groq — decisão em `docs/`) |
| PDF | WeasyPrint ou ReportLab |
| Autenticação | JWT validado, emitido pelo projeto Login API |
| Infraestrutura | VPS existente (Nexflow DX), custo zero |

## Estrutura do repositório

```text
CaseTrack/
├── frontend/     # interface do formulário de ocorrência
├── backend/      # API FastAPI (anonimização, LLM, PDF, log, e-mail)
├── docs/         # roadmap, decisões técnicas, arquitetura
└── .gitignore
```

## Princípios do projeto (não negociáveis)

- **Custo de infraestrutura zero** — qualquer ferramenta usada precisa de camada gratuita suficiente para o uso real da escola.
- **Nenhum nome real vai para o LLM** — anonimização acontece localmente, antes de qualquer chamada externa.
- **Revisão humana é obrigatória** — a IA nunca aprova sozinha; o funcionário sempre vê o diff antes de aprovar.
- **Log mínimo e auditável** — sem guardar o conteúdo da ocorrência, só metadados suficientes para provar quem aprovou o quê e quando.

Detalhes completos de cada decisão, incluindo o que foi descartado e por quê, estão em [`docs/CaseTrack-Roadmap.md`](docs/CaseTrack-Roadmap.md).

## Status

Em desenvolvimento — Fase 1 (estrutura do repositório) concluída. Acompanhamento de fase em `docs/`.

---

*Projeto mantido por Eduardo Gonçalves Jr. — Nexflow DX.*
