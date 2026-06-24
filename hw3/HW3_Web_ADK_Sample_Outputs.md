# HW3 Web ADK Sample Outputs

Screenshots from the **ADK Dev UI** (`adk web`) for each README sample prompt.

Captured from `http://127.0.0.1:8000/dev-ui/` using Doubleword/LiteLLM.

> Educational outputs only. Not financial advice.

---

## 1. mortgage_supervisor — full pipeline

**Web agent:** `mortgage_supervisor`

### ADK Dev UI (Events & tool calls)

![mortgage_supervisor — full pipeline](web_screenshots/01_mortgage_supervisor_full_pipeline_chat.png)

<details>
<summary>Prompt text</summary>

```text
I'm looking at a home in Berryessa, San Jose for $1,280,000.
20% down, 30-year fixed at 6%.
Monthly costs: property tax $1,300, home insurance $150, HOA $25, utilities $300.
Household income $190,000/year, credit score 770, no other monthly debts.
Calculate total monthly payment, LTV, PMI, cash to close, and DTI.
Explain tradeoffs — educational only, no loan recommendation.
```

</details>

---

## 2. mortgage_supervisor — compare down payments

**Web agent:** `mortgage_supervisor`

### ADK Dev UI (Events & tool calls)

![mortgage_supervisor — compare down payments](web_screenshots/02_mortgage_supervisor_compare_down_payments_chat.png)

<details>
<summary>Prompt text</summary>

```text
Compare 20% down vs 10% down on a $1,280,000 Berryessa home at 6% (30-year fixed).
Same costs: tax $1,300, insurance $150, HOA $25, utilities $300.
Income $190,000, credit 770. Show monthly payment, PMI, cash to close, and DTI side by side.
Educational only — no recommendation.
```

</details>

---

## 3. rate_finder

**Web agent:** `rate_finder`

### ADK Dev UI (Events & tool calls)

![rate_finder](web_screenshots/03_rate_finder_chat.png)

<details>
<summary>Prompt text</summary>

```text
For a conventional 30-year fixed loan on a $1,280,000 Berryessa (San Jose) purchase,
explain how today's national 30-year benchmark rate (FRED MORTGAGE30US) compares to
a 6% quoted rate. Also explain 30-year fixed vs 15-year fixed vs 5/1 ARM tradeoffs
for this price range. No recommendation — just facts.
```

</details>

---

## 4. payment_calculator

**Web agent:** `payment_calculator`

### ADK Dev UI (Events & tool calls)

![payment_calculator](web_screenshots/04_payment_calculator_chat.png)

<details>
<summary>Prompt text</summary>

```text
Purchase price: $1,280,000
Down payment: 20% ($256,000)
Interest rate: 6%, 30-year fixed
Property tax: $1,300/mo
Home insurance: $150/mo
HOA: $25/mo
Utilities: $300/mo

Calculate loan amount, LTV, monthly P&I, PMI (if any), total monthly housing cost,
and estimated cash to close (include ~3% closing costs).
```

</details>

---

## 5. affordability_analyzer

**Web agent:** `affordability_analyzer`

### ADK Dev UI (Events & tool calls)

![affordability_analyzer](web_screenshots/05_affordability_analyzer_chat.png)

<details>
<summary>Prompt text</summary>

```text
Gross annual household income: $190,000
Credit score: 770
Other monthly debts: $0
Proposed total monthly housing payment: $7,914
(includes P&I ~$6,139, tax $1,300, insurance $150, HOA $25, utilities $300)

What credit tier does 770 map to? What are front-end and back-end DTI ratios?
How do those compare to typical conventional guidelines? Illustrative only.
```

</details>

---

## 6. compliance_critic

**Web agent:** `compliance_critic`

### ADK Dev UI (Events & tool calls)

![compliance_critic](web_screenshots/06_compliance_critic_chat.png)

<details>
<summary>Prompt text</summary>

```text
Review this draft mortgage summary for math errors and advice-giving language:

"On a $1,280,000 Berryessa home with $256,000 down (20%), the loan is $1,024,000
at 6% for 30 years. Monthly P&I is $6,139. With tax ($1,300), insurance ($150),
HOA ($25), and utilities ($300), total monthly cost is $7,914.
At $190,000 income, front-end DTI is 50%. You should take this loan — you can afford it."

Verify P&I with loan_amount=1024000, rate=6%, term=30, reported_monthly_pi=6139.
Flag any issues and rewrite without advice language.
```

</details>

---

## Regenerate

```bash
# Terminal 1 — start web UI
cd src && uv run adk web ../hw3/adk_agents --port 8000

# Terminal 2 — capture screenshots + markdown
cd src && uv run --with playwright python -m playwright install chromium
cd src && uv run --with playwright python ../hw3/capture_web_adk_screenshots.py
```
