# API contract

Base URL: `http://localhost:8000`. All routes are under `/api`. Interactive docs: `/docs`.
Errors are always `{"detail": "<message>"}` with the HTTP status below.

## Enumerations

| Field | Allowed values |
|-------|----------------|
| `output_types[]` | `executive_summary`, `linkedin`, `x_thread`, `advisory`, `presentation` |
| `settings.audience` | any text, 1-100 chars (UI offers: General public, Executives / leadership, Technical specialists, Government / policy makers, Media) |
| `settings.tone` | Professional, Formal, Neutral, Urgent, Friendly |
| `settings.language` | English, Hindi, Spanish, French, German |
| `settings.detail_level` | Low, Medium, High |
| `settings.objective` | Inform, Alert, Persuade, Educate, Recommend action |
| `settings.style` | Structured, Narrative, Concise, Analytical |

`GET /api/options` returns these lists for the UI.

## `GET /api/health`
```json
{"status":"ok","provider":"demo","mode":"demo","llm_configured":true,"max_upload_mb":10,"human_review_notice":"..."}
```
`mode` is `demo` or `ai`. `llm_configured` is false when `LLM_PROVIDER=anthropic` and no key is set.

## `POST /api/upload`
`multipart/form-data` with one field `file` (`.txt`, `.pdf`, `.docx`).
Response `200`:
```json
{"filename":"report.pdf","file_type":"pdf","char_count":4210,"text":"cleaned extracted text","truncated":false}
```
Errors: `400` empty/corrupt/invalid content, `413` too large, `415` unsupported type, `422` no readable text.

## `POST /api/transform`
Request:
```json
{
  "source_text": "Source content goes here",
  "output_types": ["executive_summary","linkedin","x_thread","advisory","presentation"],
  "settings": {"audience":"General public","tone":"Professional","language":"English",
               "detail_level":"Medium","objective":"Inform","style":"Structured"}
}
```
Response `200`:
```json
{
  "job_id": "3f9a1c2b7d10",
  "status": "completed",
  "mode": "ai",
  "source_representation": {"summary":"","key_points":[],"facts":[],"entities":[],"dates":[],
                            "important_figures":[],"caveats":[],"source_language":""},
  "outputs": [
    {"type":"executive_summary","label":"Executive Summary","content":"# ...",
     "validation_warnings":[],"status":"completed","error":null}
  ],
  "errors": [],
  "warnings": [],
  "metadata": {"created_at":"...","duration_seconds":8.4,"provider":"anthropic","model":"...",
               "source_chars":4210,"truncated":false,"output_types":["..."],"settings":{}},
  "human_review_notice": "AI-generated content may contain errors..."
}
```
- `status`: `completed` (all formats succeeded), `partial` (some failed; see `outputs[].error` and `errors`), `failed` (none succeeded).
- Each output keeps its own `validation_warnings`.
- `warnings` carries job-level notices (demo mode, truncation, items removed because they were not found in the source).

Errors: `400` empty/too short source, `422` invalid output type or settings, `429` provider rate limit, `502` provider error or malformed provider data, `503` missing API key, `504` provider timeout.
If the source analysis step fails, the whole request fails with an error and the job is recorded as `failed`.

## `GET /api/jobs/{job_id}`
Job status and metadata (no output text): `job_id, status (running|completed|partial|failed), mode, created_at, completed_at, source_chars, output_types, settings, errors, metadata`. `404` if unknown.

## `GET /api/jobs/{job_id}/outputs`
The full stored `TransformResponse` (same shape as the transform response). `404` unknown, `409` still running.

## `GET /api/jobs/{job_id}/export?format=md|txt|json|docx`
Downloads the job's completed outputs as a file (`Content-Disposition: attachment`). Default `md`. `400` unsupported format.

## `POST /api/export`
Exports outputs sent by the client, so **user edits are included**.
```json
{"job_id":"3f9a1c2b7d10","mode":"ai","format":"docx",
 "outputs":[{"type":"linkedin","label":"LinkedIn Post","content":"edited text"}]}
```
Returns the file. The frontend's "Download all" uses this route.

## Output structures (what the validator checks)

| Type | Required structure |
|------|--------------------|
| `executive_summary` | `# Title`, then `## Overview`, `## Key Findings`, `## Important Facts`, `## Conclusion` |
| `linkedin` | `## Hook`, `## Post`, `## Key Takeaways`, `## Hashtags` (at least one `#tag`), `## Call to Action` |
| `x_thread` | Lines `n/N text`, consecutive numbering, each post at most 280 characters including the prefix |
| `advisory` | `# Title`, `## Severity / Priority`, `## Background`, `## Key Observations`, `## Potential Impact`, `## Recommended Actions`, `## Caveats` |
| `presentation` | `# Title`, at least 3 `## Slide n: ...` blocks, each with bullets, `**Suggested visual:**`, `**Speaker notes:**` |

Section headings are always English so they can be validated; the text under them follows `settings.language`.
