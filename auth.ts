import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

const providers = [GitHub];

export const providerMap = [{ id: "github", name: "GitHub" }];

export const { auth, handlers, signIn, signOut } = NextAuth({
  providers,
  pages: {
    signIn: "/login",
  },
});
