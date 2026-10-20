# M5 — Conversational assistant: status summary

Date: 2026-10-18

## Completed functionality
- **Provider interface** (`backend/app/ai/provider.py`). The orchestrator talks to an `LLMProvider` protocol with one
  method, `run_turn(system, transcript, tools)`, so tests can script a fake model and another vendor could be added
  without touching the tools.
  - `ClaudeProvider` uses the Anthropic Python SDK (`anthropic==1.15.0`), model `claude-opus-5-5` with effort `low`,
    a 60-second timeout and one SDK retry. Model and effort come from `LLM_MODEL` and `LLM_EFFORT`.
  - It returns the model's content blocks unchanged into the next request, so tool calls and reasoning stay intact.
  - A refusal, a truncated answer (`max_tokens`), rate limiting, an API error or a network error all raise
    `ProviderError`, which sends the question to Basic search mode with a notice.
  - Without `ANTHROPIC_API_KEY` no provider is created and every answer comes from Basic search mode.
- **Nine read-only tools** (`backend/app/ai/tools.py`), each with a Pydantic input model whose JSON schema is sent to
  the model:
  - `search_properties`, `get_property_details`, `recommend_properties`, `predict_property_price`,
    `compare_properties`, `explain_ranking`, `get_document_information`, `get_location_summary`, `explain_term`.
  - They call the same services as the REST API, with the caller's own visibility: a guest never sees a pending
    listing, and its owner does.
  - Invalid arguments come back to the model as `invalid_arguments` with the validation errors. A listing that does
    not exist or is hidden comes back as `not_found_or_not_visible`. Neither reaches the user as a server error.
  - No tool can write anything.
- **Orchestrator** (`backend/app/ai/orchestrator.py`):
  - user message and the last 10 history turns → model with tool schemas → tool calls, at most 5 rounds → answer
    → grounding check → answer with property cards, mode label and disclaimers.
  - **Grounding check.** Every listing id in the answer must have been returned by a tool during this question. If
    not, the answer is replaced by the rule-based answer and marked `grounded: false` with a notice.
  - **Prompt-injection resistance.** Tool output is wrapped in `<listing_data tool="…">…</listing_data>`. The system
    prompt says that text inside it is data and never an instruction. Seller-written text has any copy of the wrapper
    tags removed, so a description cannot close the wrapper early.
  - The system prompt requires that listing data, ML estimates and suitability scores be labelled as such, and that
    document statuses be described as the seller's claims.
- **Basic search mode** (`backend/app/ai/basic_mode.py`). This is a rule-based parser that calls the same tools and
  fills templated answers. It is labelled "Basic search mode – AI unavailable" in the UI.
  - It understands budgets in lakh, crore, ₹ and plain numbers, including "under" and "above" forms.
  - It recognises areas in sq ft, sq m, gunta and acre, the property types, Hubballi and Dharwad and the locality
    names, the four objectives, and listing ids from links.
  - Intents, in priority order: why one listing ranks higher, compare, price estimate, document status, listing
    details, which documents to ask for, glossary terms, locality summary, help, recommend, search.
- **Glossary** (`backend/app/ai/glossary.py`): approved definitions only, reused from the document guidance already
  shown on listing pages, plus area units, land terms, guidance value, stamp duty and the platform's own scores.
  Unknown terms get "no approved definition" rather than a made-up one.
  - Official portal links: Bhoomi `https://landrecords.karnataka.gov.in`, Kaveri `https://kaveri.karnataka.gov.in`,
    RERA `https://rera.karnataka.gov.in` and HDMC `https://www.hdmc.mrc.gov.in`.
  - The government sites themselves could not be opened from the build environment, so these addresses were checked
    against secondary sources: RERA through a lender's guide, and HDMC through Wikipedia's reference list. Check them
    once more before a public demo.
- **Rate limiting** (`backend/app/ai/rate_limit.py`): 12 assistant requests per minute per client, kept in memory.
  Behind Render's proxy the client is read from `X-Forwarded-For` (`TRUST_PROXY_HEADERS=true`).
- **API:** `POST /api/v1/ai/chat`. `/health` now reports `llm_configured`.
- **Risk flags** (`backend/app/services/risk_flags.py`). These are rule-based warnings on listing details:
  - high: missing key documents, conversion not established, unapproved layout, no road access;
  - medium: road access unknown, asking price below the model's range;
  - low: asking price above the model's range, no map location.
  - On the 275 approved demo listings, 213 have missing key documents and 45 have no flag.
- **Frontend:**
  - A **Chat page** (`/chat`, "Assistant" in the navigation) with suggestions, a mode badge, the tools used, a
    notice line, safe rich text (links, bold, lists; no HTML), listing mini-cards, disclaimers and retry on error.
  - `/chat?ask=…` pre-fills and sends a question. The Advisor preferences saved in the browser are sent with each
    question, so rankings are explained against them.
  - The **listing page** shows the risk flags, plus links to "Ask the assistant about this listing" and "Ask whether
    its documents are verified".
  - The **compare page** links to "Ask the assistant why one ranks higher".

## Defaults chosen where the spec left a detail open
- **Model.** The spec's risk table asks for a small model by default. The configured default is `claude-opus-5-5`
  with effort `low`, at most 5 tool rounds and 12 requests per minute, which bounds cost per question. `LLM_MODEL`
  can name a smaller model. No key is needed for the demo, because Basic search mode covers steps 12–15.
- **Ranking explanations** use the buyer's stated preferences when the question gives them, otherwise the saved
  Advisor preferences. When the assistant is asked, strictness is relaxed, so the answer can explain why a listing
  scores lower instead of only saying it is excluded.
- **History** is sent by the browser, not stored on the server. This keeps the API stateless; the last 10 turns are
  used.

## Files created or changed
- **Created:**
  - backend/app/ai/: provider.py, tools.py, orchestrator.py, basic_mode.py, glossary.py, format.py, rate_limit.py
  - backend/app/schemas/chat.py, backend/app/api/v1/routes/chat.py, backend/app/services/risk_flags.py
  - backend/tests/test_chat.py, backend/tests/test_risk_flags.py
  - frontend/src/app/chat/page.tsx, frontend/src/components/chat/RichText.tsx
  - frontend/e2e/chat.spec.ts, frontend/e2e/demo.spec.ts
- **Changed:**
  - backend: core/config.py (LLM and rate-limit settings), router.py, routes/system.py, routes/auth.py,
    schemas/property.py, services/property_service.py, services/recommendation_service.py (shared `match_details`),
    requirements.txt, tests/conftest.py
  - frontend: types.ts, api.ts, Navbar, the listing page, the compare page

## Tests performed (actually run)
| Check | Result |
|---|---|
| Backend pytest on SQLite, Python 3.11 | 132 passed (39 new since M4) |
| Backend pytest on PostgreSQL 16 | 132 passed |
| New assistant tests cover | tool selection with a scripted fake model; grounding check replacing an answer that cites an id no tool returned; invalid tool arguments and unknown tools; a prompt-injection description wrapped as data and its fake closing tag removed; a pending listing hidden from guests but visible to its owner; a price question with the model unloaded and loaded; provider failure → Basic search mode with a notice; the tool-round cap; history role alternation; Basic search for search, no matches, recommend, explain ranking, document verification and unknown ids; the budget, area and type parser (parametrised); INR formatting; rate limit → 429; request validation; `llm_configured`; Render's `postgresql://` URL normalisation; the Claude adapter's request shape and refusal handling, with a mocked SDK response; tool schemas |
| Risk flag tests | 4 passed |
| Frontend `tsc`, `next lint`, `vitest` | clean, clean, 11 passed (3 new for the proxy) |
| Playwright against the live backend and a production build | 17 passed (4 new: three on the Chat page, plus the full 15-step demo) |

**Not tested:** a live call to the Anthropic API. No key was available while building, so the adapter is tested only
against mocked SDK responses. The first question after setting `ANTHROPIC_API_KEY` is the real test. If it fails, the
answer falls back to Basic search mode and the API log says why.

## Outstanding issues
- Basic search mode is a keyword parser. It handles the demo questions and common phrasings, not free-form language.
- Rate limits are per process, which is correct for one Render instance, but would need a shared store for more.
- The assistant has no memory between page loads.

## Next milestone
**M6 — Hardening, documentation and academic material** (see `M6-hardening.md`).
