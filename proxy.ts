import { auth } from "@/auth";
import { isDevAuthBypassEnabled } from "@/lib/auth-dev";

export const proxy = auth((req) => {
  if (isDevAuthBypassEnabled()) {
    return;
  }

  const { pathname, search } = req.nextUrl;

  if (!req.auth && pathname !== "/login") {
    const loginUrl = new URL("/login", req.nextUrl.origin);
    loginUrl.searchParams.set("callbackUrl", `${pathname}${search}`);
    return Response.redirect(loginUrl);
  }
});

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
