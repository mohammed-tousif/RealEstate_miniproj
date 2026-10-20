# Viva questions and answers

Short answers you can give in your own words, each with the evidence to point to. Numbers are from the actual runs in
`ml/reports/`.

## The specification's questions (§22)

**Q: Why did you choose this problem?**
Buying land around Hubballi–Dharwad mixes units (gunta, acre, sq ft) and several separate legal facts. Portals filter
and sort, but do not rank by a buyer's purpose or explain why. That is a real, local problem where AI and ML each have
a defined job.

**Q: What real-world problem does it solve?**
It turns "₹25 lakh, long-term investment, near Hubballi or Dharwad" into a ranked, explained shortlist with an
indicative price check. It also tells the buyer what is only claimed and what they must verify themselves.

**Q: What is the role of AI, and what is the role of ML?**
Four kinds of functionality are kept separate:
- **Traditional software:** listings, filters, accounts, roles and review.
- **Algorithmic recommendation:** the weighted ranking and KNN similar listings. Nothing is trained.
- **Supervised ML:** the price regression model, the only trained component.
- **Generative AI:** the Claude assistant, which interprets questions, calls the tools and explains their results.

**Q: Which component is actually trained?**
Only the price model: a scikit-learn pipeline saved with joblib, trained by `backend/scripts/train_price_model.py`.
KNN only stores standardised listing vectors.

**Q: Why was Random Forest chosen?**
It was a candidate, not the final choice. Random Forest, Gradient Boosting and Linear Regression were all tuned and
compared on the validation set. Linear Regression on log price had the lowest validation MAE (₹7.85 lakh, against
₹10.32 lakh for GBR and ₹12.88 lakh for RF), so it was selected. Random Forest would be the natural choice on real
data with non-linear effects; the pipeline keeps it, so retraining on genuine data could pick it.

**Q: How was the dataset collected?**
It was generated, not collected: there is no lawful, consented local dataset, and scraping portals is not allowed.
The generator is reproducible (seed 42) and documented, and every row is labelled synthetic.

**Q: What preprocessing was applied?**
- Unit conversion to sq ft with `Decimal`.
- Exclusion of duplicates and invalid rows (18 of 306, listed in `ml/reports/data_quality.md`).
- Log of price and area.
- Missing flags, for example for road frontage.
- Ordinal road access.
- One-hot encoding of categories with rare levels grouped.
- Scaling.

All of it sits inside one scikit-learn pipeline, fitted on training rows only.

**Q: How was overfitting prevented?**
- A group-aware split, so near-duplicates never sit on both sides.
- Hyperparameters chosen by 5-fold group cross-validation on the training split only.
- Model selection on validation; the test set was used once.
- Comparison against two baselines.
- A locality hold-out check, which exposed weak generalisation to unseen localities. We report it.

**Q: What does the price model predict?**
The current **asking** price of a listing from its attributes, with an 80% indicative range. It does not predict sale
price or a valuation.

**Q: What is the difference between price prediction and price forecasting?**
Prediction estimates a price now from attributes; forecasting estimates how prices move over time, which needs dated
transaction history. PropWise does only prediction. Synthetic data has no real time axis, so forecasting is future
work.

**Q: What happens when the database contains no suitable property?**
The Advisor says so and lists how many listings each strict requirement excluded, so the buyer knows what to relax.
The assistant answers that nothing matched, and invents nothing. Both behaviours are tested.

**Q: How does the LLM communicate with the machine learning models?**
Only through tools. The model calls, for example, `predict_property_price` or `recommend_properties`. The backend
validates the arguments, runs the same service code the REST API uses, and returns the result to the model as
labelled data. The model never sees the database or the model files directly.

**Q: How could the platform scale into a commercial product?**
- Consented listing data from sellers or partners, retraining on real prices.
- Buyer feedback to learn ranking weights.
- A real verification workflow with authorities.
- Object storage and a shared rate-limit store.
- More cities; the localities table already supports them.
- Paid hosting with persistent disks and several instances.

The rest of the specification's questions are answered in the sections below.

## The problem and the data

**Q: What problem does PropWise solve?**
Buyers in Hubballi–Dharwad compare plots, houses and farmland with very different legal statuses and units (sq ft,
gunta, acre). PropWise puts them in one schema, ranks them against a buyer's stated needs with reasons, gives an
indicative price check, and is explicit about what is only claimed by the seller.

**Q: Where does your data come from?**
It is synthetic: `backend/scripts/generate_synthetic_data.py`, seed 42, 306 rows including 6 injected near-duplicates.
Prices follow a documented formula with invented base rates. No portal was scraped, because their terms forbid it and
the data would not be consented. Every record carries `is_synthetic=true`, and the UI says so.

**Q: Then what do your accuracy numbers mean?**
They show that the pipeline (cleaning, unit conversion, leakage-safe splitting, training, evaluation) works and
recovers the generator's rules. They say nothing about the real market. The same pipeline can be retrained on genuine
data with the same schema.

**Q: Why separate land classification, conversion, layout approval and documents?**
They are different facts. A plot can be classified agricultural, have conversion "in progress", sit in an unapproved
layout and still have an RTC. Merging them into one "legal status" would hide exactly what a buyer must check.

**Q: How do you handle units?**
Each listing keeps its original value and unit, and a normalised sq ft value computed with `Decimal` (1 acre = 40
gunta = 43,560 sq ft; 1 gunta = 1,089 sq ft; 1 sq m = 10.7639 sq ft). Money is stored as decimal, never float.

## Price model

**Q: Which models did you try, and which won?**
Two baselines (overall median; locality + type median ₹/sq ft × area), Linear Regression, Random Forest and Gradient
Boosting, all on log(price). Linear Regression had the lowest validation MAE (₹7.85 lakh against ₹10.32 lakh for GBR
and ₹12.88 lakh for RF), so it was selected before the test set was touched.

**Q: Why would Linear Regression beat Random Forest?**
The generator multiplies factors, and taking logs makes that a sum, which is exactly what a linear model fits. Trees
must approximate it in steps from only 200 training rows. On real data the ranking could change.

**Q: What are the test results?**
On 44 test rows: MAE ₹7.59 lakh, MAPE 15.2%, R² 0.963. The baselines had MAPE 91.9% and 46.1%. R² is on rupee values,
so a few large farmland prices dominate it; MAPE is easier to read across ₹5 lakh plots and ₹1 crore farms.

**Q: How did you avoid data leakage?**
Near-duplicate listings share a `dup_group_id`, and the 70/15/15 split is a `GroupShuffleSplit` on it, so copies never
land on both sides. Preprocessing is fitted inside the pipeline on training data only. The test set was used once.

**Q: How does the model do on a locality it has never seen?**
Badly, and we report it. With GroupKFold by locality, MAE was ₹36.82 lakh against ₹21.19 lakh for the baseline. The
model only knows the city and distance to the centre for a new locality, so the API warns in that case.

**Q: What does the price range mean?**
It is the 10th–90th percentile of validation errors, so nominally 80%. On the test set it covered 84.1% of rows. With
44 rows that figure is itself uncertain.

**Q: Is the estimate a valuation?**
No. It is an indicative asking-price estimate from a demonstration model, and every response says so.

## Recommendations

**Q: How does the recommender work?**
It is content-based and rule-driven (`weighted-v1`). Hard filters apply only to requirements the buyer marks strict.
Then five factors are scored 0–1 (budget 30, location 25, purpose 20, road access 15, documents declared 10). The
buyer's importance settings scale the weights, factors without a preference are dropped and the rest rescaled to 100.

**Q: Why not collaborative filtering or a trained ranker?**
There are no real users or interactions to learn from. A transparent rule can be explained, tested and configured;
a learned ranker on fake interactions would only learn our own assumptions.

**Q: How did you evaluate it without labels?**
- An independent checker found 0 strict-requirement violations in 15 scripted scenarios, and a randomised test found
  none either.
- 100% of the available rule-derived "ideal" listings reached the top 5, against 0% for cheapest-first and 13% for
  newest-first.
- Kendall's tau was 0.94 under ±20% random weight changes.
- No Precision@K is reported, because there are no genuine relevance labels.

**Q: What does a score of 85 mean?**
It is a suitability score for the stated preferences, not a probability of investment success. The card shows each
factor's contribution, so the score can be checked by adding them up.

**Q: What is KNN used for?**
For "similar listings" only, on standardised log price, log area, coordinates, road access, documentation and one-hot
city and type. KNN towards a preference vector broke strict requirements in most scenarios, so the Advisor uses the
weighted engine.

## The assistant

**Q: How do you stop the LLM from inventing listings or prices?**
- The model has no data of its own. It can only call nine read-only tools, which use the same services as the API.
- After it answers, every listing id it cites must have been returned by a tool in that turn. If not, the answer is
  replaced by the rule-based one and marked `grounded: false`.
- Prices come only from `predict_property_price`. The prompt forbids estimating, and listing data, ML estimates and
  suitability scores are labelled separately.

**Q: What about prompt injection in a seller's description?**
Tool output is wrapped in `<listing_data>` tags and the system prompt says that content is data, never instructions.
Any copy of those tags inside seller text is removed, so a description cannot break out. A test plants an injection
in a description and checks it stays wrapped.

**Q: What if there is no API key or the API fails?**
The same tools are driven by a rule-based parser, labelled "Basic search mode – AI unavailable". It handles search,
recommendations, prices, comparisons, ranking explanations, documents and glossary terms. The whole demo works this way.

**Q: How do you control cost?**
At most 5 tool rounds per question, low reasoning effort, 12 questions per minute per client, and no key at all for
the demo. Tests use a scripted fake model, so they cost nothing.

## Legal, security and deployment

**Q: Can a document be marked verified?**
No. That needs an authorised verification process, which the project does not have, so the API refuses it (409).
Statuses are "provided – unverified", "not provided", "not applicable" or "unknown", and users are pointed to Bhoomi,
Kaveri, RERA Karnataka and HDMC.

**Q: What security measures are in place?**
- bcrypt password hashes and JWT tokens. The role is re-read from the database on every request, and admins cannot
  self-register.
- Server-side validation on every input, ORM-parameterised queries, and one error format.
- Hidden listings return 404, so their existence is not revealed.
- Image types are checked from the file bytes, with size limits and random file names.
- Rate limits on the assistant and on failed logins, plus security headers.
- Secrets come from the environment, and production refuses to start without a JWT secret.

**Q: How is it deployed?**
A Render Blueprint (`render.yaml`) creates a Postgres database, the FastAPI service and the Next.js service. The API
migrates and seeds on start. The frontend forwards `/api/v1` to the API on the same origin, so there is no CORS setup.
See `DEPLOY.md`.

**Q: What would you do next with more time?**
- Partner with a consenting data source and retrain on real asking or registered prices.
- Collect buyer feedback to tune the weights.
- Add a real document-verification workflow with the authorities.
- Move photos to object storage.
- Extend to more cities; the localities table already supports it.

**Q: What are the main limitations?**
See `limitations.md`. In short: synthetic data, weak generalisation to unseen localities, expert-set weights, and
nothing legally verified.
