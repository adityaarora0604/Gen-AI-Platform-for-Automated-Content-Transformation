"""Generation: orchestrates the full transform job. (Owner: Anishk)

Flow: validate request -> clean source -> understand -> generate each format -> validate -> store job.
Every format is generated independently from the same structured source representation.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from app import jobs_store
from app.ai_service import client
from app.ai_service.demo import demo_generate
from app.content_understanding.understand import understand
from app.ingestion.extractors import prepare_source_text
from app.prompt_templates.templates import OUTPUT_SPECS, build_generation_prompt
from app.schemas import (
    AppError,
    GenerationSettings,
    LANGUAGES,
    OBJECTIVES,
    OutputItem,
    STYLES,
    TONES,
    TransformRequest,
    TransformResponse,
)
from app.validation.validator import validate_output

log = logging.getLogger("generation")

DEMO_NOTICE = (
    "DEMO MODE is active: outputs are produced by simple rules from the source text, not by an AI model. "
    "Set LLM_PROVIDER=anthropic and an API key in backend/.env for real AI generation."
)


def validate_settings(settings: GenerationSettings) -> None:
    """Reject settings outside the supported options."""
    checks = [
        ("tone", settings.tone, TONES),
        ("language", settings.language, LANGUAGES),
        ("objective", settings.objective, OBJECTIVES),
        ("style", settings.style, STYLES),
    ]
    for name, value, allowed in checks:
        if value not in allowed:
            raise AppError(f"Invalid {name} '{value}'. Allowed values: {', '.join(allowed)}.", 422)
    if not settings.audience.strip() or len(settings.audience) > 100:
        raise AppError("Target audience must be between 1 and 100 characters.", 422)


def normalise_output_types(types: List[str]) -> List[str]:
    unique = []
    for t in types:
        if t not in OUTPUT_SPECS:
            raise AppError(f"Unknown output type '{t}'.", 422)
        if t not in unique:
            unique.append(t)
    if not unique:
        raise AppError("Select at least one output format.", 422)
    return unique


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def generate_one(output_type: str, rep: dict, source_text: str, settings: dict) -> OutputItem:
    """Generate and validate one format. Never raises: failures are reported in the item."""
    label = OUTPUT_SPECS[output_type]["label"]
    try:
        if client.is_demo():
            content = demo_generate(output_type, rep, settings)
        else:
            system, user = build_generation_prompt(output_type, rep, settings)
            content = _strip_fences(client.complete(system, user))
        if not content.strip():
            raise client.LLMError("The AI returned an empty output.", 502, False)
    except AppError as e:
        return OutputItem(type=output_type, label=label, status="failed", error=e.message)
    except Exception:  # unexpected bug: report without leaking details or source text
        log.exception("Unexpected error generating %s", output_type)
        return OutputItem(type=output_type, label=label, status="failed", error="Unexpected error while generating this format.")
    warnings = validate_output(output_type, content, source_text)
    return OutputItem(type=output_type, label=label, content=content, validation_warnings=warnings)


def generate_outputs(rep: dict, source_text: str, output_types: List[str], settings: dict) -> List[OutputItem]:
    with ThreadPoolExecutor(max_workers=min(3, len(output_types))) as pool:
        futures = [pool.submit(generate_one, t, rep, source_text, settings) for t in output_types]
        return [f.result() for f in futures]


def run_transform(req: TransformRequest) -> TransformResponse:
    """Run a complete transformation job and persist its result."""
    started = time.time()
    validate_settings(req.settings)
    output_types = normalise_output_types(list(req.output_types))
    source_text, truncated = prepare_source_text(req.source_text)
    client.check_configuration()

    mode = "demo" if client.is_demo() else "ai"
    settings = req.settings.model_dump()
    job_id = jobs_store.new_job_id()
    jobs_store.create_job(job_id, mode, len(source_text), output_types, settings)

    warnings: List[str] = []
    if mode == "demo":
        warnings.append(DEMO_NOTICE)
    if truncated:
        warnings.append("The source was longer than the allowed limit and was truncated before processing.")

    try:
        rep_model, understand_warnings = understand(source_text)
        warnings += understand_warnings
        rep = rep_model.model_dump()
        outputs = generate_outputs(rep, source_text, output_types, settings)
    except AppError as e:
        jobs_store.complete_job(job_id, "failed", {"errors": [e.message]})
        raise
    except Exception:
        log.exception("Unexpected error in job %s", job_id)
        jobs_store.complete_job(job_id, "failed", {"errors": ["Unexpected error."]})
        raise AppError("An unexpected error occurred while processing the job.", 500)

    errors = [f"{o.label}: {o.error}" for o in outputs if o.status == "failed"]
    done = sum(1 for o in outputs if o.status == "completed")
    status = "completed" if done == len(outputs) else ("partial" if done else "failed")

    response = TransformResponse(
        job_id=job_id,
        status=status,
        mode=mode,
        source_representation=rep,
        outputs=outputs,
        errors=errors,
        warnings=warnings,
        metadata={
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(time.time() - started, 2),
            "provider": client.provider(),
            "model": client.model_name(),
            "source_chars": len(source_text),
            "truncated": truncated,
            "output_types": output_types,
            "settings": settings,
        },
    )
    jobs_store.complete_job(job_id, status, response.model_dump())
    return response
