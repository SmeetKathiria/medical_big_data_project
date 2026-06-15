from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from dagster import Definitions, job, op

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"


def _run(context: Any, command: list[str], env: dict[str, str] | None = None) -> None:
    merged_env = {
        **os.environ,
        "PYTHONPATH": "pipeline",
        "CMS_MCD_LICENSE_ACCEPTED": os.getenv("CMS_MCD_LICENSE_ACCEPTED", "true"),
        **(env or {}),
    }
    context.log.info("Starting command: %s", " ".join(command))
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    pending = ""
    for chunk in iter(process.stdout.readline, ""):
        for line in (pending + chunk).replace("\r", "\n").split("\n"):
            clean = line.strip()
            if clean:
                context.log.info(clean)
        pending = "" if chunk.endswith(("\n", "\r")) else chunk
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)
    context.log.info("Finished command: %s", " ".join(command))


@op
def fetch_small_real_sources(context) -> str:
    _run(context, [
        str(PYTHON),
        "pipeline/jobs/00_fetch_small_sources.py",
        "--run-id",
        "local-real-small",
        "--cms-license-accepted",
    ])
    return "small_sources_ready"


@op
def run_small_real_spark_pipeline(context, _ready: str) -> str:
    _run(context, ["make", "local-pipeline-small-from-raw"])
    return "small_spark_ready"


@op
def index_small_real_rag(context, _ready: str) -> str:
    _run(context, ["make", "local-rag-index-small"])
    return "small_rag_indexed"


@job
def local_real_small_rag_job() -> None:
    index_small_real_rag(run_small_real_spark_pipeline(fetch_small_real_sources()))


@op
def prepare_local_representative_raw(context) -> str:
    _run(context, ["make", "local-representative-raw"], env={"CMS_MCD_LICENSE_ACCEPTED": "true"})
    return "local_representative_raw_ready"


@op
def run_local_representative_spark_pipeline(context, _ready: str) -> str:
    _run(context, ["make", "local-representative-pipeline"])
    return "local_representative_spark_ready"


@op
def index_local_representative_rag(context, _ready: str) -> str:
    _run(context, ["make", "local-representative-rag-index"])
    return "local_representative_rag_indexed"


@op
def evaluate_local_representative_rag(context) -> str:
    _run(context, ["make", "local-representative-rag-eval"])
    return "local_representative_rag_evaluated"


@op
def gate_local_representative_rag(context) -> str:
    _run(context, ["make", "local-representative-rag-eval-gate"])
    return "local_representative_rag_gate_checked"


@job
def local_representative_rag_job() -> None:
    index_local_representative_rag(
        run_local_representative_spark_pipeline(prepare_local_representative_raw())
    )


@job
def local_representative_rag_eval_job() -> None:
    evaluate_local_representative_rag()


@job
def local_representative_rag_eval_gate_job() -> None:
    gate_local_representative_rag()


defs = Definitions(jobs=[
    local_real_small_rag_job,
    local_representative_rag_job,
    local_representative_rag_eval_job,
    local_representative_rag_eval_gate_job,
])
