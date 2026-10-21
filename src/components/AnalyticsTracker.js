"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { TRACKED_ROUTES, track } from "@/lib/analytics";

export default function AnalyticsTracker() {
  const pathname = usePathname();

  useEffect(() => {
    if (TRACKED_ROUTES.has(pathname)) track("page_view", pathname);
  }, [pathname]);

  return null;
}
