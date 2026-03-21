"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState, Suspense } from "react";
import { login, setAuthToken } from "@/lib/api-client";
import { ArrowLeft, LogIn, LoaderCircle, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
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
      setAuthToken(auth.access_token, auth.refresh_token);

      const returnUrl = searchParams.get("returnUrl");
      if (returnUrl) {
        window.location.href = decodeURIComponent(returnUrl);
      } else {
        window.location.href = "/dashboard";
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="font-display text-4xl font-bold tracking-tight text-foreground">
            DataSim Lab
          </h1>
          <p className="mt-2 text-muted-foreground">Welcome back, agent.</p>
        </div>

        <Card className="rounded-xl border-border bg-gradient-to-br from-white/[0.05] to-transparent p-8 backdrop-blur-[2px] shadow-xl shadow-primary/5">
          <div className="relative z-10">
            <form onSubmit={onSubmit} className="space-y-6">
              <div className="space-y-2">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-muted-foreground"
                >
                  Email address
                </label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                  placeholder="agent@datasim.lab"
                />
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-muted-foreground"
                >
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  placeholder="••••••••"
                />
              </div>

              {status && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{status}</AlertDescription>
                </Alert>
              )}

              <Button
                type="submit"
                variant="cyber"
                disabled={isSubmitting}
                className="w-full !h-11"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <LoaderCircle className="h-4 w-4 animate-spin" />{" "}
                    Authenticating…
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <LogIn className="h-4 w-4" /> Sign In
                  </span>
                )}
              </Button>
            </form>

            <p className="mt-6 text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link
                className="font-semibold text-primary/90 underline-offset-4 transition-colors hover:text-primary hover:underline hover:drop-shadow-sm"
                href="/register"
              >
                Create one free
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
