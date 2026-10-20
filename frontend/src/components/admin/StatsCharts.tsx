"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AdminStats } from "@/lib/types";
import { Card } from "@/components/ui";

function Chart({ title, data }: { title: string; data: { name: string; value: number }[] }) {
  return (
    <Card className="p-4">
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <div className="mt-3 h-60">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: -20, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#475569" }} interval={0} angle={-25} textAnchor="end" height={56} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#475569" }} />
            <Tooltip cursor={{ fill: "#f1f5f9" }} />
            <Bar dataKey="value" fill="#0f766e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

const toData = (o: Record<string, number>, labels?: Record<string, string>) =>
  Object.entries(o).map(([k, v]) => ({ name: labels?.[k] ?? k.replace(/_/g, " "), value: v }));

export function StatsCharts({ stats, typeLabels }: { stats: AdminStats; typeLabels?: Record<string, string> }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Chart title="Listings by review status" data={toData(stats.listings_by_status)} />
      <Chart title="Listings by property type" data={toData(stats.listings_by_type, typeLabels)} />
      <Chart title="Listings by city" data={toData(stats.listings_by_city)} />
    </div>
  );
}
