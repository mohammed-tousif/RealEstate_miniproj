# M4 — Recommendation engine and comparison: status summary

Date: 2026-10-15

## Completed functionality
- **Engine `weighted-v1`** (`backend/app/ml/recommendation/`). It is a transparent scoring rule, not a trained model.
  - **Filter.** Only approved listings are considered. Budget, property type, minimum area and location become hard
    filters only when the buyer marks them strict. Each exclusion is counted by reason, so an empty result says which
    requirement to relax. A non-strict budget allows listings up to 10% over the maximum, scored down linearly.
  - **Score.** There are five factors, each scored 0–1, with default weights budget 30, location 25, purpose 20,
    road access 15 and documents declared 10.
    - The buyer's importance setting multiplies each weight: ×2, ×1, ×0.5 or ×0.
    - A factor the buyer gave no preference for is left out, and the remaining weights are rescaled to 100.
    - Missing data (unknown road access, undeclared documents) scores 0 for that factor, and every result reports
      `data_coverage`, the share of the weighting backed by known fields.
  - **Purpose table.** This sets how well each property type suits building a house, long-term investment, farming
    or commercial use. The score is reduced when the land classification, conversion or layout approval does not fit
    the purpose. All values are declared claims; nothing is treated as verified.
  - **Explain.** Reasons, trade-offs, missing information and "verify independently" items are templated from the
    same factor numbers, so the text cannot disagree with the score.
  - **Ties** break on documents declared, then lower price, then id, so the same input always gives the same order.
  - **Price check.** Each result says whether the asking price is below, within or above the M3 model's indicative
    range, labelled as a demonstration model and not a valuation.
  - Every call is logged in `recommendation_history` with the engine version.
- **KNN similar listings** (`knn.py`) use standardised log price, log area, coordinates, road access and documentation
  score, plus one-hot city and property type (type weighted ×3). Each neighbour shows what it has in common with the listing.
- **API:**
  - `POST /api/v1/recommendations`
  - `GET /api/v1/recommendations/config` (all weights and tables, which the Methodology page renders)
  - `POST /api/v1/properties/compare` (2–3 listings, with match score, rank and any failed strict requirement)
  - `GET /api/v1/properties/{id}/similar`
- **Frontend:**
  - An **Advisor** page (`/advisor`) in the navigation. It has a lakh/crore budget input, strict toggles, an objective,
    preferred localities, a minimum area in Indian units and importance settings. Its demo button runs the ₹25 lakh
    scenario.
  - Each result card shows the score, the factor bars, its explanations and the price check.
  - Preferences are kept in the browser, and saved to the account when the buyer is signed in.
  - **Compare** now has a "Match for your preferences" row with score and rank, using the last Advisor preferences.
    A cell is highlighted only when one listing is clearly ahead.
  - **Listing page:** "Similar listings" now uses KNN in place of the M2 search rule.
  - **Methodology page:** a live "How recommendations are calculated" section with the weights, the purpose table and
    how the method was checked.

## Evaluation (synthetic data; see `ml/reports/recommender_evaluation.md`)
`scripts/evaluate_recommender.py` runs 15 scripted buyer scenarios against 275 approved synthetic listings, using a
temporary copy of the demo database. There are no genuine relevance labels, so no Precision@K is reported.

| Top 5, mean over scenarios | Weighted engine | Cheapest first | Newest first |
|---|---|---|---|
| Available rule-derived "ideal" listings that reached the top 5 | 100% | 0% | 13% |
| Documentation completeness | 76% | 62% | 58% |
| Road access known | 100% | 96% | 94% |

- **Strict requirements:** an independent checker found 0 violations in any scenario. A randomised test over many
  preference combinations also found none.
- **Rule agreement:** the engine agrees with the rule-derived expectations on 99% of ideal/non-ideal pairs. That figure
  is partly true by construction, since both follow the same specification.
- **Stability:** Kendall's tau is 0.94 under ±20% random weight changes.
- **KNN towards a preference vector** has no notion of strict requirements, and it broke them in most scenarios. So KNN
  is used only for "similar listings", and the weighted engine for the Advisor.
- **Caveat:** these checks show the rule behaves as designed. They do not show that buyers would agree with it.

## Defaults chosen where the spec left a detail open
- Budget and type are strict by default; location and area are not. This matches how buyers usually state a hard
  budget but soft location wishes.
- The full budget score applies from 60% to 100% of the maximum. A listing far below budget scores lower, because it
  is often smaller or less suitable than the buyer planned for.
- Choosing only cities scores any locality in them as fully preferred. Choosing localities scores other localities in
  the same city 0.7.
- The default weights (30/25/20/15/10) are design assumptions, not learned. The Methodology page shows them, and the
  stability figure shows how much the order depends on them.

## Files created or changed
- **Created:**
  - backend/app/ml/recommendation/: `__init__.py`, config.py, engine.py, knn.py
  - backend/app/schemas/recommendation.py, backend/app/services/recommendation_service.py,
    backend/app/api/v1/routes/recommendations.py
  - backend/scripts/evaluate_recommender.py, backend/tests/test_recommendations.py
  - ml/reports/recommender_evaluation.md and .json
  - frontend/src/app/advisor/page.tsx, frontend/src/lib/advisor.ts
  - frontend/src/components/advisor/: MatchDetails.tsx, RecommendationCard.tsx, MethodReport.tsx
  - frontend/e2e/advisor.spec.ts
- **Changed:**
  - backend/app/api/v1/router.py
  - frontend: types.ts, api.ts, Navbar, the compare page, the property detail page, the about page
  - README, the requirements checklist

## Tests performed (actually run)
| Check | Result |
|---|---|
| Backend pytest on SQLite, Python 3.13 | 93 passed (23 new) |
| Backend pytest on PostgreSQL 16 | 93 passed |
| Backend pytest on Python 3.11 | 93 passed |
| New tests cover | strict and non-strict budget, minimum budget, type, location and area; missing road access and undeclared documents scoring 0; "doesn't matter" removing a factor and renormalising; factors without a preference ignored; all factors unimportant → 422; purpose (converted plot for a house, farmland for farming); score equals the weighted sum; explanations match the record; low factors become trade-offs; identical input gives identical order with tie-breaks; empty result counts exclusions; randomised preferences never break a strict requirement; recommend, compare (including a hidden pending listing → 404) and similar APIs; validation errors |
| Frontend `tsc`, `next lint`, `vitest` | clean, clean, 8 passed |
| `next build` | succeeded, 15 routes |
| Playwright against live backend + production build | 13 passed (3 new: the ₹25 lakh demo through to compare with match ranks, input validation and an empty result, KNN similar listings and the Methodology section) |
| Recommendation evaluation script | ran; results above |

Screenshots of the Advisor page (desktop and phone width), a result card and the compare page were reviewed. Fixes
that followed:
- Cards show sq ft next to a sq m or gunta area.
- Compare ranks ties with the same tie-break as the Advisor and no longer highlights a tied score.
- The Methodology text now explains the city-only location score.

## Outstanding issues
- Weights and the purpose table are expert judgement, not learned from buyer behaviour. There is no feedback data to
  tune them.
- The Explore page still sorts by price, area and date. Ranking by suitability lives in the Advisor.
- The KNN distance treats straight-line distance as location similarity. It does not know about roads or travel time.
- All results run on synthetic listings.

## Next milestone
**M5 — Conversational assistant:**
- Claude behind a provider interface, using read-only validated tools (search, details, estimate, recommend);
- a grounding check so it never invents listings or prices;
- prompt-injection resistance;
- a labelled basic search mode when no LLM is configured;
- rate limiting and the Chat page.
