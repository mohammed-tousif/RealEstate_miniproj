# Limitations

These are stated plainly in the report and in the viva. The project is honest about each of them in the UI as well.

## Data
- **All listings are synthetic.** They come from `generate_synthetic_data.py` (seed 42, 306 rows), using invented base
  rates per locality multiplied by type, conversion, layout and road-access factors, a power of area, and log-normal
  noise. No real Hubballi–Dharwad listing or transaction data was used, and no portal was scraped.
- **Asking price, not sale price.** The model's target is the asking price. Asking prices in India often differ from
  registered sale values and from the government guidance value.
- **Coordinates are approximate.** Each listing is placed near a rough locality centre.
- **21 localities in 2 cities.** The schema supports more cities, but the demo covers only Hubballi and Dharwad.

## Price model
- **Good test metrics mostly show the pipeline recovers the generator's formula.** Linear Regression on log(price)
  wins because the generator is multiplicative, which becomes additive after taking logs. Real prices need not follow
  this shape.
- **Unseen localities are poorly predicted.** With localities held out (GroupKFold by locality), the model's MAE was
  ₹36.82 lakh against ₹21.19 lakh for the simple baseline. The API warns when a locality was not in training.
- **Small test set.** 44 test rows; per-locality errors rest on 1–5 rows each, and the 84.1% interval coverage is
  itself uncertain.
- **Feature importance is global.** It describes the model overall, not why one listing got its estimate.

## Recommendations
- **The weights are expert judgement.** The 30/25/20/15/10 weights and the purpose table are design assumptions with
  no buyer feedback behind them. There are no relevance labels, so no Precision@K or NDCG is reported.
- **The evaluation shows the rule behaves as designed**: 0 strict violations, 100% of rule-derived ideal listings in
  the top 5, Kendall's tau 0.94 under ±20% weight changes. It does not show that buyers would agree with the ranking.
- **Straight-line distance.** KNN similarity treats coordinates as location, without roads or travel time.

## Legal and documents
- **Nothing is verified.** Land classification, conversion, layout approval and documents are the seller's
  declarations. Marking a document "verified" is disabled because no authorised verification process exists.
- **Risk flags are rules, not legal review.** They highlight missing declarations; their absence does not mean a
  property is safe to buy.
- **Portal links were checked through secondary sources.** The government sites could not be opened from the build
  environment.
- **Private document upload is deferred.** Only declarations are stored; the free hosting tier has no persistent disk
  for private files.

## Assistant
- **Basic search mode is a keyword parser**, built for the demo questions and common phrasings.
- **The Claude adapter was not tested against the live API** during development (no key was available); it is tested
  against mocked SDK responses, and falls back to Basic search mode on any failure.
- **Grounding is checked for listing ids only.** A model could still misstate a number taken from a tool result; the
  system prompt, labelled tool output and visible cards reduce but do not remove this risk.
- **No server-side chat memory.** The browser sends the last turns with each question.

## Deployment
- **Free tier.** Services sleep when idle (about a minute to wake), uploaded photos are lost on restart or redeploy,
  and the free database expires after Render's free period.
- **In-memory rate limits.** Correct for one instance only.
