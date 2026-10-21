"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { PriceEstimate } from "@/lib/types";
import { Card, Skeleton } from "@/components/ui";
import { EstimateResult } from "./EstimateResult";

/** Detail-page card: the model's estimate for this listing next to its asking price. */
export function PriceCard({ propertyId }: { propertyId: string }) {
  const [e, setE] = useState<PriceEstimate | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    setE(null);
    setError(null);
    api.estimatePrice({ property_id: propertyId }).then(setE).catch(setError);
  }, [propertyId]);

  return (
    <Card className="p-5">
      <h2 className="text-base font-semibold text-ink-900">Indicative price estimate</h2>
      <div className="mt-3">
        {error ? (
          <p className="text-sm text-slate-600">
            {error.status === 503 ? "The price model is not available on this server yet." : error.message}
          </p>
        ) : e ? (
          <EstimateResult e={e} compact />
        ) : (
          <Skeleton className="h-32 w-full" />
        )}
      </div>
    </Card>
  );
}
