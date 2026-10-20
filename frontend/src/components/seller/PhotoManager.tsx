"use client";

import { useRef, useState } from "react";
import { api, ApiError, mediaUrl } from "@/lib/api";
import type { PropertyDetail } from "@/lib/types";
import { Alert, Button, Card } from "@/components/ui";

const MAX_MB = 5;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

export function PhotoManager({ p, onChange }: { p: PropertyDetail; onChange: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = async (files: FileList | null) => {
    if (!files?.length) return;
    setError(null);
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        if (!TYPES.includes(file.type)) throw new Error(`${file.name}: only JPEG, PNG or WebP images are allowed.`);
        if (file.size > MAX_MB * 1024 * 1024) throw new Error(`${file.name}: images must be ${MAX_MB} MB or smaller.`);
        await api.uploadImage(p.id, file);
      }
      onChange();
    } catch (e) {
      setError((e as ApiError).message);
      onChange();
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  const remove = async (imageId: number) => {
    try {
      await api.deleteImage(p.id, imageId);
      onChange();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  return (
    <Card className="space-y-4 p-5">
      <div>
        <h2 className="font-semibold">Photos</h2>
        <p className="text-sm text-slate-500">Upload only photos you took or have permission to use. JPEG, PNG or WebP, up to {MAX_MB} MB each, 10 per listing.</p>
      </div>
      {p.images.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {p.images.map((im) => (
            <div key={im.id} className="group relative aspect-[4/3] overflow-hidden rounded-lg border border-slate-200">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={mediaUrl(im.url) ?? ""} alt="Listing photo" className="h-full w-full object-cover" />
              <button onClick={() => remove(im.id)} className="absolute right-1 top-1 rounded bg-white/90 px-2 py-0.5 text-xs text-red-700 shadow">Remove</button>
            </div>
          ))}
        </div>
      )}
      <input ref={input} type="file" accept={TYPES.join(",")} multiple className="hidden" onChange={(e) => upload(e.target.files)} aria-label="Upload photos" />
      <Button variant="secondary" onClick={() => input.current?.click()} loading={busy} disabled={p.images.length >= 10}>Upload photos</Button>
      {error && <Alert tone="red">{error}</Alert>}
    </Card>
  );
}
