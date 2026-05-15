import { useCallback, useEffect, useState } from 'react';
import { api, apiRaw, apiVoid } from '@/lib/api';

export type AssetMeta = { path: string; size: number; contentType: string };

export type ProjectFull = {
  id: string;
  name: string;
  entry: string;
  files: Record<string, string>;
  assets: AssetMeta[];
};

const TEXT_EXTENSIONS = ['.tex', '.bib', '.cls', '.sty', '.txt', '.md', '.bst'];

export function isTextPath(path: string): boolean {
  const lower = path.toLowerCase();
  return TEXT_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export function useProjectFiles(projectId: string) {
  const [data, setData] = useState<ProjectFull | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await api<ProjectFull>(`/api/projects/${projectId}/full`);
      setData(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Load failed');
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    api<ProjectFull>(`/api/projects/${projectId}/full`)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Load failed');
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const createFile = useCallback(
    async (path: string) => {
      await apiVoid(`/api/projects/${projectId}/files`, {
        method: 'POST',
        body: JSON.stringify({ path, content: '' }),
      });
      await refresh();
    },
    [projectId, refresh],
  );

  const deleteFile = useCallback(
    async (path: string) => {
      await apiVoid(`/api/projects/${projectId}/files/${encodeFilePath(path)}`, {
        method: 'DELETE',
      });
      await refresh();
    },
    [projectId, refresh],
  );

  const renameFile = useCallback(
    async (oldPath: string, newPath: string) => {
      await apiVoid(`/api/projects/${projectId}/files/${encodeFilePath(oldPath)}/rename`, {
        method: 'POST',
        body: JSON.stringify({ newPath }),
      });
      await refresh();
    },
    [projectId, refresh],
  );

  const setEntry = useCallback(
    async (entry: string) => {
      await apiVoid(`/api/projects/${projectId}/entry`, {
        method: 'PUT',
        body: JSON.stringify({ entry }),
      });
      await refresh();
    },
    [projectId, refresh],
  );

  const uploadAsset = useCallback(
    async (path: string, file: File) => {
      const body = await file.arrayBuffer();
      await apiRaw(`/api/projects/${projectId}/assets/${encodeFilePath(path)}`, {
        method: 'POST',
        body,
        headers: { 'Content-Type': file.type || 'application/octet-stream' },
      });
      await refresh();
    },
    [projectId, refresh],
  );

  const deleteAsset = useCallback(
    async (path: string) => {
      await apiVoid(`/api/projects/${projectId}/assets/${encodeFilePath(path)}`, {
        method: 'DELETE',
      });
      await refresh();
    },
    [projectId, refresh],
  );

  return {
    data,
    error,
    refresh,
    createFile,
    deleteFile,
    renameFile,
    setEntry,
    uploadAsset,
    deleteAsset,
  };
}

function encodeFilePath(path: string): string {
  return path.split('/').map(encodeURIComponent).join('/');
}
