"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { register } from "@/lib/api-client";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus("");
    setIsSubmitting(true);
    try {
      await register({ email, password });
      window.location.href = "/dashboard";
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Registration failed");
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
          Create your account
        </h1>
        <p className="mt-1 text-[hsl(var(--muted-foreground))]">
          Free forever. Start generating datasets in minutes.
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
            Password{" "}
            <span className="text-xs font-normal text-[hsl(var(--muted-foreground))]">
              (min. 8 characters)
            </span>
          </label>
          <input
            id="password"
            type="password"
            className="sk-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
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
              <span className="sk-spinner h-4 w-4" /> Creating account…
            </span>
          ) : (
            "Create Account"
          )}
        </button>
      </form>

      <p className="text-center text-sm text-[hsl(var(--muted-foreground))]">
        Already have an account?{" "}
        <Link
          className="font-semibold text-[hsl(var(--primary))] underline-offset-2 hover:underline"
          href="/login"
        >
          Sign in
        </Link>
      </p>
    </section>
  );
}
