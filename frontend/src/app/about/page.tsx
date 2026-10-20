import type { Metadata } from "next";
import { MethodReport } from "@/components/advisor/MethodReport";
import { ModelReport } from "@/components/price/ModelReport";

export const metadata: Metadata = { title: "Methodology" };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-6 text-slate-700">{children}</div>
    </section>
  );
}

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Methodology and limitations</h1>
        <p className="mt-2 text-slate-600">
          PropWise AI is a college mini-project. This page explains what each part of the system does, where the data
          comes from, and what it cannot tell you.
        </p>
      </div>

      <Section title="Purpose">
        <p>
          Help buyers and small investors in Hubballi–Dharwad discover land and property, judge how well each listing
          fits their needs, and see which legal documents still need independent checking.
        </p>
      </Section>

      <Section title="What kind of technology does what">
        <ul className="list-disc space-y-1 pl-5">
          <li><strong>Traditional software:</strong> listings, search and filters, accounts, seller submissions and admin review.</li>
          <li><strong>Algorithmic recommendation:</strong> a transparent weighted suitability score with hard constraints. It is not a trained model.</li>
          <li><strong>Supervised machine learning:</strong> a regression model that estimates an indicative asking price, trained and tested on held-out data.</li>
          <li><strong>Generative AI:</strong> an assistant that turns questions into backend searches and explains the results (Milestone 5).</li>
        </ul>
      </Section>

      <Section title="Data sources">
        <p>
          <strong>Most listings in the system are synthetic.</strong> They come from a documented generator
          (fixed random seed) that uses invented base rates per locality and simple multipliers for land
          classification, conversion, layout approval and road access, plus random noise. Locality names are real
          places; their map positions are rough approximations.
        </p>
        <p>
          <strong>A small set of real listings</strong> (land and plots in the Hubballi and Dharwad taluks) was copied by hand
          from public listing pages on 1acre.in, whose robots rules allow those pages. Each keeps its source link and the date it
          was copied, is marked &ldquo;Real listing&rdquo;, and is owned in PropWise by an import account, not by the seller. Only
          property facts were copied: no seller names, phone numbers or e-mails. Anything the source does not state (land
          classification, conversion, approvals, documents) is shown as unknown rather than guessed, and nothing was verified.
        </p>
      </Section>

      <Section title="Land classification and documents">
        <p>
          Property type, land classification, conversion status, layout approval and documents are recorded
          separately because they mean different things. For example, &ldquo;agricultural land&rdquo; is a land-use
          classification, while a DC conversion order is a document permitting non-agricultural use.
        </p>
        <p>
          Every document has one of six statuses: Not provided, Provided – unverified, Verification pending,
          Verified, Not applicable, or Unknown. PropWise has no authorised verification process, so no document is
          ever shown as Verified. An uploaded or declared Encumbrance Certificate shows that a document was provided;
          it does not establish clear title.
        </p>
        <p>
          The documentation figure on each listing is the share of relevant documents the seller declared, with key
          documents (RTC, EC, sale deed, conversion order, layout approval) counted double.
        </p>
      </Section>

      <Section title="How recommendations are calculated">
        <MethodReport />
      </Section>

      <Section title="How the price model is trained">
        <ModelReport />
      </Section>

      <Section title="Legal and investment disclaimer">
        <p>
          PropWise AI provides property research and indicative analysis only. It does not verify ownership or title,
          does not give legal or financial advice, and does not promise returns. Always inspect records with the
          relevant authorities (for example Karnataka&rsquo;s land-records and registration services, Karnataka RERA,
          and the local planning authority) and consult qualified professionals before buying.
        </p>
      </Section>
    </div>
  );
}
