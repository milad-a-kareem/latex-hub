import { useState, type FormEvent } from 'react';
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
} from 'firebase/auth';
import { useNavigate } from 'react-router-dom';
import { auth } from '@/lib/firebase';

type Mode = 'in' | 'up' | 'reset';

export function LoginPage() {
  const nav = useNavigate();
  const [mode, setMode] = useState<Mode>('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      if (mode === 'reset') {
        await sendPasswordResetEmail(auth, email);
        setInfo('Password reset email sent. Check your inbox.');
      } else {
        const fn = mode === 'in' ? signInWithEmailAndPassword : createUserWithEmailAndPassword;
        await fn(auth, email, password);
        nav('/projects');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Auth failed');
    } finally {
      setSubmitting(false);
    }
  }

  const heading =
    mode === 'in' ? 'Sign in' : mode === 'up' ? 'Create account' : 'Reset password';
  const submitLabel =
    mode === 'in' ? 'Sign in' : mode === 'up' ? 'Sign up' : 'Send reset email';

  return (
    <div className="mx-auto flex h-full max-w-sm flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">{heading}</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="rounded-md border px-3 py-2"
        />
        {mode !== 'reset' && (
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="rounded-md border px-3 py-2"
          />
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {info && <p className="text-sm text-green-700">{info}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-[var(--primary)] px-3 py-2 text-[var(--primary-foreground)] disabled:opacity-50"
        >
          {submitting ? 'Working…' : submitLabel}
        </button>
      </form>
      <div className="flex items-center justify-between text-sm text-[var(--muted-foreground)]">
        {mode === 'reset' ? (
          <button type="button" onClick={() => setMode('in')} className="underline">
            Back to sign in
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={() => setMode(mode === 'in' ? 'up' : 'in')}
              className="underline"
            >
              {mode === 'in' ? 'Need an account? Sign up' : 'Have an account? Sign in'}
            </button>
            <button type="button" onClick={() => setMode('reset')} className="underline">
              Forgot password?
            </button>
          </>
        )}
      </div>
    </div>
  );
}
