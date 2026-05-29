import { AlertCircle, Bot, Github, LogIn } from "lucide-react";
import { AuthError } from "next-auth";
import { redirect } from "next/navigation";
import { auth, providerMap, signIn } from "@/auth";

type LoginPageProps = {
  searchParams: Promise<{
    callbackUrl?: string;
    error?: string;
  }>;
};

function safeCallbackUrl(value: string | undefined) {
  if (!value || value.startsWith("/api/auth")) {
    return "/";
  }

  if (value.startsWith("/")) {
    return value;
  }

  try {
    const url = new URL(value);
    return `${url.pathname}${url.search}${url.hash}` || "/";
  } catch {
    return "/";
  }
}

function errorMessage(error: string | undefined) {
  if (!error) {
    return null;
  }

  if (error === "OAuthAccountNotLinked") {
    return "This GitHub account is linked to another sign-in method.";
  }

  if (error === "AccessDenied") {
    return "Access was denied by GitHub or the application.";
  }

  return "GitHub sign-in could not be completed. Please try again.";
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const session = await auth();
  const params = await searchParams;
  const callbackUrl = safeCallbackUrl(params.callbackUrl);

  if (session?.user) {
    redirect(callbackUrl);
  }

  const message = errorMessage(params.error);

  return (
    <main className="min-h-screen bg-panel px-4 py-8 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center justify-center">
        <section className="grid w-full max-w-5xl overflow-hidden rounded-md border border-line bg-white shadow-panel lg:grid-cols-[0.82fr_1fr]">
          <div className="flex flex-col justify-center bg-[#1f686a] p-5 text-white sm:p-6 lg:min-h-[420px] lg:p-8">
            <div className="flex items-center gap-3">
              <p className="font-heading text-3xl font-semibold tracking-normal sm:text-4xl lg:text-5xl">ra-agent</p>
            </div>
            
            <p className="mt-2 hidden max-w-sm text-sm leading-5 text-white/75 sm:block sm:text-base lg:mt-3">
              AI agent for finding RA openings, ranking relevance with Gemini, and sending Gmail alerts.
            </p>
          </div>

          <div className="flex items-center justify-center p-6 sm:p-10">
            <div className="w-full max-w-sm">
              <div className="mb-7">
                <div className="flex h-11 w-11 items-center justify-center rounded-md bg-teal-50 text-accent">
                  <LogIn className="h-5 w-5" aria-hidden="true" />
                </div>
                <h2 className="mt-4 font-heading text-2xl font-semibold tracking-normal text-ink">Welcome back</h2>
                <p className="mt-2 text-sm leading-6 text-muted">Use your GitHub account to continue to the ra-agent dashboard.</p>
              </div>

              {message ? (
                <div className="mb-4 flex items-start gap-3 rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <p>{message}</p>
                </div>
              ) : null}

              <div className="grid gap-3">
                {providerMap.map((provider) => (
                  <form
                    key={provider.id}
                    action={async () => {
                      "use server";

                      try {
                        await signIn(provider.id, { redirectTo: callbackUrl });
                      } catch (error) {
                        if (error instanceof AuthError) {
                          redirect(`/login?error=${encodeURIComponent(error.type)}&callbackUrl=${encodeURIComponent(callbackUrl)}`);
                        }

                        throw error;
                      }
                    }}
                  >
                    <button
                      className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md border border-line bg-ink px-4 text-sm font-semibold text-white transition hover:bg-[#253044]"
                      type="submit"
                    >
                      <Github className="h-4 w-4" aria-hidden="true" />
                      Sign in with {provider.name}
                    </button>
                  </form>
                ))}
              </div>

              <p className="mt-5 text-xs leading-5 text-muted">
                You will be redirected to GitHub, then returned to the requested dashboard page.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
