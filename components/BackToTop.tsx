"use client";

import { ArrowUp } from "lucide-react";
import { useEffect, useState } from "react";

export function BackToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");

    function updateVisibility() {
      setVisible(mediaQuery.matches && window.scrollY > 500);
    }

    updateVisibility();
    window.addEventListener("scroll", updateVisibility, { passive: true });
    mediaQuery.addEventListener("change", updateVisibility);

    return () => {
      window.removeEventListener("scroll", updateVisibility);
      mediaQuery.removeEventListener("change", updateVisibility);
    };
  }, []);

  if (!visible) {
    return null;
  }

  return (
    <button
      className="fixed bottom-5 right-5 z-50 inline-flex h-11 w-11 items-center justify-center rounded-full border border-line bg-white text-accent shadow-panel hover:border-accent hover:bg-panel"
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="Back to top"
      title="Back to top"
    >
      <ArrowUp className="h-5 w-5" aria-hidden="true" />
    </button>
  );
}
