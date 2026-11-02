# Architecture

## Pipeline

```
React UI ──HTTP──> FastAPI routes (api/routes.py)
                       │
         upload ───────┤──> ingestion.extract_text ──> preprocessing.clean_text
                       │
         transform ────┴──> generation.run_transform
                              1. validate settings + output types
                              2. ingestion.prepare_source_text (clean, length-limit)
                              3. content_understanding.understand ──> SourceRepresentation (JSON)
                              4. generation.generate_one × selected formats (parallel, independent)
                                    prompt_templates ─> ai_service.complete (or demo)
                                    validation.validate_output
                              5. jobs_store (SQLite) records status + result
                       │
         export ───────┴──> export.build_export (md / txt / json / docx)
```

## Design decisions

- **One structured representation feeds every format.** Step 3 turns the source into `summary, key_points, facts, entities, dates, important_figures, caveats, source_language`. Step 4 only sees this JSON (never the raw source), so formats are consistent with each other and are generated independently.
- **Grounding in two layers.** Prompts forbid unsupported facts and require "Not specified in the source." for gaps. In code, entities, dates and figures returned by the model are dropped if they cannot be found in the source text (`content_understanding.build_representation`), and generated outputs are scanned for figures that are absent from the source.
- **AI service isolation.** `ai_service/client.py` is the only file that talks to a provider. It reads credentials from environment variables, applies a timeout, retries rate-limit/timeout/5xx/empty responses with backoff (`LLM_MAX_RETRIES`), and maps provider errors to `LLMError` with a useful message and HTTP status. Adding another provider means adding one function next to `_call_anthropic` and one value in `SUPPORTED_PROVIDERS`.
- **Honest demo mode.** `ai_service/demo.py` extracts and templates text by rules, prefixes every output with a visible `[DEMO MODE ... NOT AI-generated]` banner, sets `mode: "demo"` on the job, and the UI shows a banner. It is never used implicitly: a missing API key in `anthropic` mode is an error, not a silent switch.
- **Partial success.** A failure in one format does not lose the others: the job returns `partial`, with a per-format error. A failure in source analysis fails the job.
- **Validation is advisory.** Findings are warnings shown next to the output. Checks: required sections/title, thread numbering and 280-character limit, hashtags, slide structure, empty output, numbers not found in the source, certainty wording ("confirmed") when the source is uncertain (negations such as "has not been verified" are ignored), severity stated without support in the source, and placeholder text.
- **Privacy.** The raw source is never persisted or logged; the job table stores settings, the structured representation and outputs. Uploaded files are parsed in memory and never written to disk or executed.
- **Simplicity.** SQLite (standard library), synchronous request handling, no queue, no auth: suitable for a laptop demo.

## Module interfaces (contracts between team members)

| Module | Public function | Input → Output |
|--------|-----------------|----------------|
| `ingestion.extractors` | `extract_text(filename, bytes)` | → `(clean_text, file_type, truncated)`; raises `AppError` |
| `ingestion.extractors` | `prepare_source_text(text)` | → `(clean_text, truncated)`; raises `AppError` |
| `preprocessing.cleaner` | `clean_text(str)`, `truncate_text(str, n)` | → `str`, `(str, bool)` |
| `content_understanding.understand` | `understand(source_text)` | → `(SourceRepresentation, warnings)` |
| `prompt_templates.templates` | `OUTPUT_SPECS`, `build_generation_prompt(type, rep_dict, settings_dict)`, `build_understanding_prompt(text)` | → `(system_prompt, user_prompt)` |
| `ai_service.client` | `complete(system, user)`, `check_configuration()`, `is_demo()` | → `str`; raises `LLMError` |
| `generation.generator` | `run_transform(TransformRequest)` | → `TransformResponse` |
| `validation.validator` | `validate_output(type, content, source_text)` | → `list[str]` warnings |
| `export.exporter` | `build_export(job_id, outputs, mode, fmt)` | → `(bytes, filename, media_type)` |

Shared types live in `schemas.py` (`SourceRepresentation`, `OutputItem`, `TransformRequest/Response`, `AppError`). `OUTPUT_SPECS` is the single source of truth for each format's structure, used by both prompts and validation. When Hardik changes a format, the validator follows automatically unless a new rule is needed.

## Frontend

`App.jsx` owns state (source text, selected formats, settings, result, edits). Components: `SourceInput` (paste + upload), `FormatSelector`, `SettingsPanel`, `ResultsPanel` (tabs, editable text, copy, per-format and bulk download, validation warnings, job metadata, source representation view). `api.js` is the only file that calls the backend. Edits are kept in the browser and sent to `POST /api/export` for bulk download.

## Out of scope (Phase 3 and stretch)

Image OCR, video transcription, RAG, video rendering, automatic social-media publishing, user accounts, job queues.
