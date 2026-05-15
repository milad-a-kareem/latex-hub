import { useEffect, useRef, useState } from 'react';
import * as pdfjs from 'pdfjs-dist';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

type Props = { url: string | null; downloadName?: string };

export function PdfPreview({ url, downloadName }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);

  useEffect(() => {
    if (!url || !canvasRef.current) return;
    let cancelled = false;
    (async () => {
      const pdf = await pdfjs.getDocument(url).promise;
      if (cancelled) return;
      setPages(pdf.numPages);
      const p = await pdf.getPage(page);
      const viewport = p.getViewport({ scale: 1.4 });
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext('2d')!;
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await p.render({ canvasContext: ctx, viewport, canvas }).promise;
    })();
    return () => {
      cancelled = true;
    };
  }, [url, page]);

  if (!url) {
    return (
      <div className="flex h-full items-center justify-center text-[var(--muted-foreground)]">
        No PDF yet — click Compile.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b p-2 text-sm">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
          ‹
        </button>
        <span>
          {page} / {pages || '?'}
        </span>
        <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}>
          ›
        </button>
        <a
          href={url}
          download={downloadName || 'document.pdf'}
          target="_blank"
          rel="noreferrer"
          className="ml-auto rounded border px-2 py-0.5 text-xs hover:bg-[var(--muted)]"
        >
          Download PDF
        </a>
      </div>
      <div className="flex-1 overflow-auto bg-neutral-800 p-4">
        <canvas ref={canvasRef} className="mx-auto bg-white shadow" />
      </div>
    </div>
  );
}
