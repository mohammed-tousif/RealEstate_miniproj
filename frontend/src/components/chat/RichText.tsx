import Link from "next/link";
import type { ReactNode } from "react";

// Renders the small subset of Markdown the assistant uses: paragraphs, "- " lists, **bold**,
// [text](/properties/id) links and bare https links. Everything else is shown as plain text,
// so nothing in an answer can inject HTML.

const INLINE = /\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|(https:\/\/[^\s)]+)/g;

export function inline(text: string, keyBase = ""): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let i = 0;
  for (const m of text.matchAll(INLINE)) {
    const at = m.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    const key = `${keyBase}-${i++}`;
    if (m[1] !== undefined) {
      const href = m[2];
      if (href.startsWith("/")) out.push(<Link key={key} href={href} className="font-medium text-brand-700 underline hover:text-brand-800">{m[1]}</Link>);
      else if (href.startsWith("https://")) out.push(<a key={key} href={href} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">{m[1]}</a>);
      else out.push(m[1]);
    } else if (m[3] !== undefined) {
      out.push(<strong key={key}>{m[3]}</strong>);
    } else if (m[4] !== undefined) {
      out.push(<a key={key} href={m[4]} target="_blank" rel="noopener noreferrer" className="break-all text-brand-700 underline">{m[4]}</a>);
    }
    last = at + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const BULLET = /^\s*([-*]|\d+\.)\s+/;

type Segment = { kind: "p"; lines: string[] } | { kind: "ul"; items: string[][] };

function segments(text: string): Segment[] {
  const out: Segment[] = [];
  for (const raw of text.trim().split("\n")) {
    const last = out[out.length - 1];
    if (!raw.trim()) {
      out.push({ kind: "p", lines: [] });
    } else if (BULLET.test(raw)) {
      const item = [raw.replace(BULLET, "")];
      if (last?.kind === "ul") last.items.push(item);
      else out.push({ kind: "ul", items: [item] });
    } else if (last?.kind === "ul" && /^\s{2,}\S/.test(raw)) {
      last.items[last.items.length - 1].push(raw.trim());
    } else if (last?.kind === "p") {
      last.lines.push(raw);
    } else {
      out.push({ kind: "p", lines: [raw] });
    }
  }
  return out.filter((s) => (s.kind === "p" ? s.lines.length > 0 : true));
}

export function RichText({ text }: { text: string }) {
  return (
    <div className="space-y-3">
      {segments(text).map((seg, bi) =>
        seg.kind === "ul" ? (
          <ul key={bi} className="list-disc space-y-1.5 pl-5">
            {seg.items.map((it, ii) => (
              <li key={ii}>
                {inline(it[0], `${bi}-${ii}`)}
                {it.slice(1).map((sub, si) => (
                  <span key={si} className="block text-slate-600">{inline(sub, `${bi}-${ii}-${si}`)}</span>
                ))}
              </li>
            ))}
          </ul>
        ) : (
          <p key={bi} className="whitespace-pre-line">{inline(seg.lines.join("\n"), String(bi))}</p>
        ),
      )}
    </div>
  );
}
