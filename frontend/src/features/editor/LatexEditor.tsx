import { useEffect, useRef } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';
import { MonacoBinding } from 'y-monaco';
import type { YjsHandle } from './useYjsDoc';

type Props = { yjs: YjsHandle };

export function LatexEditor({ yjs }: Props) {
  const bindingRef = useRef<MonacoBinding | null>(null);

  useEffect(() => () => bindingRef.current?.destroy(), []);

  const onMount: OnMount = (editor) => {
    const model = editor.getModel();
    if (!model) return;
    bindingRef.current = new MonacoBinding(
      yjs.text,
      model,
      new Set([editor]),
      yjs.provider.awareness,
    );
  };

  return (
    <Editor
      height="100%"
      defaultLanguage="latex"
      theme="vs-dark"
      onMount={onMount}
      options={{ wordWrap: 'on', minimap: { enabled: false }, fontSize: 14 }}
    />
  );
}
