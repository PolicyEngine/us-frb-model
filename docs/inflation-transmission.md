# Inflation transmission in this FRB/US implementation

Question (issue #14): the 2022–23 tightening counterfactual gives real GDP
−3.3% and unemployment +1.71pp at 2023Q4, but core PCE only −0.14pp (mean
−0.12pp over 2022–24). The 100bp benchmark ping gives a core PCE trough of
−0.034pp against "as much as 0.08" in the 2014 FEDS Note. Is the weak
inflation response (a) faithful to FRB/US, or (b) an implementation gap?

**Answer: (a).** The like-for-like comparator is the Board's own published
ping of the post-2018 model, and this repo reproduces it. Nothing in the
price–wage block is switched off or exogenized relative to pyfrbus. The
2013–14 "−0.08" refers to an earlier model vintage. The FRBSF and Chicago Fed
estimates of the episode come from a different class of model.

Numbers: `scripts/inflation_transmission.py` → `results/inflation_transmission.{json,md}`,
gated by `tests/test_inflation_transmission.py`.

## 1. The Board's own simulation of the current model

Laforte (2018), "Overview of the changes to the FRB/US model (2018)", FEDS
Notes, 7 Dec 2018, doi:10.17016/2380-7172.2306, Figure 2, "Responses to a
100 bps increase in the Fed funds rate (VAR-based expectations)". The values
below are from the note's accessible data table, checked against the raw HTML
on 6 Nov 2026. The shock is in 2020Q1.

| 100bp ping, VAR expectations | this repo (2026Q1 shock) | Board, new (post-2018) model | Board, previous model |
|---|---|---|---|
| core PCE inflation (annualised q/q `picxfe`; the Board's table gives no concept, and the quarter-8 timing matches q/q, not 4q, whose trough here is quarter 10), trough | **−0.034pp, quarter 8** | **−0.0345pp, quarter 8 (2021Q4)** | −0.0617pp, quarter 6 |
| output gap, trough | −0.50pp, quarter 7 | −0.486pp, quarter 8 | −0.459pp, quarter 9 |
| unemployment, peak | +0.26pp, quarter 8 | +0.219pp, quarter 8 | +0.215pp, quarter 9 |
| funds rate, impact / undershoot | +1.00 / −0.26pp | +1.00 / −0.27pp | +0.95 / −0.30pp |

The note's explanation of the smaller inflation response, verbatim: "the
smaller short-term responses of the inflation variables reflect not so much
the changes to the model as they do the re-estimation of the wage-price block
equations over a longer sample period that now extends through 2017. An
update of the estimation of the old version of the FRB/US would have resulted
in smaller responses of the inflation process as well."

The 2014 FEDS Note (−0.08pp) and the 2013 price–wage note (Fig. 3, about
−0.08pp) both describe the pre-2018 vintage. They should not be read as the
benchmark for this model. The Board's own "previous version" column (−0.062)
already sits between them and the current −0.0345.

Settings check. The Board's `programs/pings.prg` turns off the ZLB and the
thresholds (`rffmin=-9999`, `dmptrsh=0`) and fixes `rstar` (`drstar=0`) for
40 quarters. LONGBASE already has `drstar=0` and `dmptrsh=0`, and the floor
never binds for a +100bp shock from a 3.8% baseline. Rerunning the ping from
2040Q1 with the pings.prg settings gives the same trough (−0.034pp), so the
result depends on neither the baseline nor the settings.

## 2. Where the response comes from: channel shut-offs

Each row reruns the experiment with one channel removed.

| channel removed | ping: core PCE trough | episode: core PCE 4q, 2023Q4 | share of the response |
|---|---|---|---|
| none (model as published) | −0.034 | −0.143 | — |
| VAR expectations `zpicxfe`, `zpieci` held at baseline | −0.000 | −0.002 | **~99%** |
| long-run expectations `ptr` held at baseline | −0.032 | −0.141 | ~5% / ~1% |
| real exchange rate `fpxr` held at baseline | −0.027 | −0.095 | ~20% / ~34% |

* **Expectations carry almost the whole response.** `picxfe` puts weight
  0.98 (`y_picxfe(3)`) on `zpicxfe`, and `pieci` puts the same weight on
  `zpieci`. In VAR mode these are reduced-form forecasts that load directly
  on lagged `rff`, `xgap2` and the unemployment gap. The NKPC's own slack
  terms are small: the wage unemployment slope is `y_pieci(2) = −0.0167`,
  and the price markup term is `y_picxfe(2) = 0.0019` (×400).
* **Anchoring is strong and is in the published equation.**
  `ptr = 0.9·ptr(−1) + 0.05·picxfe(−1) + 0.05·pitarg(−1)`. Over the episode,
  `ptr` moves −0.017pp.
* **The exchange-rate channel is live.** In the episode the real exchange
  rate appreciates 11% by 2023Q4 (`fpxr`, from the real long-rate gap,
  `y_fpxr(1) = 0.048`). Import prices ex-oil (`pmo`) fall 5.1%. That reaches
  core PCE only through the desired-price aggregates (`qpxp` → `qpcnia` →
  `picxfe` markup term) and through `pipxnc`. `picxfe` has no direct
  import-price term in the published model.
* **Commodity prices** (`poilr`) are behavioural with an exogenous trend
  (`poilrt`) and have no policy-rate term in the published model. Energy and
  food reach headline PCE only (`picnia`), not core.

## 3. Coefficient vintage: the structural slopes are not the gap

The five NKPC parameters were set to the 2013 note's estimates (Table 1,
p. 8; the mapping is in the script docstring). The current `model.xml`
satisfies the note's restriction κw = 0.5·κp (0.000957/0.001915 = 0.50),
which supports reading the units as identical.

| NKPC parameters | ping: core PCE trough | episode: core PCE 4q, 2023Q4 |
|---|---|---|
| current model.xml | −0.034 | −0.143 |
| wage slope only → −0.024 (2013 Bayesian) | −0.034 | −0.143 |
| 2013 Bayesian 1985–2012, all five | −0.033 | −0.141 |
| 2013 ML 1985–2007, all five | −0.034 | −0.141 |

Changing the structural slopes moves nothing. Under VAR expectations, the
inflation response is set by the auxiliary forecasting system (`zpicxfe`,
`zpieci`), which the Board re-estimated together with the NKPCs in 2018. The
2013 auxiliary coefficients are not published, so the earlier vintage cannot
be rebuilt here. The coefficient rows are a test of the slope hypothesis,
which they reject. They are not a reconstruction of the 2013 model.

## 4. The episode against published estimates

* Najjar and Shapiro (FRBSF EL 2025-03): ~3pp on average over 2022–24. The
  method is high-frequency-identified monetary-policy shocks (Bauer–Swanson,
  Jarociński–Karadi) applied to the supply/demand decomposition of core PCE.
  In their Fig. 3, a 25bp surprise lowers core PCE by about 0.5pp within 12
  months. That is roughly 60 times FRB/US's response per 100bp. It is
  an empirical estimate from a different class of model, not an FRB/US
  result.
* D'Amico and King (Chicago Fed Letter 483) use a survey-augmented VAR.
  It is also not FRB/US.
* No FRB/US counterfactual for the episode has been published (searched
  6 Nov 2026).

So the episode gap is a gap between FRB/US (VAR) and the empirical
literature, not an error in this code. The model's sacrifice ratio is the
same in both experiments: about 0.08–0.13pp of core inflation per pp of
unemployment.

The Board's pyfrbus gives the same counterfactual path (section 6).

## 5. Transfers to consumption (issue #13)

The chain is `gtr_aerr → gtr → gtn = .01·pgdp·gtr → yhtn = uyhtn·gtn` (with
`uyhtn` = 0.9997) `→ yht = yhtn/(.01·pcnia) → eco`. Transfers are not taxed:
`tryh` applies to labour and property income. Measured with the funds rate
pegged and the tax trends exogenous:

| 1% of GDP for 8 quarters | Δyht/Δgtr | consumption per unit income, q1 | hand-to-mouth prediction, q1 | yr 1 | GDP per unit income, yr 1 |
|---|---|---|---|---|---|
| transfers | 1.020 | 0.305 | 0.291 | 0.359 | 0.309 |
| after-tax labour income (`yhl_aerr`) | — | 0.288 | 0.291 | 0.351 | 0.301 |

* The transmission is clean. Households receive 1.02 of each real unit
  (the pgdp/pcnia deflator ratio).
* The MPC out of transfers equals the MPC out of after-tax labour income.
  `eco` has a single hand-to-mouth term,
  `y_eco(4) = 0.3075` on Δlog(yhl + yht). It does not tell transfer
  recipients from earners. The forward-looking `qec` channel barely moves
  for a temporary shock: `zyht` loads only ~0.002 on `yhtgap`. The impact
  MPC is therefore y_eco(4)·y_ecnia(1)·ecnia/(yhl+yht) ≈ 0.29.
* The transfers multiplier scales with that one coefficient. Setting
  `y_eco(4)` to 0.40, the share in the 2009–10 model used by Coenen et al.,
  raises the year-1 multiplier from 0.278 to 0.360 (Taylor, surplus rule)
  and from 0.315 to 0.409 (peg, rule off). CBO's range for transfers assumes
  that recipients have higher MPCs than average. FRB/US has no channel for
  that, so a multiplier below CBO's derived range is a property of the
  model, not of this code.

## 6. Cross-check of the episode against the Board's pyfrbus

`scripts/generate_vendor_episode_reference.sh` runs the Board's pyfrbus (the
same patched copy as the 100bp cross-validation) on the identical history and
counterfactual runs, and writes `tests/data/vendor_episode_2022_{hist,cf}.csv`.
Across all 284 endogenous variables and 16 quarters this implementation agrees
with it to 8.5e-9 abs on the history run and 5.0e-8 abs (2.3e-7 rel) on the
counterfactual. Both runs give the same effects at 2023Q4: core PCE 4q
−0.1429pp, mean 2022–24 −0.1180pp, GDP −3.2764%, unemployment +1.7103pp.
The weak inflation effect is therefore what the Board's own code produces.
Gate: `tests/test_inflation_transmission.py::test_episode_matches_vendor_pyfrbus`
(1e-6 abs and rel, the Test 2 tolerances).
