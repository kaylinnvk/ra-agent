import { Bot, Github } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-[#1f686a] text-white">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-start px-4 py-4 sm:px-6 md:justify-between md:py-5 lg:px-8">
        <div className="hidden min-w-0 items-center gap-3 md:flex">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-white/25 bg-white/10">
            <Bot className="h-6 w-6" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h2 className="break-words text-sm font-semibold sm:text-lg">ra-agent</h2>
            <p className="break-words text-sm font-medium text-white/65">mini project by kaylinnvk</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            className="inline-flex h-9 items-center gap-2 rounded-md border border-white/25 bg-white/10 px-3 text-sm font-semibold text-white transition hover:bg-white/15"
            href="https://github.com/kaylinnvk/ra-agent"
            target="_blank"
            rel="noreferrer"
          >
            <Github className="h-4 w-4" aria-hidden="true" />
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
