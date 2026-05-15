import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

const sendReset = vi.fn();

vi.mock('firebase/auth', () => ({
  signInWithEmailAndPassword: vi.fn(),
  createUserWithEmailAndPassword: vi.fn(),
  sendPasswordResetEmail: (...args: unknown[]) => sendReset(...args),
}));

vi.mock('@/lib/firebase', () => ({
  auth: {},
}));

import { LoginPage } from '../LoginPage';

describe('LoginPage', () => {
  beforeEach(() => {
    sendReset.mockReset();
    sendReset.mockResolvedValue(undefined);
  });

  it('shows reset form when "Forgot password?" is clicked', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    expect(screen.getByPlaceholderText('Password')).toBeTruthy();

    fireEvent.click(screen.getByText('Forgot password?'));

    expect(screen.queryByPlaceholderText('Password')).toBeNull();
    expect(screen.getByText('Reset password')).toBeTruthy();
    expect(screen.getByText('Send reset email')).toBeTruthy();
  });

  it('calls sendPasswordResetEmail with the entered address', async () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Forgot password?'));
    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'user@example.com' },
    });
    fireEvent.click(screen.getByText('Send reset email'));

    await waitFor(() => {
      expect(sendReset).toHaveBeenCalledWith({}, 'user@example.com');
    });
    expect(screen.getByText(/Password reset email sent/)).toBeTruthy();
  });
});
