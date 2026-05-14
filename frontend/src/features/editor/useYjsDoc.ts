import { useEffect, useState } from 'react';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { auth } from '@/lib/firebase';
import { wsUrl } from '@/lib/api';

export type YjsHandle = {
  doc: Y.Doc;
  provider: WebsocketProvider;
  text: Y.Text;
};

export function useYjsDoc(projectId: string, filePath: string): YjsHandle | null {
  const [handle, setHandle] = useState<YjsHandle | null>(null);

  useEffect(() => {
    let cancelled = false;
    const doc = new Y.Doc();

    (async () => {
      const token = (await auth.currentUser?.getIdToken()) ?? '';
      if (cancelled) return;
      const room = `${projectId}:${filePath}`;
      const provider = new WebsocketProvider(wsUrl('/ws/collab'), room, doc, {
        params: { token },
      });
      const text = doc.getText('content');
      setHandle({ doc, provider, text });
    })();

    return () => {
      cancelled = true;
      doc.destroy();
    };
  }, [projectId, filePath]);

  return handle;
}
