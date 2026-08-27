# CaseTrack: Intelligent School Incident Report System — Revised Roadmap (v2)

## Premises of this revision

This roadmap fixes four points identified in the previous version:

1. **LGPD (Brazilian data protection law)** — data from an underage student cannot be sent to a third-party LLM API without anonymization.
2. **Minimal log** — even without a permanent database, there needs to be an auditable record of who approved what and when.
3. **Review diff** — the staff member needs to see what the AI changed, not just the final text.
4. **Zero cost** — every tool used, from start to finish, needs a free tier sufficient for the school's real usage volume.

**Update (08/26/2026):** this version incorporates additional decisions on the anonymization technique (Phase 0/Phase 5), the infrastructure choice (Phase 4/22), and process isolation on the VPS (Phase 5), defined in conversation after the first revision.

---

# PART 1 — REAL PROJECT

## Phase 0 — Problem definition, scope, and constraints

Beyond the original scope (helping draft and print the incident report, without turning into a full school management system), this phase now includes two formal constraints:

### Privacy constraint (LGPD)

No proper name — of a student, staff member, teacher, or any person mentioned in the report — may be sent to the LLM provider. This applies not only to the "student" field on the screen, but to **any name that appears within the free-text body of the report**.

**Technical decision (updated):** the approach initially considered — swapping names using a reference list (class roster/staff registry) — was discarded. It's unfeasible to maintain because students enter and leave the school constantly, and it doesn't cover third-party names mentioned in the report (teachers, inspectors, parents).

Instead, anonymization uses **automatic proper-name recognition, without depending on any pre-registered list**, via **spaCy** (`pt_core_news_md`), running **locally on the backend** — never a network call, never a third-party AI performing this step.

**Masking rule (aggressive by design):** mask any token classified as:

- **NER `PER`** (person-type entity), OR
- **POS tagging `PROPN`** (proper noun, even without certainty whether it's a person, place, or institution).

Over-masking (e.g., a street name, "EMEF Assad Abdala") is acceptable; letting a child's name slip through is not. The human review in Phase 6 is the layer that corrects false positives before final approval.

Correct flow (the order is mandatory):

```text
Original report (real names, still on the backend, never leaves the process)
        ↓
spaCy (pt_core_news_md) runs LOCALLY — detects PER + PROPN
        ↓
Each name/entity becomes an identifier (Person A, Person B...)
The substitution map exists only in memory, per request, and is discarded afterward
        ↓
Text with identifiers is sent to the LLM (never the original text)
        ↓
LLM reviews the text (never saw the real name)
        ↓
Response comes back still with identifiers
        ↓
Backend swaps identifiers back for real names, using the in-memory map
        ↓
Staff member sees the final text (with real names) in the Phase 6 diff
```

**Mistake to never make:** anonymizing after calling the LLM, or letting "the AI fix the names" before anonymizing. The LLM must never receive text with real names under any circumstance — this would violate this constraint even if it seems like a reasonable simplification.

**Acknowledged limitation (document it, don't hide it):** NER + POS drastically reduces name leakage, but doesn't guarantee 100% — unusual nicknames, typos outside the model's training pattern, or names in ambiguous context can escape automatic detection. The system's real guarantee lies in the combination "automatic anonymization (best-effort) + mandatory human review," not in anonymization alone.

It's also established: no log, no temporary file, and no error message may contain the real name of the student (or of any person mentioned) together with the incident content in plain text persisted beyond what's needed to generate the session's PDF.

### Cost constraint

The entire project must run at **zero infrastructure cost**, using exclusively free tiers:

| Component | Free choice |
|---|---|
| Frontend | Lovable (free plan) |
| Backend | FastAPI, self-hosted on the VPS already paid for Nexflow DX |
| Name anonymization | spaCy (`pt_core_news_md`), local, no cost, no network call |
| Database (if needed) | PostgreSQL on the same VPS (already provisioned) |
| LLM | API with a free tier (e.g., Gemini API free tier or Groq free tier) — **decide in Phase 4**, never a per-token paid provider without a sufficient free tier |
| PDF generation | free Python library (e.g., WeasyPrint or ReportLab) |
| Version control | GitHub (free for a public repo or personal private repo) |

**Decision on cloud (AWS/Azure/GCP):** evaluated as an infrastructure alternative for the real version and discarded.

- AWS and Azure: free VM tiers expire after 12 months and start auto-charging the registered card — contrary to the permanent zero-cost criterion.
- GCP: has an `e2-micro` "Always Free" VM with no expiration (the only one of the three with this property), but still requires a credit card at signup and is only free in US regions (`us-west1`, `us-central1`, `us-east1`), which would add latency for use in Brazil without real need, since the current VPS is already sufficient and already paid for independently of this project.
- **Final decision:** the real version (Part 1) remains entirely on the existing VPS. GCP is used only as a learning environment in Part 2 (see Phase 22).

This table should be revisited whenever a new dependency is added in any phase.

---

## Phase 1 — Repository and organization

No content change from the previous plan: `frontend/`, `backend/`, `docs/` structure, descriptive commits.

Add a "Privacy and cost" section to `docs/architecture.md`, documenting the Phase 0 constraints (including the spaCy anonymization technique and the cloud decision).

---

## Phase 2 — Interface (Lovable)

No change. When setting up the project in Lovable, confirm the plan used is within the free tier before proceeding.

---

## Phase 3 — Incident report form

No change to the fields (student, class, date, guardian, report). The "student" field remains normally visible on screen — anonymization happens on the backend, not the interface.

---

## Phase 4 — Choosing and configuring the LLM provider (free)

Selection criteria:

* has a free tier with a request limit sufficient for the school's real volume (a few incidents per day);
* supports calls via a simple API (REST);
* doesn't require a credit card for the free tier, if possible.

Candidates to evaluate: Gemini API (free tier), Groq (free tier), or an open model running locally on the VPS itself via Ollama (zero additional cost, but consumes resources on the server you already own).

Document in `docs/phase-04-llm-choice.md` which one was chosen and why. Document alongside it the cloud infrastructure decision (AWS/Azure discarded; GCP reserved only for Part 2 — see Phase 0).

---

## Phase 5 — Backend with FastAPI

Same structure as before:

```text
backend/
├── app/
│   ├── main.py
│   ├── routes/
│   │   └── incidents.py
│   ├── schemas/
│   │   └── incident.py
│   ├── services/
│   │   ├── anonymization.py
│   │   ├── llm.py
│   │   ├── pdf.py
│   │   └── approval_log.py
│   └── config.py
└── tests/
```

`anonymization.py` (updated): uses spaCy (`pt_core_news_md`) to detect `PER` + `PROPN` in the report text, generates a name↔identifier map in memory (per request, discarded after use), and performs the swap in both directions — never relying on a class roster or staff registry.

`approval_log.py`: writes the Phase 6 minimal log.

Initial endpoint:

```text
POST /incidents/review
```

Flow:

```text
Lovable
   ↓
FastAPI
   ↓
Data validation
   ↓
Anonymization (local spaCy: PER + PROPN → identifiers)
   ↓
LLM (only with identifiers, never real names)
   ↓
Reviewed text (still with identifiers)
   ↓
Swap identifiers back for real names (in-memory map)
   ↓
Return to frontend
```

### VPS isolation (defined in this revision)

Since the real version shares the same VPS as other projects (Nexflow DX, Login API), this project's backend must run with:

- a dedicated Python `venv`, exclusive to this project (no shared dependencies with other projects on the same VPS);
- its own process via `systemd`, with a separate (non-root) system user and automatic restart;
- Docker is **not** a prerequisite here — it's reserved for Phase 20, in the study version.

---

## Phase 6 — Review, diff, and human approval

The staff member doesn't just see the final text — they see **what changed**.

```text
ORIGINAL TEXT (as the staff member wrote it)
┌─────────────────────────────────────┐
│ the student was running in the      │
│ hallway...                          │
└─────────────────────────────────────┘

REVIEWED TEXT (with changes highlighted)
┌─────────────────────────────────────┐
│ The student was observed running    │
│ through the hallway... [changes     │
│ highlighted]                        │
└─────────────────────────────────────┘

[ EDIT ]     [ APPROVE AND GENERATE FORM ]
```

The highlighting can be simple (e.g., a text-diff library generating HTML with `<mark>` around the changed parts) — it doesn't need to be sophisticated, just visible.

This step also acts as the final protection layer against a failure in automatic anonymization: if a name escapes spaCy's detection, this is where the staff member has a chance to notice before approving.

Upon approval, the backend writes the **minimal log**:

```json
{
  "timestamp": "2026-08-26T11:45:00-03:00",
  "staff_member": "staff identifier, not the student's name",
  "approved_text_hash": "sha256(salt + approved_text)",
  "class": "...",
  "incident_date": "..."
}
```

**Updated in this revision:** the hash is salted before being generated (`secrets.token_hex()` locally, zero cost) to mitigate a dictionary attack against short, predictable texts — without this, someone with access to the log could try guessing the content by hashing plausible candidates and comparing.

This log is a simple local file (e.g., a single-file SQLite database, or even an append-only `.jsonl`) — free, no additional server, and **does not store the incident content or the student's name**, only enough metadata to prove that an approval happened, when, and the hash of the final text.

---

## Phase 7 — PDF form

Same form template (EMEF Assad Abdala, fields, A4 frame). One point remains open for your decision, not automatically decided here: reassess whether a cursive font is the best choice for a formal document, given legibility — it may be worth using cursive only in the report field and a standard font for the fixed fields (name, class, date).

Generated via a free Python library (WeasyPrint or ReportLab).

---

## Phase 8 — Text length control

No change: a warning before generating the PDF if the text exceeds the available space, with no automatic truncation.

---

## Phase 9 — Printing

No change. End of the real flow, with no permanent storage of the incident content (only the Phase 6 minimal log).

---

## Phase 10 — Testing

Same coverage as before (form, LLM, PDF), plus:

* a test confirming that no proper name (student, staff member, or third party mentioned) appears in log entries or LLM API calls;
* a test confirming that the anonymization map (spaCy) is discarded after use and doesn't persist between requests;
* a test confirming that the diff correctly shows the changes;
* a test confirming that the approval log is written without the incident content and with the salted hash.

---

## Phase 11 — Real project documentation

Document in `docs/`: the problem, architecture, flow, privacy decision (anonymization via spaCy, with the limitation that it's not 100% guaranteed), minimal-log decision (salted hash), zero-cost decision (including why AWS/Azure/GCP were discarded for the real version), limitations.

---

# PART 2 — STUDY AND PORTFOLIO PROJECT

Same logic as before — evolving the same base for learning — with one central difference: since you already have the **Login API** project covering basic authentication (email/password + JWT), this part only justifies itself as a separate project if it focuses on what the Login API **doesn't** cover: RBAC with multiple roles, auditing, and integration with an external API (Google Drive). Avoid repeating the Login API's simple auth without adding this from the start.

## Phase 12 — Git/GitHub evolution

No change: branches, PRs, issues, releases.

## Phase 13 — PostgreSQL

No content change: `staff`, `students`, `incidents` entities. Confirm it runs on the same already-paid VPS (zero additional cost).

## Phase 14 — Authentication **with RBAC from the start**

Unlike the previous plan, don't implement simple login first "to add roles later." Build the user table already with a role field (`STAFF`, `COORDINATION`, `ADMINISTRATOR`) and route-based permission rules from the very first version of login. This is the point that truly differentiates this project from the Login API.

## Phase 15 — Incident history

No change: search, filtering, editing, reprinting.

## Phase 16 — Auditing

No content change (`created_at`, `approved_by`, `audit_logs`), but now connected to the same anonymization principle from Phase 0 — audit logs also don't store student or staff names in plain text unnecessarily.

## Phase 17 — LLM integration evolution

No change: structured prompts, structured output, response validation, tests checking whether the AI followed the rules (didn't invent, didn't alter names/dates).

## Phase 18 — Automated testing

No change.

## Phase 19 — CI with GitHub Actions

No change — GitHub Actions is free for a personal project's volume.

## Phase 20 — Docker

No change.

## Phase 21 — Backup and Google Drive

No content change. Confirm that Google Drive API usage stays within the free quota (15GB) for the real backup volume.

## Phase 22 — CI/CD and deployment

Reuses the same VPS/EasyPanel already used for Nexflow DX and the Login API, at no additional cost.

**Added in this revision:** this phase also includes, as a parallel learning exercise (not replacing the main VPS), a demo deployment using Google Cloud Platform's "Always Free" `e2-micro` VM. Goal: learn to work with another cloud platform. Points of attention already mapped: requires a credit card at signup (even on the always-free tier), is only free in the `us-west1`, `us-central1`, and `us-east1` regions (US-based server), and has modest specs (2 shared vCPUs, ~1GB usable RAM, 30GB disk) — sufficient for study purposes.

## Phase 23 — Security

No content change (HTTPS, CORS, rate limiting, secrets, least privilege).

---

# Expected outcome

The real project solves the school's problem with automatic anonymization via spaCy (without depending on lists that would require constant maintenance), an auditable minimal log with a salted hash, a human-review diff as the final protection layer, and real zero cost on the already-existing VPS. The study project stops being a repeat of the Login API and instead specifically demonstrates multi-role RBAC, auditing, external API integration, and now alternative cloud deployment (GCP) as a learning exercise — which, together with the Login API, forms a more complete backend portfolio instead of redundant projects.

---

*Document updated on 08/26/2026, based on decisions about anonymization (local spaCy, no list), salted hash, infrastructure (GCP reserved for Part 2), and process isolation on the VPS (São Paulo time).*
