# Published benchmarks for the fiscal and monetary responses

This file records the external numbers this implementation is compared with,
the exact table or figure each comes from, and how the comparison is made
like-for-like. Every number quoted from a table carries its table and page.
Numbers read off a chart are marked "approx." with a stated reading error.
Nothing here is quoted from memory.

The PDFs were retrieved on 6 November 2026. cbo.gov and imf.org refuse
scripted downloads (HTTP 403), so those were fetched from the Internet Archive
copy of the same URL; the URLs below are the original publisher URLs.

## 1. Sources

**[CBO 2015]** Congressional Budget Office, *Estimated Impact of the American
Recovery and Reinvestment Act on Employment and Economic Output in 2014*,
February 2015. <https://www.cbo.gov/publication/49958>, PDF
<https://www.cbo.gov/sites/default/files/114th-congress-2015-2016/reports/49958-ARRA.pdf>.
Table 3, "Estimated Output Multipliers for Major Provisions of the American
Recovery and Reinvestment Act of 2009", pp. 6–7.

| type of activity (Table 3) | low | high |
|---|---|---|
| Purchases of goods and services by the federal government | 0.5 | 2.5 |
| Transfer payments to state and local governments for infrastructure | 0.4 | 2.2 |
| Transfer payments to state and local governments for other purposes | 0.4 | 1.8 |
| Transfer payments to individuals | 0.4 | 2.1 |
| One-time payments to retirees | 0.2 | 1.0 |
| Two-year tax cuts for lower- and middle-income people | 0.3 | 1.5 |
| One-year tax cut for higher-income people | 0.1 | 0.6 |
| Extension of first-time homebuyer credit | 0.2 | 0.8 |

Table 3, note a (p. 7), verbatim: "The output multiplier is the cumulative
impact of spending under the provisions on gross domestic product over
several quarters. The ranges shown in the table reflect the fact that the
Federal Reserve was holding short-term interest rates about as low as
possible and did not tighten monetary policy in response to a fiscal
stimulus."

The February 2012 edition
(<https://www.cbo.gov/sites/default/files/112th-congress-2011-2012/reports/02-22-ARRA.pdf>,
PDF p. 14) has the same purchases (0.5–2.5) and transfers-to-individuals
(0.4–2.1) rows, so there is no vintage drift between 2012 and 2015 on the two
rows compared here. The 2015 edition is cited as current.

**[WR 2015]** Charles J. Whalen and Felix Reichling, *The Fiscal Multiplier
and Economic Policy Analysis in the United States*, CBO Working Paper 2015-02.
<https://www.cbo.gov/publication/49925>, PDF
<https://www.cbo.gov/sites/default/files/114th-congress-2015-2016/workingpaper/49925-FiscalMultiplier_1.pdf>.

* Table 1 (p. 11) reproduces the CBO 2015 Table 3 ranges above, plus
  "Corporate tax provisions primarily affecting cash flow 0–0.4".
* Table 2 (p. 12), "The Effect of a $1 Increase in Aggregate Demand Over
  Eight Quarters" (first published by CBO on 11 October 2012), quarterly
  effect on GDP:

| quarter | well below potential, Fed response limited: low | high | close to potential, Fed responds typically: low | high |
|---|---|---|---|---|
| 1 | 0.50 | 1.45 | 0.50 | 1.43 |
| 2 | 0 | 0.60 | −0.03 | 0.48 |
| 3 | 0 | 0.30 | −0.04 | 0.10 |
| 4 | 0 | 0.15 | −0.05 | −0.10 |
| 5 | 0 | 0 | −0.06 | −0.30 |
| 6 | 0 | 0 | −0.06 | −0.28 |
| 7 | 0 | 0 | −0.05 | −0.25 |
| 8 | 0 | 0 | −0.05 | −0.25 |
| cumulative after 8 quarters | 0.50 | 2.50 | 0.17 | 0.83 |

  p. 11: for purchases these ranges are the whole multiplier (direct effect 1);
  for taxes and transfers they are the "indirect effect", multiplied by a
  provision-specific direct effect. Footnote 36: CBO treats the effects as
  roughly symmetric between expansions and contractions.
* p. 7: Reichling and Whalen (2012) find eight-quarter cumulative US
  multipliers of 0.75–2.25 in macroeconometric forecasting models, 0.3–3.5 in
  time-series models and 0.5–2.25 in DSGE models.
* WR 2015 contains **no** "central" tax-cut multiplier of 0.3. The only 0.3 in
  its tables is the *low* end of the two-year lower- and middle-income tax-cut
  row, in the Fed-not-tightening regime.

**[Coenen 2010]** Günter Coenen, Christopher Erceg, Charles Freedman et al.,
*Effects of Fiscal Stimulus in Structural Models*, IMF Working Paper
WP/10/73, March 2010, <https://www.imf.org/external/pubs/ft/wp/2010/wp1073.pdf>;
published as AEJ: Macroeconomics 4(1), 2012, pp. 22–68,
doi:10.1257/mac.4.1.22. Seven policy-institution models, one of them the
Board's FRB-US. Stimulus = 1% of baseline GDP for one or two years; the
multiplier is "the percentage deviation of real GDP from baseline GDP"
(WP p. 11). Taxes are not raised during the stimulus; "following the
withdrawal of temporary fiscal stimulus … there is a reduction in general
transfers" to restore the debt ratio (WP p. 16, footnote 8). FRB-US has a 40%
hand-to-mouth share (Table 1). The WP does not state which expectations mode
FRB-US was run under, so none is assumed here.

* Text (WP p. 14), government **investment**, one year of stimulus: "For the
  case of no monetary accommodation, the multipliers for the first year are
  similar in all six models, ranging between 0.9 and 1.3." Two years of
  stimulus with two years of accommodation: largest "about 2.2 in GIMF",
  smallest "about 1.1 in FRB-US".
* FRB-US lines read off the charts (approx., ±0.1; annual mean of the
  plotted quarters):

| figure (WP page) | instrument, stimulus length | monetary policy | FRB-US year 1 | FRB-US year 2 |
|---|---|---|---|---|
| Fig. 4 (p. 32) | government consumption, 1 yr | no accommodation | ≈0.95 | — |
| Fig. 25 (p. 53) | government consumption, 2 yr | no accommodation | ≈0.95 | ≈0.8 |
| Fig. 25 (p. 53) | government consumption, 2 yr | 2 yr accommodation | ≈1.05 | ≈1.25 |
| Fig. 7 (p. 35) | general transfers, 1 yr | no accommodation | ≈0.5 | — |
| Fig. 28 (p. 56) | general transfers, 2 yr | no accommodation | ≈0.48 | ≈0.44 |
| Fig. 28 (p. 56) | general transfers, 2 yr | 2 yr accommodation | ≈0.55 | ≈0.65 |

  Across all six US models in Fig. 25 (no accommodation, year 1) the range is
  approx. 0.7 (QUEST) to 1.1 (BoC-GEM). FRB-US has the **largest** general-
  transfers multiplier of the six in Figs. 7 and 28.

**Board documentation.** The Board's own published FRB/US documentation
contains no fiscal-multiplier experiment. The 2014 FEDS Note ("The FRB/US
Model: A Tool for Macroeconomic Policy Analysis", 3 April 2014,
<https://www.federalreserve.gov/econresdata/notes/feds-notes/2014/a-tool-for-macroeconomic-policy-analysis.html>)
has two figures: funds-rate and MFP shocks under VAR vs MCE (Fig. 1) and
stochastic simulations (Fig. 2). It mentions fiscal rules only as a design
feature. The vendored `FRBUS_Simulation_Basics.pdf` (§6) documents the
fiscal switches `dfpex`/`dfpsrp`/`dfpdbt` but reports no multipliers. So
Coenen et al. is the only published source of FRB-US fiscal multipliers found.

## 2. Converting the published numbers to this repo's definition

This repo's multiplier (tests/test_multipliers.py, scripts/scenario_sweep.py)
is a calendar-year ratio for a *sustained* shock: mean ΔGDP over year N /
mean Δinstrument over year N. CBO's Table 2 is the response to a *one-quarter*
$1 impulse. For a sustained shock the quarter-t response is the sum of the
impulse response over the first t quarters, so

    sustained year-1 = mean over t=1..4 of (sum of IRF quarters 1..t)
    sustained year-2 = mean over t=5..8 of (sum of IRF quarters 1..t)

| CBO Table 2 column | year 1 | year 2 |
|---|---|---|
| Fed response limited, low | 0.50 | 0.50 |
| Fed response limited, high | 2.09 | 2.50 |
| Fed responds typically, low | 0.45 | 0.24 |
| Fed responds typically, high | 1.82 | 1.21 |

For transfers to individuals, CBO 2015 Table 3 (0.4–2.1) divided by the
limited-response totals (0.5–2.5) implies a direct effect of 0.80–0.84 per
dollar. Applied to the typical-response path, transfers to individuals with
the Fed responding normally come out at **0.36–1.52** in year 1 and
**0.19–1.02** in year 2. This is a derivation, not a CBO-published number.

## 3. Comparison

Our numbers: `results/benchmark_multipliers.md` (generated by
`scripts/benchmark_multipliers.py`; 8-quarter shocks worth 1% of baseline
real GDP, VAR expectations). "srp" is the demo surplus-ratio fiscal rule the
site's numbers use; "exog" switches it off for the whole window.

| experiment | ours yr 1 | ours yr 2 | matched benchmark | reading |
|---|---|---|---|---|
| purchases, inertial Taylor, srp (site's 0.72) | 0.725 | 0.643 | CBO typical-Fed, derived: 0.45–1.82 / 0.24–1.21 | inside, lower third |
| purchases, inertial Taylor, srp | 0.725 | 0.643 | Coenen Fig. 25, FRB-US, no accommodation: approx. 0.95 / 0.8 | **below** the paper's own FRB-US line by ~0.2 |
| purchases, peg, srp (site's 0.90) | 0.769 | 0.904 | CBO limited-Fed, derived: 0.50–2.09 / 0.50–2.50 | inside, near the low end |
| purchases, peg, srp | 0.769 | 0.904 | Coenen Fig. 25, FRB-US, 2 yr accommodation: approx. 1.05 / 1.25 | **below** by ~0.3 |
| transfers, inertial Taylor, srp | 0.278 | 0.303 | CBO transfers to individuals, typical-Fed, derived: 0.36–1.52 / 0.19–1.02 | **below** in year 1 |
| transfers, peg, exog | 0.315 | 0.512 | CBO 2015 Table 3, transfers to individuals (Fed not tightening): 0.4–2.1 | **below** |
| transfers, inertial Taylor, exog | 0.299 | 0.395 | Coenen Fig. 28, FRB-US general transfers, no accommodation: approx. 0.48 / 0.44 | **below** by ~0.15–0.2 |
| personal tax rate, inertial Taylor | 0.224 | 0.319 | CBO 2015 Table 3: two-year cut, lower/middle income 0.3–1.5; one-year cut, higher income 0.1–0.6 (Fed not tightening) | between the rows; no published "central 0.3" |
| personal tax rate, peg | 0.235 | 0.403 | same | same |

### Why the gaps

1. **Monetary accommodation (the regime).** CBO 2015 Table 3 is explicitly a
   Fed-not-tightening regime (note a). Round 1 compared the active-rule
   transfers multiplier (0.28) with 0.4–2.1 and called it "below CBO's
   range"; that comparison mixed regimes and is withdrawn. Matched comparisons
   are the peg rows against Table 3, and the Taylor rows against the
   typical-Fed path of Whalen & Reichling Table 2. Transfers are still below
   on both matched comparisons, so the finding survives but is smaller than
   round 1 implied. Pegging raises every multiplier (gated in
   `tests/test_benchmarks.py`).
2. **The fiscal closure is not the explanation.** The demo rule raises the
   personal tax rate during the stimulus (purchases: +0.25pp in year 1,
   +0.68pp in year 2; with the rule off, +0.09 / +0.17). Switching it off
   moves the year-1 multipliers by only +0.02 (purchases 0.725 → 0.748,
   transfers 0.278 → 0.299); year 2 moves more (0.643 → 0.735; 0.303 → 0.395).
   Coenen et al. hold taxes fixed during the stimulus, so the matched rows are
   "exog". Year 1: purchases 0.748 vs approx. 0.95 and transfers 0.299 vs
   approx. 0.48, gaps of ~0.2 that are larger than the ±0.1 chart-reading
   error. Year 2: purchases 0.735 vs approx. 0.8 and transfers 0.395 vs
   approx. 0.44, gaps of ~0.05–0.07 that sit inside the reading error. **The
   year-1 shortfall is the finding; the year-2 one mostly dissolves once the
   closure is matched.**
3. **Expectations mode and model vintage.** This repo implements VAR
   expectations only (`Frbus(mce=...)` raises `NotImplementedError`; see
   `docs/mce-feasibility.md`). The Coenen et al. runs used the 2009-10
   FRB-US, whose expectations mode the WP does not state, with a 40%
   hand-to-mouth share (their Table 1); the 2026 model's consumption block and
   coefficients are different. Either can account for a ~0.2 gap; neither can
   be tested here until MCE exists. The FRB-US lines are chart readings
   (±0.1), so a gap below ~0.1 would not be meaningful.
4. **Horizon definition.** CBO's multipliers are cumulative over "several
   quarters" per dollar of a one-time outlay; ours are calendar-year ratios
   for a sustained shock. Section 2 converts CBO's quarterly path to ours. A
   one-year-mean ratio and an eight-quarter cumulative sum differ by a factor
   that depends on the shape of the response, so never compare 0.72 with
   0.5–2.5 directly.
5. **Size and sign** (issue #11): at 1% of GDP the purchases multiplier is
   0.725 for a rise and 0.900 for a cut (log aggregation). CBO assumes
   symmetry (WR 2015 footnote 36). The small-shock value is ~0.80.

### What is gated (tests/test_benchmarks.py, CI correctness-gates)

* Purchases, inertial Taylor, both closures: year 1 in [0.45, 1.82], year 2
  in [0.24, 1.21] (CBO typical-Fed path, converted). Peg: [0.50, 2.09] and
  [0.50, 2.50] (CBO limited-Fed path, converted).
* Transfers: 0.15 < transfers < purchases and < 0.7 in every cell. Not gated
  to CBO, because the model is outside the derived CBO range; that is a
  finding, not a regression.
* Closure switches: the srp and exog tax rows coincide (trp exogenized);
  the surplus rule raises trp at least twice as much as with the rule off;
  pegging raises every multiplier.
* Chart readings from Coenen et al. are never gated.

## 4. The 2022–23 tightening

`scripts/episode_2022_tightening.py` → `results/episode_2022_tightening.md`.
LONGBASE carries realised history to 2025Q4. The history run puts the funds
rate on its realised path (`dmpex=1`, `rfffix` = realised `rff`, set before
`init_trac`) with fiscal tax trends exogenous; it reproduces realised rff,
real GDP, unemployment and core PCE to < 1e-6 (asserted). Counterfactual A
holds the funds rate at the model's 0.125% floor through 2025Q4;
counterfactual B holds it there through 2023Q4 and then lets the inertial
Taylor rule set it in both runs.

| effect of the tightening (history − counterfactual) | 2023Q4 | 2024Q4, A | 2024Q4, B |
|---|---|---|---|
| real GDP, % | −3.28 | −6.66 | −5.18 |
| unemployment rate, pp | +1.71 | +3.63 | +2.74 |
| core PCE inflation, 4-quarter, pp | −0.14 | −0.35 | −0.31 |
| core PCE price level, % | −0.15 | −0.49 | −0.45 |
| 10-year Treasury yield, pp | +2.12 | +2.40 | +0.94 |

Mean four-quarter core PCE effect over 2022–2024: −0.12pp (A), −0.11pp (B).

**Published estimates of this episode:**

* Najjar and Shapiro, "Does Monetary Policy Tightening Reduce Inflation?",
  FRBSF Economic Letter 2025-03, 3 Feb 2025,
  <https://www.frbsf.org/research-and-insights/publications/economic-letter/2025/02/does-monetary-policy-tightening-reduce-inflation/>:
  "core PCE inflation would have been approximately 3 percentage points
  higher on average between 2022 and 2024 if the FOMC had not raised
  interest rates in 2022 and 2023". No output or unemployment counterfactual.
* D'Amico and King, "Past and Future Effects of the Recent Monetary Policy
  Tightening", Chicago Fed Letter 483, Sept 2023,
  <https://www.chicagofed.org/publications/chicago-fed-letter/2023/483>:
  counterfactual policy rate at the lower bound 2021Q4–2023Q3, survey-
  augmented VAR. By 2023Q3, real GDP level −5.4pp and CPI level −7.1pp
  (median), about 65% and 75% of the eventual effects. No unemployment
  estimate.
* No Federal Reserve publication with an FRB/US counterfactual for this
  episode was found (searched FEDS Notes and regional Fed letters, 6 Nov
  2026).

**Reading.** The model's real effects are in the range of the Chicago Fed
VAR (GDP −3.3% at 2023Q4 vs −5.4% at 2023Q3), but its inflation effect is an
order of magnitude smaller than either published estimate: −0.12pp on
average over 2022–24 against ~3pp (FRBSF), and a core-PCE level effect of
−0.15% at 2023Q4 against −7.1% for the CPI level (Chicago Fed; different
index). Neither published estimate is an FRB/US run: FRBSF uses
high-frequency-identified policy shocks (a 25bp surprise lowers core PCE by
~0.5pp within 12 months), and Chicago uses a survey-augmented VAR. The
Board's pyfrbus gives the identical counterfactual (5e-8 abs, gated), and
the 100bp ping matches the Board's published post-2018 simulation (Laforte
2018, core PCE trough −0.0345pp). Almost all of the inflation response runs
through the VAR-expectations equations `zpicxfe`/`zpieci`, not the NKPC
slopes. See `docs/inflation-transmission.md`. The model attributes almost all
of the 2022–23 disinflation to residuals (supply-side unwinding), not to
policy.

**Domain warning.** Counterfactual A drives unemployment to 0.52% by 2024Q4
and −0.61% by 2025Q4, which is impossible: the model has no floor on
unemployment, and its linearised labour block is far outside its estimation
range. Only the 2022–23 columns (counterfactual unemployment 3.3% and 2.1%)
and counterfactual B should be read; even 2.1% is below any post-war US
outturn. The real-side numbers should therefore be read as an upper bound.

Other caveats: all non-policy shocks of 2022–25 are held at their tracked
values; the counterfactual long rate moves only through the VAR's response
to the funds rate, so the anticipation of hikes in early 2022 is not removed;
balance-sheet runoff is not modelled.

## 5. Expectations mode

The repo, and every number the macro site quotes from it, uses VAR
expectations only. MCE is not implemented (`src/frbus/frbus.py` raises
`NotImplementedError`; `docs/mce-feasibility.md` sets out the build). So a
100bp shock cannot be compared across modes here. The macro site says so: the
FRB/US landing, methodology and validation pages all state "VAR expectations"
and that MCE and forward guidance are out of scope (PolicyEngine/macro
`frb-us/index.html`, `frb-us/methodology/index.html` line 295,
`frb-us/validation/index.html` lines 268–269, at commit 153cf41).
