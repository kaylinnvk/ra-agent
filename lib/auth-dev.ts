export function isDevAuthBypassEnabled() {
  return process.env.NODE_ENV === "development" && process.env.DISABLE_AUTH_IN_DEV === "true";
}

export function getDevSession() {
  return {
    user: {
      name: "Local developer",
      email: "dev@localhost",
      image: null,
    },
    expires: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
  };
}
