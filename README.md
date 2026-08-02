# Veterinary Medical Records System

Lean MVP that helps veterinarians upload a pet medical-record **PDF or Word document (.docx)**, extract text, structure it with a **local LLM** (Ollama), and review/edit the result in a React UI.

Built with **Spec-Driven Development**. Living specs live in [`specs/`](./specs/).

## Stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI |
| Document text | pdfplumber (PDF), python-docx (.docx) |
| Structuring | Ollama structured outputs + `qwen2.5:7b` |
| Persistence | SQLite + filesystem |
| Packaging | Docker Compose |

## Quick start (Docker)

### 1. Install and start Ollama (host)

```bash
# macOS: https://ollama.com/download
ollama pull qwen2.5:7b
ollama serve   # if not already running
```

### 2. Run the app

```bash
docker compose up --build
```

- UI: http://localhost:3000  
- API: http://localhost:8000/api/health  
- Sample PDF: [`backend/fixtures/sample_vet_record.pdf`](./backend/fixtures/sample_vet_record.pdf)
- Sample Word: [`backend/fixtures/sample_vet_record.docx`](./backend/fixtures/sample_vet_record.docx) (.docx only; legacy .doc not supported)

### Fake LLM mode (no Ollama)

```bash
LLM_PROVIDER=fake docker compose up --build
```

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p ../data/uploads
export LLM_PROVIDER=fake   # or ollama with Ollama running
uvicorn app.main:app --reload --port 8000
```

Tests:

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

## API overview

See [`specs/api.md`](./specs/api.md).

- `POST /api/records` — upload PDF or Word (.docx)
- `GET /api/records` — list
- `GET /api/records/{id}` — detail
- `PATCH /api/records/{id}` — save edited structured data
- `GET /api/records/{id}/file` — download original file

## Spec-Driven Development

1. [`specs/problem.md`](./specs/problem.md)  
2. [`specs/scope.md`](./specs/scope.md)  
3. [`specs/data-model.md`](./specs/data-model.md)  
4. [`specs/api.md`](./specs/api.md)  
5. [`specs/acceptance.md`](./specs/acceptance.md)  
6. [`specs/architecture.md`](./specs/architecture.md)  
7. [`specs/tasks.md`](./specs/tasks.md)

Architecture notes and ADRs: [`docs/`](./docs/).

## Performance notes

- Default `PROCESSING_MODE=async` avoids gateway timeouts: upload returns immediately; the UI polls and shows progressive section loading with percent/step feedback until the clinical summary is ready.
- Use the header **English / Español** toggle to change site UI language (labels, dates, processing messages). This does not change extracted data or clinical summary language; `meta.source_language` shows the document language.
- Default `LLM_CLINICAL_MODE=hybrid`: for multi-visit PDFs with strong historial hints, **clinical narrative** LLM is skipped but **clinical summary polish** may still run when Ollama is available; heuristic clinical summary is always generated. Weak-hint documents may call narrative LLM instead of polish.
- Demographics LLM is also skipped when header heuristics find `pet.name`.
- `LLM_CLINICAL_MODE=heuristic`: fastest — no clinical LLM calls; heuristic clinical summary only.
- If the LLM is used and times out, the record still completes with heuristic data (no hard failure).
- Optional smaller model: `OLLAMA_MODEL=llama3.2:3b`.

## Future improvements

See [`docs/future-improvements.md`](./docs/future-improvements.md).
