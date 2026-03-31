"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Milestone, Menu, X, LogOut, Sparkles } from "lucide-react";
import { useState, useEffect } from "react";
import { logout, me } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { cn } from "@/lib/utils";

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
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
        }
      }
    };

    void checkSession();

    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => {
      cancelled = true;
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  const navLinks = [{ name: "Dashboard", href: "/dashboard" }];
  const mobileFlows = [
    { name: "Dataset List", href: "/dashboard" },
    { name: "Create New Dataset", href: "/studio?new=true" },
  ];

  const isActive = (path: string) => pathname === path;

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Ignore API errors on logout
    } finally {
      setIsAuthenticated(false);
      window.location.href = "/";
    }
  };

  return (
    <nav
      className={cn(
        "fixed top-0 z-50 w-full transition-all duration-300",
        scrolled ? "py-3" : "py-4",
      )}
    >
      <div
        className={cn(
          "mx-auto flex max-w-7xl items-center justify-between rounded-2xl border px-4 shadow-sm transition-all md:px-8",
          scrolled
            ? "border-border/70 bg-card/85 py-2.5 backdrop-blur-xl"
            : "border-transparent bg-transparent py-2",
        )}
      >
        <Link href="/" className="flex items-center gap-2 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-primary/25 bg-primary/15 text-primary transition-transform group-hover:scale-110">
            <Milestone className="h-5 w-5" />
          </div>
          <span className="font-display text-xl font-bold tracking-tight text-foreground">
            DataSim<span className="text-primary">Lab</span>
          </span>
          <span className="hidden rounded-full border border-secondary/40 bg-secondary/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.13em] text-secondary md:inline-flex">
            Beta
          </span>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden items-center gap-8 md:flex">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              href={link.href}
              className={cn(
                "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
                isActive(link.href)
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {link.name}
            </Link>
          ))}
          <div className="flex items-center gap-3">
            <ThemeToggle />
            {isAuthenticated ? (
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                className="h-9 px-4 text-xs hover:border-destructive hover:bg-destructive hover:text-destructive-foreground"
              >
                <LogOut className="mr-2 h-3.5 w-3.5" />
                Sign Out
              </Button>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  Sign In
                </Link>
                <Button
                  asChild
                  variant="default"
                  size="sm"
                  className="h-9 px-5 text-xs"
                >
                  <Link href="/register">Get Started</Link>
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Mobile Toggle */}
        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <Button
            variant="outline"
            size="icon"
            className="h-11 w-11"
            onClick={() => setIsOpen(!isOpen)}
            aria-label={
              isOpen ? "Close navigation menu" : "Open navigation menu"
            }
          >
            {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="absolute left-0 top-full w-full p-4 md:hidden">
          <div className="mx-auto max-w-7xl rounded-2xl border border-border/70 bg-card/95 p-4 shadow-2xl backdrop-blur-xl">
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-secondary/30 bg-secondary/15 px-3 py-2 text-xs text-secondary">
              <Sparkles className="h-3.5 w-3.5" />
              Design faster with guided studio flow
            </div>
            <div className="flex flex-col gap-4">
              {mobileFlows.map((link) => (
                <Link
                  key={link.name}
                  href={link.href}
                  className={`min-h-12 rounded-lg px-4 py-3 text-sm font-medium transition-colors ${
                    isActive(link.href)
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground"
                  }`}
                  onClick={() => setIsOpen(false)}
                >
                  {link.name}
                </Link>
              ))}
              <hr className="border-border" />
              {isAuthenticated ? (
                <Button
                  variant="default"
                  className="min-h-12 w-full"
                  onClick={() => {
                    setIsOpen(false);
                    handleLogout();
                  }}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign Out
                </Button>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="min-h-12 rounded-lg px-4 py-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-card/70 hover:text-foreground"
                    onClick={() => setIsOpen(false)}
                  >
                    Sign In
                  </Link>
                  <Button asChild variant="default" className="min-h-12 w-full">
                    <Link href="/register" onClick={() => setIsOpen(false)}>
                      Get Started
                    </Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
