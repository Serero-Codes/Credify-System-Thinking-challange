# SkillProof

SkillProof organises evidence from a public GitHub repository into a transparent
report for human review. It does not certify skills, rank candidates, or make
hiring decisions.

## Project layout

```text
app.py                  Flask API entry point
core/                   Configuration, request validation, skill catalogue
services/               GitHub client, evidence rules, report builder
tests/                  Mocked API, service, analyzer, and validation tests
frontend/               React + Vite browser application
SkillProof_*.docx       Project documentation
SkillProof_*.pptx       Presentation deck
```

## Run locally

Start the Flask API from this directory:

```powershell
python -m pip install -r requirements.txt
python app.py
```

In another terminal:

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The Vite development
server proxies `/api` requests to `http://127.0.0.1:5000`. For a separately
hosted frontend, set `VITE_API_BASE_URL` to the backend origin and configure
`CORS_ORIGINS` on the backend.

Useful backend settings are `GITHUB_API_TIMEOUT`, `INSPECTION_BUDGET_SECONDS`,
`MAX_FILES_TO_INSPECT`, `MAX_FILE_SIZE_BYTES`, `MAX_SKILLS_PER_REQUEST`, and
`CORS_ORIGINS`.

## Validation run

- `python -m pytest tests -q` — 84 passed.
- `cd frontend; npm run build` — production build succeeded.
- Generated PDF smoke check — valid PDF output includes repository metadata,
  inspection coverage, outcomes, linked evidence, next steps, and limitations.
- Local smoke check — health endpoint returned `ok`; the catalogue returned 17
  skills with a maximum selection of 8; the browser loaded the catalogue,
  sample report, and mobile layout.
- No live GitHub repository analysis was run; repository/API behavior is
  covered by mocked tests.

## API

- `GET /api/health` — service health.
- `GET /api/skills` — backend-maintained skills and the selection limit.
- `POST /api/analyze` — `{ "repository_url": "https://github.com/owner/repo", "skills": ["python"] }`.

Analysis reports can be downloaded from the results view as a PDF. The export
includes repository metadata, inspection coverage, selected skills and their
statuses, linked evidence, explanations, next steps, and limitations. Sample
reports are labelled as illustrative in both the UI and downloaded PDF.
The results dashboard visualizes bounded file-inspection stages, selected-skill
outcomes, linked evidence counts, and the directories containing linked source
files. These charts describe the available report data, not a complete file
inventory, a skill score, or a measure of a person's ability.

Analysis accepts only HTTPS `github.com` repository URLs. It fetches repository
metadata, selects eligible text files under file, size, and time limits, and
uses deterministic patterns without executing repository code. The report
links detected evidence to the source file and distinguishes incomplete
inspection from a completed scan with no recognised pattern.

## Documentation and implementation check

| Documented capability | Implementation |
| --- | --- |
| Public GitHub URL and server-side validation | `core/validation.py`, `POST /api/analyze` |
| Backend-owned skills and 1–8 selection | `core/skills_catalogue.py`, `GET /api/skills` |
| Bounded, safe repository inspection | `services/github_service.py`, configurable file/size/time limits, no redirects |
| Deterministic evidence rules and source links | `services/evidence_analyzer.py` |
| Incomplete vs. not-found outcomes | Analyzer status handling and inspection coverage metadata |
| Loading, error, success, and sample states | React application in `frontend/src/` |
| Health endpoint and mocked backend tests | `GET /api/health`, `tests/` |
| Visible limitations and human review | Frontend report and project documentation |

The delivered React + Vite frontend is reflected in the project documentation
and pitch-deck technology summary. Its workflow, report content, and safeguards
follow the project's stated requirements and presentation. The demonstration
report is explicitly labelled as illustrative fixture data and is never
substituted for a failed live analysis.
