# Team guide: who owns what

Each member owns a folder and a small public interface (see the table in `ARCHITECTURE.md`). Work independently against those interfaces; the demo provider lets everyone run the whole app without an API key.

| Member | Role | Files | Interface you must keep stable | Test file(s) |
|--------|------|-------|-------------------------------|--------------|
| **Aditya** | Data Science: ingestion and preprocessing | `backend/app/ingestion/extractors.py`, `backend/app/preprocessing/cleaner.py` | `extract_text`, `prepare_source_text`, `clean_text`, `truncate_text`; raise `AppError(message, status)` for bad input | `tests/test_ingestion.py`, `tests/test_preprocessing.py` |
| **Aaditya** | Data Science: content understanding | `backend/app/content_understanding/understand.py` (and the demo extractor `ai_service/demo.py::demo_understand`) | `understand(text) -> (SourceRepresentation, warnings)`; never add facts that are not in the source | `tests/test_understanding.py` |
| **Hardik** | Data Science: schemas and prompts | `backend/app/prompt_templates/templates.py`, format parts of `backend/app/schemas.py` | `OUTPUT_SPECS`, `build_generation_prompt`, `build_understanding_prompt` | `tests/test_generation.py` (prompt tests) |
| **Shivam** | Data Science: validation and testing | `backend/app/validation/validator.py`, `backend/tests/`, `sample_data/` | `validate_output(type, content, source_text) -> list[str]` | `tests/test_validation_export_e2e.py` |
| **Rishabh** | Full stack | `frontend/`, `backend/app/api/routes.py`, `backend/app/main.py`, `backend/app/export/exporter.py`, `backend/app/jobs_store.py`, root docs | API contract in `docs/API.md`; `build_export` | `tests/test_api.py` |
| **Anishk** | AI & ML | `backend/app/ai_service/client.py`, `backend/app/generation/generator.py`, `backend/app/config.py` | `complete(system, user)`, `LLMError`, `run_transform` | `tests/test_generation.py` |

## Working rules

1. **Do not change a shared interface alone.** If you must change `schemas.py`, `OUTPUT_SPECS` or a function signature, tell the owners of the callers and update `docs/API.md`.
2. **Everyone develops in demo mode** (`LLM_PROVIDER=demo`). Only Anishk and Hardik need a real key to tune prompts; never commit it.
3. **Run `pytest` in `backend/` before every push.** Add tests for what you change in your own test file.
4. **Branches:** one per member (`feature/ingestion`, `feature/prompts`, ...), merge into `main` through pull requests reviewed by Rishabh (integration owner).

## Typical hand-offs

- Aditya improves PDF extraction → output goes straight into `understand()`; no other change needed.
- Hardik adds a section to the Advisory spec in `OUTPUT_SPECS` → Shivam's validator checks it automatically; Anishk's generator needs no change; update `demo.py::_advisory` so demo mode still passes validation.
- Anishk adds a second LLM provider → add a function next to `_call_anthropic`, add its name to `SUPPORTED_PROVIDERS`, add env vars to `.env.example`.
- Rishabh adds a field to the UI settings → add it to `GenerationSettings` (schemas), the prompt builder (Hardik) and `validate_settings` (Anishk).

## Suggested integration order

1. Rishabh + Anishk: run the app in demo mode end to end.
2. Aditya and Aaditya: improve extraction and understanding quality using `sample_data/`.
3. Hardik and Anishk: tune prompts with a real key on public sample text.
4. Shivam: grow the test dataset and tighten validation on real model output.
