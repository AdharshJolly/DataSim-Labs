"use client";

import { useEffect } from "react";

export function ScrollReveal() {
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    const selectors = [
      "main section",
      "main article",
      "main .reveal-item",
      "main .card-reveal",
    ];

    const nodes = Array.from(
      document.querySelectorAll<HTMLElement>(selectors.join(",")),
    );

    if (prefersReducedMotion) {
      for (const node of nodes) {
        node.classList.add("is-revealed");
      }
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-revealed");
            observer.unobserve(entry.target);
          }
        }
      },
      {
        rootMargin: "0px 0px -12% 0px",
        threshold: 0.08,
      },
    );

    for (const node of nodes) {
      node.classList.add("reveal-on-scroll");
      observer.observe(node);
    }

    return () => observer.disconnect();
  }, []);

  return null;
}
