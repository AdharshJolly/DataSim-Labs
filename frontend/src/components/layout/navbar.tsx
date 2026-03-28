"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Milestone, Menu, X, LogOut, User } from "lucide-react";
import { useState, useEffect } from "react";
import { logout, me } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

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

  const navLinks = [
    { name: "Dashboard", href: "/dashboard" },
    { name: "Profile", href: "/profile-upload" },
  ];
  const mobileFlows = [
    { name: "Dataset List", href: "/dashboard" },
    { name: "Create New Dataset", href: "/studio?new=true" },
    { name: "Profile", href: "/profile-upload" },
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
      className={`fixed top-0 z-50 w-full transition-all duration-300 ${
        scrolled
          ? "border-b border-white/10 bg-background/80 backdrop-blur-md py-3"
          : "bg-transparent py-5"
      }`}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 md:px-8">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/20 text-primary transition-transform group-hover:scale-110">
            <Milestone className="h-5 w-5" />
          </div>
          <span className="font-display text-xl font-bold tracking-tight text-foreground">
            DataSim<span className="text-primary">Lab</span>
          </span>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden items-center gap-8 md:flex">
          <div className="flex items-center gap-6">
            {navLinks.map((link) => (
              <Link
                key={link.name}
                href={link.href}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  isActive(link.href) ? "text-primary" : "text-muted-foreground"
                }`}
              >
                {link.name}
              </Link>
            ))}
          </div>
          <div className="h-4 w-px bg-border" />
          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <Button
                variant="default"
                size="sm"
                onClick={handleLogout}
                className="h-9 px-5 text-xs hover:border-destructive hover:bg-destructive hover:text-destructive-foreground"
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
        <Button
          variant="outline"
          size="icon"
          className="h-12 w-12 md:hidden"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
        >
          {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="absolute left-0 top-full w-full border-b border-border bg-background/95 p-4 backdrop-blur-xl md:hidden">
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
                  className="min-h-12 rounded-lg px-4 py-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground"
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
      )}
    </nav>
  );
}
