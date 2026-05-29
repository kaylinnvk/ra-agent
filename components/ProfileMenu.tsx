"use client";

import { ChevronDown, Github, LogOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type ProfileMenuProps = {
  image?: string | null;
  name?: string | null;
  email?: string | null;
  signOutAction: () => Promise<void>;
};

export function ProfileMenu({ image, name, email, signOutAction }: ProfileMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const userLabel = name || email || "GitHub user";

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        className="inline-flex h-10 shrink-0 items-center gap-2 rounded-md border border-line bg-white px-2 text-sm font-semibold text-ink transition hover:border-accent hover:text-accent"
        onClick={() => setOpen((value) => !value)}
        title="Account menu"
        type="button"
      >
        {image ? (
          <img className="h-6 w-6 shrink-0 rounded-full" src={image} alt="" />
        ) : (
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-50 text-accent">
            <Github className="h-3.5 w-3.5" aria-hidden="true" />
          </div>
        )}
        <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
      </button>

      {open ? (
        <div
          className="absolute right-0 top-12 z-30 w-64 rounded-md border border-line bg-white p-2 shadow-lg"
          role="menu"
        >
          <div className="flex min-w-0 items-center gap-3 px-2 py-2">
            {image ? (
              <img className="h-9 w-9 shrink-0 rounded-full" src={image} alt="" />
            ) : (
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-teal-50 text-accent">
                <Github className="h-4 w-4" aria-hidden="true" />
              </div>
            )}
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-ink">{userLabel}</div>
              {email && name ? <div className="truncate text-xs text-muted">{email}</div> : null}
            </div>
          </div>

          <div className="my-1 h-px bg-line" />

          <form action={signOutAction}>
            <button
              className="flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-sm font-semibold text-ink transition hover:bg-panel hover:text-accent"
              role="menuitem"
              type="submit"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Log out
            </button>
          </form>
        </div>
      ) : null}
    </div>
  );
}
