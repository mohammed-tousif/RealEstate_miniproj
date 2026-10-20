"use client";

// Leaflet + OpenStreetMap tiles (low-volume demo use, attribution shown).
// Loaded only in the browser via next/dynamic (see MapView).
import Link from "next/link";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";
import type { PropertySummary } from "@/lib/types";
import { formatINRShort } from "@/lib/format";

const COLORS: Record<string, string> = {
  residential_plot: "#0f766e",
  independent_house: "#0369a1",
  agricultural_land: "#4d7c0f",
  commercial_plot: "#b45309",
  commercial_building: "#c2410c",
};

export const HUBBALLI_DHARWAD: [number, number] = [15.41, 75.07];

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) map.fitBounds(points, { padding: [30, 30], maxZoom: 14 });
    else if (points.length === 1) map.setView(points[0], 14);
  }, [map, points]);
  return null;
}

export default function PropertyMap({ items, height = 480, single = false }: { items: PropertySummary[]; height?: number; single?: boolean }) {
  const pts = items
    .filter((p) => p.latitude && p.longitude)
    .map((p) => ({ p, pos: [Number(p.latitude), Number(p.longitude)] as [number, number] }));
  return (
    <div style={{ height }} className="overflow-hidden rounded-xl border border-slate-200">
      <MapContainer center={pts[0]?.pos ?? HUBBALLI_DHARWAD} zoom={single ? 14 : 11} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {!single && <FitBounds points={pts.map((x) => x.pos)} />}
        {pts.map(({ p, pos }) => (
          <CircleMarker key={p.id} center={pos} radius={single ? 10 : 7} pathOptions={{ color: "#fff", weight: 1.5, fillColor: COLORS[p.property_type] ?? "#334155", fillOpacity: 0.9 }}>
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{formatINRShort(p.asking_price_inr)}</p>
                <p>{p.title}</p>
                {!single && <Link href={`/properties/${p.id}`} className="text-brand-700 underline">View details</Link>}
                <p className="mt-1 text-xs text-slate-500">Approximate location</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
