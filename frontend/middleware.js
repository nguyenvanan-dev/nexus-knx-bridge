import { NextResponse } from "next/server";

export function middleware(request) {
  const token = request.cookies.get("knx_token")?.value;
  const isLoginPage = request.nextUrl.pathname.startsWith("/login");
  const isApiRoute = request.nextUrl.pathname.startsWith("/api/");
  const isAuthApi = request.nextUrl.pathname.startsWith("/api/auth/");

  // Allow auth APIs to pass through without token
  if (isAuthApi) {
    return NextResponse.next();
  }

  // If user has no token and tries to access a protected page
  if (!token && !isLoginPage) {
    // If it's an API request, return 401
    if (isApiRoute) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    // Otherwise redirect to login
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // If user has token and visits login page, redirect to dashboard
  if (token && isLoginPage) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.svg|.*\\.png|.*\\.jpg).*)',
  ],
};
