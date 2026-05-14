import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '@/lib/api';

type Project = { id: string; name: string; updatedAt: string };

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState('');

  useEffect(() => {
    api<Project[]>('/api/projects').then(setProjects).catch(() => setProjects([]));
  }, []);

  async function create() {
    const p = await api<Project>('/api/projects', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    setProjects((prev) => [p, ...prev]);
    setName('');
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
      <ul className="divide-y rounded-md border">
        {projects.map((p) => (
          <li key={p.id} className="flex items-center justify-between p-3">
            <Link to={`/projects/${p.id}`} className="font-medium hover:underline">
              {p.name}
            </Link>
            <span className="text-xs text-[var(--muted-foreground)]">{p.updatedAt}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
