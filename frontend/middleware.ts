import { type NextRequest, NextResponse } from "next/server";

const PASSWORD_COOKIE = "basis_auth";
const HARDCODED_PASSWORD = "basis";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow static assets and API auth routes
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api/auth") ||
    pathname === "/favicon.ico" ||
    pathname === "/login"
  ) {
    return NextResponse.next();
  }

  const cookie = request.cookies.get(PASSWORD_COOKIE);
  if (cookie?.value === HARDCODED_PASSWORD) {
    return NextResponse.next();
  }

  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/auth).*)"],
};
