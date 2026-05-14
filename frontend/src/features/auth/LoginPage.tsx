import { useState, type FormEvent } from 'react';
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
} from 'firebase/auth';
import { useNavigate } from 'react-router-dom';
import { auth } from '@/lib/firebase';

export function LoginPage() {
  const nav = useNavigate();
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const fn = mode === 'in' ? signInWithEmailAndPassword : createUserWithEmailAndPassword;
      await fn(auth, email, password);
      nav('/projects');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Auth failed');
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-sm flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">{mode === 'in' ? 'Sign in' : 'Create account'}</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="rounded-md border px-3 py-2"
        />
        <input
          type="password"
          required
          minLength={6}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="rounded-md border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          className="rounded-md bg-[var(--primary)] px-3 py-2 text-[var(--primary-foreground)]"
        >
          {mode === 'in' ? 'Sign in' : 'Sign up'}
        </button>
      </form>
      <button
        type="button"
        onClick={() => setMode(mode === 'in' ? 'up' : 'in')}
        className="text-sm text-[var(--muted-foreground)] underline"
      >
        {mode === 'in' ? 'Need an account? Sign up' : 'Have an account? Sign in'}
      </button>
    </div>
  );
}
