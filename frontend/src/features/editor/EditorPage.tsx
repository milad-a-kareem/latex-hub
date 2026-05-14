import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { LatexEditor } from './LatexEditor';
import { PdfPreview } from './PdfPreview';
import { useYjsDoc } from './useYjsDoc';
import { api } from '@/lib/api';

type CompileResult = { pdfUrl: string; log: string };

export function EditorPage() {
  const { projectId = '' } = useParams<{ projectId: string }>();
  const yjs = useYjsDoc(projectId, 'main.tex');
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [log, setLog] = useState<string>('');

  async function compile() {
    setCompiling(true);
    try {
      const r = await api<CompileResult>(`/api/projects/${projectId}/compile`, {
        method: 'POST',
      });
      setPdfUrl(r.pdfUrl);
      setLog(r.log);
    } catch (e) {
      setLog(e instanceof Error ? e.message : 'Compile failed');
    } finally {
      setCompiling(false);
    }
  }

  return (
    <div className="grid h-full grid-rows-[auto_1fr]">
      <header className="flex items-center justify-between border-b px-4 py-2">
        <h1 className="text-sm font-medium">Project {projectId}</h1>
        <button
          onClick={compile}
          disabled={compiling}
          className="rounded-md bg-[var(--primary)] px-3 py-1 text-sm text-[var(--primary-foreground)] disabled:opacity-50"
        >
          {compiling ? 'Compiling…' : 'Compile'}
        </button>
      </header>
      <div className="grid h-full grid-cols-2 overflow-hidden">
        <div className="border-r">
          {yjs ? <LatexEditor yjs={yjs} /> : <div className="p-4">Connecting…</div>}
        </div>
        <div className="grid grid-rows-[1fr_auto]">
          <PdfPreview url={pdfUrl} />
          {log && (
            <pre className="max-h-40 overflow-auto border-t bg-neutral-950 p-2 text-xs text-neutral-200">
              {log}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
