import asyncio
import shutil
import uuid
from pathlib import Path


class CompileError(RuntimeError):
    def __init__(self, log: str) -> None:
        super().__init__("tectonic compile failed")
        self.log = log


def _stage_sources(workdir: Path, files: dict[str, str]) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    job_dir = workdir / uuid.uuid4().hex
    job_dir.mkdir()
    for path, content in files.items():
        target = job_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return job_dir


def _read_pdf(job_dir: Path, entry: str) -> bytes | None:
    pdf_path = job_dir / Path(entry).with_suffix(".pdf").name
    return pdf_path.read_bytes() if pdf_path.exists() else None


async def compile_latex(workdir: Path, files: dict[str, str], entry: str = "main.tex") -> bytes:
    """Run tectonic on the given LaTeX sources and return the PDF bytes.

    Each call gets a fresh temp directory under ``workdir`` so concurrent
    requests do not collide. Filesystem ops are offloaded to a worker thread
    so they don't block the event loop.
    """
    job_dir = await asyncio.to_thread(_stage_sources, workdir, files)
    try:
        proc = await asyncio.create_subprocess_exec(
            "tectonic",
            "--keep-logs",
            "--outdir",
            str(job_dir),
            str(job_dir / entry),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        log = stdout.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            raise CompileError(log)

        pdf = await asyncio.to_thread(_read_pdf, job_dir, entry)
        if pdf is None:
            raise CompileError(log + "\n(no PDF produced)")
        return pdf
    finally:
        await asyncio.to_thread(shutil.rmtree, job_dir, ignore_errors=True)
