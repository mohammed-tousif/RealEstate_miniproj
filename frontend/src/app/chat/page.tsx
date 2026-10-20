"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { loadPreferences } from "@/lib/advisor";
import { api, ApiError } from "@/lib/api";
import { formatINRShort } from "@/lib/format";
import type { ChatResponse, ChatTurn, PropertySummary } from "@/lib/types";
import { Badge, Button, PageHeader, OriginBadge, Spinner, cx } from "@/components/ui";
import { RichText } from "@/components/chat/RichText";

type Message =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; reply: ChatResponse }
  | { role: "error"; content: string; retry: string };

const SUGGESTIONS = [
  "Residential plots in Dharwad under 25 lakh",
  "Farmland near Hubballi for long-term investment, budget 30 lakh, at least 2 acres",
  "What is an RTC and where do I check it?",
  "Which documents should I ask for when buying a house?",
  "Average asking price of plots in Saptapur",
];

function ModeBadge({ mode }: { mode: ChatResponse["mode"] }) {
  return mode === "llm" ? (
    <Badge tone="violet" title="Answer written by the AI model from tool results">AI assistant</Badge>
  ) : (
    <Badge tone="slate" title="Rule-based search over the same tools; no AI model was used">Basic search mode – AI unavailable</Badge>
  );
}

function MiniCard({ p }: { p: PropertySummary }) {
  return (
    <Link
      href={`/properties/${p.id}`}
      className="block min-w-[220px] max-w-[260px] shrink-0 rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-sm hover:border-brand-300"
    >
      <p className="font-semibold text-slate-900">
        {formatINRShort(p.asking_price_inr)} <span className="text-xs font-normal text-slate-500">Listing data</span>
      </p>
      <p className="mt-0.5 line-clamp-2 font-medium text-slate-800">{p.title}</p>
      <p className="mt-1 text-xs text-slate-500">{p.locality.locality_name}, {p.locality.city}</p>
      {(p.is_synthetic || p.source_url) && <div className="mt-2"><OriginBadge p={p} /></div>}
    </Link>
  );
}

function ChatInner() {
  const params = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const asked = useRef(false);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || busy) return;
    const history: ChatTurn[] = messages
      .filter((m): m is Exclude<Message, { role: "error" }> => m.role !== "error")
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.content.slice(0, 4000) }));
    setMessages((ms) => [...ms.filter((m) => m.role !== "error"), { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    try {
      const reply = await api.chat(message, history, loadPreferences());
      setMessages((ms) => [...ms, { role: "assistant", content: reply.answer, reply }]);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Something went wrong.";
      setMessages((ms) => [...ms.slice(0, -1), { role: "error", content: msg, retry: message }]);
      setInput(message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const ask = params.get("ask");
    if (ask && !asked.current) {
      asked.current = true;
      void send(ask);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <PageHeader
        title="Property assistant"
        subtitle="Ask in plain language. Answers come only from PropWise's own listings, price model and approved definitions. Your Advisor preferences, if set, are used to explain rankings."
      />
      <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50">
        <div className="max-h-[65vh] min-h-[320px] space-y-4 overflow-y-auto p-4" aria-live="polite" data-testid="chat-log">
          {messages.length === 0 && (
            <div className="py-6 text-center">
              <p className="text-sm text-slate-600">Try one of these:</p>
              <div className="mt-3 flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => void send(s)}
                    className="rounded-full border border-brand-200 bg-white px-3 py-1.5 text-sm text-brand-800 hover:bg-brand-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-brand-700 px-4 py-2 text-sm text-white">{m.content}</div>
              </div>
            ) : m.role === "error" ? (
              <div key={i} role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                {m.content}{" "}
                <button className="font-medium underline" onClick={() => { setMessages((ms) => ms.filter((x) => x !== m)); void send(m.retry); }}>
                  Retry
                </button>
              </div>
            ) : (
              <div key={i} className="flex justify-start" data-testid="assistant-message">
                <div className="w-full max-w-[92%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-800 shadow-sm">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <ModeBadge mode={m.reply.mode} />
                    {m.reply.tool_calls.length > 0 && (
                      <span className="text-xs text-slate-500">Used: {m.reply.tool_calls.map((t) => t.replace(/_/g, " ")).join(", ")}</span>
                    )}
                  </div>
                  {m.reply.notice && <p className="mb-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">{m.reply.notice}</p>}
                  <RichText text={m.content} />
                  {m.reply.properties.length > 0 && (
                    <div className="-mx-1 mt-3 flex gap-2 overflow-x-auto px-1 pb-1">
                      {m.reply.properties.map((p) => <MiniCard key={p.id} p={p} />)}
                    </div>
                  )}
                  <ul className="mt-3 space-y-0.5 border-t border-slate-100 pt-2 text-xs text-slate-500">
                    {m.reply.disclaimers.map((d) => <li key={d}>{d}</li>)}
                  </ul>
                </div>
              </div>
            ),
          )}
          {busy && (
            <div className="flex items-center gap-2 text-sm text-slate-500"><Spinner className="h-4 w-4" /> Looking that up…</div>
          )}
          <div ref={endRef} />
        </div>
        <form
          className="flex gap-2 border-t border-slate-200 bg-white p-3"
          onSubmit={(e) => { e.preventDefault(); void send(input); }}
        >
          <label htmlFor="chat-input" className="sr-only">Your question</label>
          <input
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={1000}
            placeholder="e.g. Plots in Dharwad under 25 lakh"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200"
          />
          <Button type="submit" loading={busy} disabled={!input.trim()}>Send</Button>
        </form>
      </div>
      <p className={cx("mt-3 text-xs text-slate-500")}>
        The assistant can only read listings and run the price model; it cannot change anything. Most listings are synthetic
        demonstration data; listings marked real are unverified third-party asking prices. Not legal or financial advice.
      </p>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-8"><Spinner /></div>}>
      <ChatInner />
    </Suspense>
  );
}
