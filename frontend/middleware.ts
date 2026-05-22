import { type NextRequest, NextResponse } from "next/server";
import { updateSession } from "@/utils/supabase/middleware";

const PASSWORD_COOKIE = "basis_auth";
const HARDCODED_PASSWORD = "basis";

export async function middleware(request: NextRequest) {
  // Refresh Supabase session first
  const response = await updateSession(request);

  const { pathname } = request.nextUrl;

  // Allow static assets, API routes, and login page
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api/") ||
    pathname === "/favicon.ico" ||
    pathname === "/login"
  ) {
    return response;
  }

  const cookie = request.cookies.get(PASSWORD_COOKIE);
  if (cookie?.value === HARDCODED_PASSWORD) {
    return response;
  }

  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/auth).*)",],
};
