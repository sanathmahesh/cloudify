import asyncio
import shlex
import re
import sys
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]


class MigrationRequest(BaseModel):
    args: str


@dataclass
class MigrationProcess:
    process: Optional[asyncio.subprocess.Process] = None
    logs: Deque[str] = field(default_factory=lambda: deque(maxlen=2000))
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    returncode: Optional[int] = None


app = FastAPI(title="Cloudify Web Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)

_migrations: Dict[str, MigrationProcess] = {}


def _format_line(line: str, stream: str) -> str:
    prefix = "STDOUT" if stream == "stdout" else "STDERR"
    return f"[{prefix}] {line.rstrip()}"


async def _read_stream(
    stream: asyncio.StreamReader, migration: MigrationProcess, stream_name: str
) -> None:
    while True:
        line = await stream.readline()
        if not line:
            break
        text = _format_line(line.decode(errors="replace"), stream_name)
        migration.logs.append(text)
        await migration.queue.put(text)


async def _run_migration(migration_id: str, args: str) -> None:
    migration = _migrations[migration_id]
    cmd = [sys.executable, "migration_orchestrator.py", "migrate"]
    if args.strip():
        normalized = re.sub(r"\\\\\\s*\\n", " ", args)
        normalized = re.sub(r"\\s*\\n\\s*", " ", normalized)
        normalized = normalized.replace("\\n", " ")
        tokens = [t.strip() for t in shlex.split(normalized) if t != "\\"]
        tokens = [t for t in tokens if t]

        # If user pasted the full command, drop the leading parts up to "migrate".
        if "migrate" in tokens:
            migrate_index = tokens.index("migrate")
            tokens = tokens[migrate_index + 1 :]

        cmd.extend(tokens)
        await migration.queue.put(f"[SYSTEM] Parsed args: {tokens}")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(REPO_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    migration.process = process
    await migration.queue.put(f"[SYSTEM] Running: {' '.join(cmd)}")

    await asyncio.gather(
        _read_stream(process.stdout, migration, "stdout"),
        _read_stream(process.stderr, migration, "stderr"),
    )

    migration.returncode = await process.wait()
    await migration.queue.put(f"[SYSTEM] Process exited with code {migration.returncode}")
    await migration.queue.put("[SYSTEM] EOF")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/migrations")
async def start_migration(payload: MigrationRequest) -> dict:
    migration_id = str(uuid.uuid4())
    _migrations[migration_id] = MigrationProcess()
    asyncio.create_task(_run_migration(migration_id, payload.args))
    return {"id": migration_id}


@app.get("/api/migrations/{migration_id}")
async def migration_status(migration_id: str) -> dict:
    migration = _migrations.get(migration_id)
    if not migration:
        raise HTTPException(status_code=404, detail="Migration not found")

    return {
        "id": migration_id,
        "returncode": migration.returncode,
        "running": migration.returncode is None,
    }


@app.get("/api/migrations/{migration_id}/stream")
async def stream_logs(migration_id: str) -> StreamingResponse:
    migration = _migrations.get(migration_id)
    if not migration:
        raise HTTPException(status_code=404, detail="Migration not found")

    async def event_generator():
        for line in migration.logs:
            yield f"data: {line}\n\n"

        while True:
            line = await migration.queue.get()
            yield f"data: {line}\n\n"
            if line == "[SYSTEM] EOF":
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")
