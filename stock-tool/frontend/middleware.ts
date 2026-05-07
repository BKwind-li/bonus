import { NextRequest, NextResponse } from "next/server"

const PUBLIC_PATHS = ["/login"]

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next()

  // Token is in localStorage (client-side), middleware can only read cookies.
  // We use a cookie mirror for SSR guard.
  const token = req.cookies.get("stock_tool_token")?.value
  if (!token) {
    return NextResponse.redirect(new URL("/login", req.url))
  }
  return NextResponse.next()
}

export const config = { matcher: ["/((?!_next|favicon.ico|sw.js).*)"] }
