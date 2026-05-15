import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { LatexEditor } from './LatexEditor';
import { PdfPreview } from './PdfPreview';
import { useYjsDoc } from './useYjsDoc';
import { useProjectFiles, isTextPath } from './useProjectFiles';
import { FileTree } from './FileTree';
import { api } from '@/lib/api';

type CompileResult = { pdfUrl: string; log: string };

export function EditorPage() {
  const { projectId = '' } = useParams<{ projectId: string }>();
  const project = useProjectFiles(projectId);
  // User's clicked selection. Empty until they pick (or the project bootstrap
  // resolves below and we fall through to entry). Derived effective path is
  // computed each render so we never store stale state for a deleted file.
  const [selected, setSelected] = useState<string>('');
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [log, setLog] = useState<string>('');

  const known = project.data ? Object.keys(project.data.files) : [];
  const projectEntry = project.data?.entry || 'main.tex';
  const effectiveSelected =
    selected && known.includes(selected)
      ? selected
      : known.includes(projectEntry)
        ? projectEntry
        : known[0] || '';

  const yjs = useYjsDoc(projectId, effectiveSelected || 'main.tex');

  async function compile() {
    setCompiling(true);
    try {
      const r = await api<CompileResult>(`/api/projects/${projectId}/compile`, {
        method: 'POST',
      });
      setPdfUrl(r.pdfUrl || null);
      setLog(r.log);
    } catch (e) {
      setLog(e instanceof Error ? e.message : 'Compile failed');
    } finally {
      setCompiling(false);
    }
  }

  const projectName = project.data?.name || 'Project';
  const isTextFile = effectiveSelected && isTextPath(effectiveSelected);

  return (
    <div className="grid h-full grid-rows-[auto_1fr]">
      <header className="flex items-center justify-between gap-3 border-b px-4 py-2">
        <div className="flex items-center gap-3">
          <Link to="/projects" className="text-sm text-[var(--muted-foreground)] hover:underline">
            ← Projects
          </Link>
          <h1 className="text-sm font-medium">{projectName}</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-[var(--muted-foreground)]">Main: {projectEntry}</span>
          <button
            onClick={compile}
            disabled={compiling}
            className="rounded-md bg-[var(--primary)] px-3 py-1 text-sm text-[var(--primary-foreground)] disabled:opacity-50"
          >
            {compiling ? 'Compiling…' : 'Compile'}
          </button>
        </div>
      </header>
      <div className="grid h-full grid-cols-[14rem_1fr_1fr] overflow-hidden">
        {project.data ? (
          <FileTree
            files={project.data.files}
            assets={project.data.assets}
            entry={project.data.entry}
            selected={effectiveSelected}
            onSelect={setSelected}
            onCreateFile={project.createFile}
            onRenameFile={project.renameFile}
            onDeleteFile={project.deleteFile}
            onSetEntry={project.setEntry}
            onUploadAsset={project.uploadAsset}
            onDeleteAsset={project.deleteAsset}
          />
        ) : (
          <aside className="border-r p-4 text-sm text-[var(--muted-foreground)]">
            {project.error ?? 'Loading…'}
          </aside>
        )}
        <div className="border-r">
          {isTextFile && yjs ? (
            <LatexEditor yjs={yjs} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-[var(--muted-foreground)]">
              {effectiveSelected
                ? `Cannot edit ${effectiveSelected} in the source editor.`
                : 'No file selected.'}
            </div>
          )}
        </div>
        <div className="grid grid-rows-[1fr_auto]">
          <PdfPreview url={pdfUrl} downloadName={`${projectName}.pdf`} />
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
