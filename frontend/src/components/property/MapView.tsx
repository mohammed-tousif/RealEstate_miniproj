"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui";

export const MapView = dynamic(() => import("./PropertyMap"), {
  ssr: false,
  loading: () => <Skeleton className="h-[480px] w-full rounded-xl" />,
});
