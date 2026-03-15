"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { LoaderCircle } from "lucide-react";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Check if token exists in localStorage
    const token = localStorage.getItem("datasim_access_token");
    
    if (!token) {
      setIsAuthenticated(false);
      // Redirect to login if not authenticated
      const returnUrl = encodeURIComponent(pathname);
      router.push(`/login?returnUrl=${returnUrl}`);
    } else {
      setIsAuthenticated(true);
    }
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
