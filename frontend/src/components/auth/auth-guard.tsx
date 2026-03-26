"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { me } from "@/lib/api-client";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    let cancelled = false;

    const checkSession = async () => {
      try {
        await me();
        if (!cancelled) {
          setIsAuthenticated(true);
        }
      } catch {
        if (!cancelled) {
          setIsAuthenticated(false);
          const returnUrl = encodeURIComponent(pathname);
          router.push(`/login?returnUrl=${returnUrl}`);
        }
      }
    };

    void checkSession();

    return () => {
      cancelled = true;
    };
  }, [router, pathname]);

  // Show loading state while checking authentication
  if (isAuthenticated === null) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <LoaderCircle className="h-10 w-10 animate-spin text-primary" />
        <p className="text-sm font-medium text-muted-foreground animate-pulse">
          Authenticating session...
        </p>
      </div>
    );
  }

  // If not authenticated, don't render children (the redirect happens in useEffect)
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
