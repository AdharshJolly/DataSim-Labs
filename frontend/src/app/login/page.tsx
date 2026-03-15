"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { login, setAuthToken } from "@/lib/api-client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus("");
    setIsSubmitting(true);
    try {
      const auth = await login({ email, password });
      setAuthToken(auth.access_token);
      window.location.href = "/dashboard";
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="mx-auto max-w-sm space-y-6 pt-4">
      <div>
        <Link
          href="/"
          className="mb-6 flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))] transition hover:text-[hsl(var(--foreground))]"
        >
          ← DataSim Lab
        </Link>
        <h1 className="font-[var(--font-title)] text-3xl font-black tracking-tight">
          Welcome back
        </h1>
        <p className="mt-1 text-[hsl(var(--muted-foreground))]">
          Sign in to access your datasets.
        </p>
      </div>

      <form onSubmit={onSubmit} className="studio-card grid gap-5">
        <div className="studio-field">
          <label htmlFor="email" className="studio-label">
            Email address
          </label>
          <input
            id="email"
            type="email"
            className="sk-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </div>
        <div className="studio-field">
          <label htmlFor="password" className="studio-label">
            Password
          </label>
          <input
            id="password"
            type="password"
            className="sk-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        {status && (
          <div className="sk-alert-error">
            <span>{status}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="sk-btn sk-btn-primary w-full py-3"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="sk-spinner h-4 w-4" /> Signing in…
            </span>
          ) : (
            "Sign In"
          )}
        </button>
      </form>

      <p className="text-center text-sm text-[hsl(var(--muted-foreground))]">
        Don&apos;t have an account?{" "}
        <Link
          className="font-semibold text-[hsl(var(--primary))] underline-offset-2 hover:underline"
          href="/register"
        >
          Create one free
        </Link>
      </p>
    </section>
  );
}
