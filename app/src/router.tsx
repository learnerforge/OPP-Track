import type { ReactNode } from "react";

/**
 * Minimal history-API router (no external deps, keeps the frozen src/ tree and
 * root package.json untouched). Deep links work because vercel.json already
 * rewrites unknown paths to index.html.
 */
export function navigate(to: string): void {
  if (window.location.pathname === to) return;
  window.history.pushState({}, "", to);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export interface RouteProps {
  path: string;
  element: ReactNode;
}

/** Declares a route. Rendered only by <Routes>, which reads `path`/`element`. */
export function Route(_props: RouteProps): ReactNode {
  return null;
}

/** Renders the first child <Route> whose path matches, else null. */
export function Routes({
  path,
  children,
}: {
  path: string;
  children: ReactNode;
}) {
  const routes = Array.isArray(children) ? children : [children];
  for (const child of routes) {
    if (!child || typeof child !== "object" || !("props" in child)) continue;
    const props = (child as { props: RouteProps }).props;
    if (props.path === path) return <>{props.element}</>;
  }
  return null;
}
