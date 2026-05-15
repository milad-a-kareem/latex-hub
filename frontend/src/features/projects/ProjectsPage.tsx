import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, apiVoid } from '@/lib/api';

type Project = { id: string; name: string; updatedAt: string };

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  useEffect(() => {
    api<Project[]>('/api/projects')
      .then(setProjects)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'));
  }, []);

  async function create() {
    setError(null);
    try {
      const p = await api<Project>('/api/projects', {
        method: 'POST',
        body: JSON.stringify({ name }),
      });
      setProjects((prev) => [p, ...prev]);
      setName('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create');
    }
  }

  async function commitRename(id: string) {
    if (!renameValue.trim()) {
      setRenamingId(null);
      return;
    }
    try {
      const updated = await api<Project>(`/api/projects/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: renameValue.trim() }),
      });
      setProjects((prev) => prev.map((p) => (p.id === id ? { ...p, name: updated.name } : p)));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rename failed');
    } finally {
      setRenamingId(null);
    }
  }

  async function remove(id: string, name: string) {
    if (!confirm(`Delete project "${name}"? This cannot be undone.`)) return;
    try {
      await apiVoid(`/api/projects/${id}`, { method: 'DELETE' });
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-2xl font-semibold">Projects</h1>
      <div className="mb-6 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name"
          className="flex-1 rounded-md border px-3 py-2"
        />
        <button
          onClick={create}
          disabled={!name}
          className="rounded-md bg-[var(--primary)] px-3 py-2 text-[var(--primary-foreground)] disabled:opacity-50"
        >
          Create
        </button>
      </div>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <ul className="divide-y rounded-md border">
        {projects.length === 0 && (
          <li className="p-4 text-sm text-[var(--muted-foreground)]">No projects yet.</li>
        )}
        {projects.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-3 p-3">
            {renamingId === p.id ? (
              <input
                autoFocus
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={() => commitRename(p.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitRename(p.id);
                  if (e.key === 'Escape') setRenamingId(null);
                }}
                className="flex-1 rounded-md border px-2 py-1 text-sm"
              />
            ) : (
              <Link
                to={`/projects/${p.id}`}
                className="flex-1 font-medium hover:underline"
              >
                {p.name}
              </Link>
            )}
            <span className="text-xs text-[var(--muted-foreground)]">{p.updatedAt}</span>
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                onClick={() => {
                  setRenameValue(p.name);
                  setRenamingId(p.id);
                }}
                className="text-[var(--muted-foreground)] hover:underline"
              >
                Rename
              </button>
              <button
                type="button"
                onClick={() => remove(p.id, p.name)}
                className="text-red-600 hover:underline"
              >
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
