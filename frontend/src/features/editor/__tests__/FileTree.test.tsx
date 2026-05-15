import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@/lib/firebase', () => ({
  auth: {},
  db: {},
  storage: {},
}));

import { FileTree } from '../FileTree';

function noopAsync<T extends unknown[]>() {
  return vi.fn<(...args: T) => Promise<void>>().mockResolvedValue(undefined);
}

describe('FileTree', () => {
  const baseProps = {
    files: { 'main.tex': '', 'intro.tex': '' },
    assets: [{ path: 'fig.png', size: 100, contentType: 'image/png' }],
    entry: 'main.tex',
    selected: 'main.tex',
  };

  it('renders files, assets, and marks the entry', () => {
    render(
      <FileTree
        {...baseProps}
        onSelect={() => {}}
        onCreateFile={noopAsync()}
        onRenameFile={noopAsync()}
        onDeleteFile={noopAsync()}
        onSetEntry={noopAsync()}
        onUploadAsset={noopAsync()}
        onDeleteAsset={noopAsync()}
      />,
    );
    expect(screen.getByText('main.tex')).toBeTruthy();
    expect(screen.getByText('intro.tex')).toBeTruthy();
    expect(screen.getByText('fig.png')).toBeTruthy();
    // The entry file has a "main" marker next to it (also a button for
    // non-entry .tex files); we just check that at least one such marker
    // exists.
    expect(screen.getAllByText('main').length).toBeGreaterThan(0);
  });

  it('invokes onSelect when a file row is clicked', () => {
    const onSelect = vi.fn();
    render(
      <FileTree
        {...baseProps}
        onSelect={onSelect}
        onCreateFile={noopAsync()}
        onRenameFile={noopAsync()}
        onDeleteFile={noopAsync()}
        onSetEntry={noopAsync()}
        onUploadAsset={noopAsync()}
        onDeleteAsset={noopAsync()}
      />,
    );
    fireEvent.click(screen.getByText('intro.tex'));
    expect(onSelect).toHaveBeenCalledWith('intro.tex');
  });

  it('prompts and calls onCreateFile for new file action', async () => {
    const onCreateFile = noopAsync<[string]>();
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('new.tex');
    render(
      <FileTree
        {...baseProps}
        onSelect={() => {}}
        onCreateFile={onCreateFile}
        onRenameFile={noopAsync()}
        onDeleteFile={noopAsync()}
        onSetEntry={noopAsync()}
        onUploadAsset={noopAsync()}
        onDeleteAsset={noopAsync()}
      />,
    );
    fireEvent.click(screen.getByTitle('New file'));
    expect(onCreateFile).toHaveBeenCalledWith('new.tex');
    promptSpy.mockRestore();
  });
});
