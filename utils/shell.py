"""Shell command execution helpers with logging and error handling."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    command: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


def run_command(
    cmd: str,
    cwd: Optional[str] = None,
    timeout: int = 300,
    check: bool = False,
) -> CommandResult:
    """Run a shell command synchronously and return structured output."""
    log.info(f"[agent]Running:[/agent] {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        cr = CommandResult(
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
            command=cmd,
        )
        if not cr.success:
            log.warning(f"Command exited with code {cr.returncode}: {cr.stderr[:500]}")
        if check and not cr.success:
            raise subprocess.CalledProcessError(
                cr.returncode, cmd, cr.stdout, cr.stderr
            )
        return cr
    except subprocess.TimeoutExpired:
        log.error(f"Command timed out after {timeout}s: {cmd}")
        return CommandResult(returncode=-1, stdout="", stderr="Timed out", command=cmd)


async def run_command_async(
    cmd: str,
    cwd: Optional[str] = None,
    timeout: int = 300,
) -> CommandResult:
    """Run a shell command asynchronously."""
    log.info(f"[agent]Running (async):[/agent] {cmd}")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return CommandResult(
            returncode=proc.returncode or 0,
            stdout=(stdout_bytes or b"").decode().strip(),
            stderr=(stderr_bytes or b"").decode().strip(),
            command=cmd,
        )
    except asyncio.TimeoutError:
        log.error(f"Async command timed out after {timeout}s: {cmd}")
        proc.kill()
        return CommandResult(returncode=-1, stdout="", stderr="Timed out", command=cmd)


def run_command_stream(
    cmd: str,
    cwd: Optional[str] = None,
) -> subprocess.Popen:
    """Start a command and return the Popen object for streaming output."""
    return subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
