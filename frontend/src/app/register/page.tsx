"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { register, setAuthToken } from "@/lib/api-client";

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
      const response = await register({ email, password });
      setAuthToken(response.access_token);
      window.location.href = "/dashboard";
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Registration failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="mx-auto max-w-md space-y-5">
      <div className="space-y-2">
        <h1 className="font-[var(--font-title)] text-3xl font-bold">
          Register
        </h1>
        <p className="text-muted-foreground">Create your DataSim account.</p>
      </div>

      <form onSubmit={onSubmit} className="sk-panel grid gap-4">
        <label className="space-y-1 text-sm font-medium">
          Email
          <input
            type="email"
            className="sk-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label className="space-y-1 text-sm font-medium">
          Password
          <input
            type="password"
            className="sk-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        <button
          type="submit"
          disabled={isSubmitting}
          className="sk-btn sk-btn-primary w-fit"
        >
          {isSubmitting ? "Creating..." : "Register"}
        </button>
        {status ? (
          <p className="text-sm text-muted-foreground">{status}</p>
        ) : null}
      </form>

      <p className="text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link className="underline" href="/login">
          Login
        </Link>
      </p>
    </section>
  );
}
