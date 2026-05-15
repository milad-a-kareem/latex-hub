import { useRef, useState } from 'react';
import { isTextPath, type AssetMeta } from './useProjectFiles';

type Props = {
  files: Record<string, string>;
  assets: AssetMeta[];
  entry: string;
  selected: string;
  onSelect: (path: string) => void;
  onCreateFile: (path: string) => Promise<void>;
  onRenameFile: (oldPath: string, newPath: string) => Promise<void>;
  onDeleteFile: (path: string) => Promise<void>;
  onSetEntry: (path: string) => Promise<void>;
  onUploadAsset: (path: string, file: File) => Promise<void>;
  onDeleteAsset: (path: string) => Promise<void>;
};

export function FileTree(props: Props) {
  const { files, assets, entry, selected, onSelect } = props;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filePaths = Object.keys(files).sort();
  const assetPaths = assets.map((a) => a.path).sort();

  async function handleCreate() {
    const name = prompt('New file path (e.g. intro.tex)');
    if (!name) return;
    setError(null);
    try {
      await props.onCreateFile(name);
      if (isTextPath(name)) onSelect(name);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    }
  }

  async function handleRename(path: string) {
    const next = prompt('Rename to:', path);
    if (!next || next === path) return;
    setError(null);
    try {
      await props.onRenameFile(path, next);
      if (selected === path) onSelect(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rename failed');
    }
  }

  async function handleDelete(path: string, kind: 'file' | 'asset') {
    if (!confirm(`Delete ${path}?`)) return;
    setError(null);
    try {
      if (kind === 'file') {
        await props.onDeleteFile(path);
        if (selected === path) {
          const fallback = filePaths.find((p) => p !== path) ?? entry;
          if (fallback) onSelect(fallback);
        }
      } else {
        await props.onDeleteAsset(path);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    }
  }

  async function handleSetEntry(path: string) {
    setError(null);
    try {
      await props.onSetEntry(path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Set main failed');
    }
  }

  async function handleUpload(file: File) {
    setError(null);
    try {
      await props.onUploadAsset(file.name, file);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    }
  }

  return (
    <aside className="flex h-full flex-col border-r text-sm">
      <div className="flex items-center justify-between gap-1 border-b p-2">
        <span className="text-xs font-semibold uppercase text-[var(--muted-foreground)]">
          Files
        </span>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={handleCreate}
            className="rounded border px-2 py-0.5 text-xs hover:bg-[var(--muted)]"
            title="New file"
          >
            + File
          </button>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="rounded border px-2 py-0.5 text-xs hover:bg-[var(--muted)]"
            title="Upload"
          >
            ↑
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleUpload(f);
              e.target.value = '';
            }}
          />
        </div>
      </div>
      {error && <div className="border-b bg-red-50 p-2 text-xs text-red-700">{error}</div>}
      <ul className="flex-1 overflow-auto py-1">
        {filePaths.map((path) => (
          <li
            key={path}
            className={`group flex items-center justify-between gap-1 px-2 py-1 ${
              selected === path ? 'bg-[var(--muted)]' : 'hover:bg-[var(--muted)]'
            }`}
          >
            <button
              type="button"
              onClick={() => onSelect(path)}
              className="flex-1 truncate text-left"
              title={path}
            >
              <span className={entry === path ? 'font-semibold' : ''}>{path}</span>
              {entry === path && (
                <span className="ml-1 text-xs text-[var(--muted-foreground)]">main</span>
              )}
            </button>
            <div className="hidden gap-1 text-xs text-[var(--muted-foreground)] group-hover:flex">
              {path.toLowerCase().endsWith('.tex') && entry !== path && (
                <button
                  type="button"
                  onClick={() => handleSetEntry(path)}
                  className="hover:underline"
                  title="Set as compile entry"
                >
                  main
                </button>
              )}
              <button
                type="button"
                onClick={() => handleRename(path)}
                className="hover:underline"
              >
                rename
              </button>
              <button
                type="button"
                onClick={() => handleDelete(path, 'file')}
                className="text-red-600 hover:underline"
              >
                del
              </button>
            </div>
          </li>
        ))}
        {assetPaths.length > 0 && (
          <li className="mt-2 px-2 text-xs font-semibold uppercase text-[var(--muted-foreground)]">
            Assets
          </li>
        )}
        {assetPaths.map((path) => (
          <li
            key={`asset:${path}`}
            className="group flex items-center justify-between gap-1 px-2 py-1 hover:bg-[var(--muted)]"
          >
            <span className="flex-1 truncate text-[var(--muted-foreground)]" title={path}>
              {path}
            </span>
            <button
              type="button"
              onClick={() => handleDelete(path, 'asset')}
              className="hidden text-xs text-red-600 hover:underline group-hover:inline"
            >
              del
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
