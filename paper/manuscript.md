# Rest-Voltage State-of-Charge Estimation on Unseen Lithium-Ion Cells: Two Preregistered Tests Show Per-Cell Low-Temperature Registration Beats Cross-Cell Learning Transfer

*Draft v0 (2026-11-18). Target: IEEE Access. Citations marked [R:key] are resolved from `paper/refs.md`.*

## Abstract

Battery stations for drones and other small electric aircraft need the state of charge (SOC) of a returning pack within minutes of landing, when current-integration estimates from low-cost sensors have drifted. The rest voltage measured right after landing is an attractive observation, but it is short, taken at varying temperature, and read through an inexpensive measurement chain. We study SOC estimation from a 300 s rest-voltage trace and ambient temperature, with simulated low-cost measurement errors, assuming one room-temperature registration test per cell. On five public development datasets (six cells), a residual gradient-boosting correction learned on other cells reduced leave-one-dataset-out mean absolute error (MAE) from 3.40 to 2.11 percentage points (pp) relative to plain registration lookup. In a preregistered single-run test on 13 unseen cells (LG E66, Molicel P42A; 1,365 rests), the gain vanished (1.43 vs 1.41 pp; paired 95 % CI of the difference included zero). Diagnosis showed that the development gain came almost entirely from correcting the low-temperature rest-voltage depression, whose size is cell-specific (bias at −20 °C: −6.6 pp on development cells vs −3.3 pp on E66). We then fixed, on development data only, a training-free two-point lookup that interpolates 25 °C and low-temperature registration tables in temperature. In a second preregistered test on six cells of a different laboratory (Plett ESC data, −25 to 45 °C), it reduced MAE relative to 25 °C lookup by 2.74 pp (5.23 vs 7.97 pp; 95 % CI [1.08, 4.36]) and was statistically indistinguishable from the learned correction (5.23 vs 5.80 pp; CI of the difference [−0.35, 1.60]). It was the most accurate method between −15 and 15 °C, while every method exceeded 13 pp MAE at −25 °C, 20 °C below the coldest registration point. Inference takes 0.5–5 ms per estimate. For rest-voltage SOC estimation, per-cell registration design matters more than the choice of a learned model, and cross-validation over similar training cells can overstate cross-cell transfer.

**Index Terms:** state of charge, open-circuit voltage, rest voltage, temperature dependence, lithium-ion battery, generalization, preregistration, battery station, unmanned aerial vehicle.

## I. Introduction

Battery stations that recharge or swap packs for drones and small electric aircraft must decide, shortly after each landing, how much charge a returning pack holds: this sets charging priority, determines whether the pack can fly the next mission, and flags packs whose capacity has faded [R:uav-station]. Coulomb counting during flight is the usual source of this estimate, but with low-cost Hall-effect current sensors its error grows with sensor offset, gain error, and uncertainty in the actual capacity [R:cc-error, R:lowcost-sensor]. The rest period right after landing offers an independent observation: the terminal voltage relaxes toward the open-circuit voltage (OCV), which maps monotonically to SOC for most chemistries [R:ocv-soc, R:plett-book1].

Using this observation in practice is harder than reading an OCV table. The rest available before the station must act is a few minutes, far shorter than the hours needed for full relaxation [R:relaxation]; the ambient temperature varies from mission to mission, and both the OCV and the relaxation dynamics depend on temperature [R:ocv-temp]; and the voltage is read through an inexpensive analog front end. A natural remedy is to learn a correction from data: given the rest-voltage shape and temperature, predict the gap between the room-temperature OCV lookup and the true SOC [R:data-driven-soc]. Data-driven SOC estimators routinely report errors near or below 1–2 % on held-out data [R:soc-review], but held-out data are often drawn from the same cells or laboratories as the training data, and cross-cell or cross-temperature transfer is less well established [R:transfer, R:leakage].

This paper asks three questions. (Q1) How accurately can SOC be estimated from a short rest-voltage trace on cells never seen in development? (Q2) Does a correction learned on other cells improve on a per-cell registration lookup? (Q3) Which conditions remain hard? We answer them with a development phase on five public datasets followed by two preregistered tests on unseen cells, each run once with the model and analysis plan committed beforehand.

Our contributions are:
1. **A cross-cell evaluation protocol for rest-voltage SOC estimation** under simulated low-cost measurement errors, with per-cell registration, leave-one-dataset-out and temperature-extrapolation cross-validation, and two preregistered single-run tests on 19 unseen cells from three laboratories.
2. **A negative transfer result with a mechanism.** A learned residual correction that gained 1.3 pp in development gained nothing on unseen cells. The gain was almost entirely the correction of the low-temperature rest-voltage depression, whose magnitude differs between cells but happened to be similar among the development cells, so cross-validation could not reveal the variation.
3. **Evidence for per-cell low-temperature registration.** A training-free two-point lookup, a minimal instance of the temperature-dependent OCV models standard in battery management [R:plett-esc], was fixed before testing. It beat room-temperature lookup in a preregistered test and matched or exceeded the learned correction, with its advantage concentrated between −15 and 15 °C.
4. **Practical guidance and open artifacts:** which registration tests to run per cell, the remaining failure mode (temperatures far below the coldest registration point), timing for server deployment, and code with commit-hash-stamped protocols.

We do not claim a new estimator: the two-point lookup is deliberately simple and closely related to existing temperature-dependent OCV tables. The contribution is the controlled evidence about what transfers to unseen cells and what does not.

## II. Related Work

**OCV–SOC relationship and its temperature dependence.** The OCV–SOC curve underlies most SOC estimators, from table lookup to model-based observers [R:ocv-soc, R:plett-book1]. Its temperature dependence is commonly modeled as OCV(z, T) = OCV0(z) + T·OCVrel(z), identified from slow-rate tests at several temperatures, as in Plett's enhanced self-correcting (ESC) model [R:plett-esc, R:plett-book2]; hysteresis adds a path-dependent term, important for LFP [R:hysteresis]. Our two-point lookup is a minimal, data-poor version of this idea, using two registration tests per cell and interpolation in the SOC domain.

**Rest and relaxation-based OCV estimation.** Because full relaxation can take hours, several works fit equivalent-circuit relaxation models to the first minutes of a rest and extrapolate the asymptotic voltage, or learn the mapping from a short rest to OCV [R:relaxation, R:rest-short]. We include a two-RC extrapolation baseline (B3) and find that, under low-cost measurement noise, it does not improve on lookup at the end of a 300 s rest.

**Data-driven SOC estimation and generalization.** Gradient-boosted trees and neural networks are widely used for SOC estimation from voltage, current, and temperature histories [R:data-driven-soc, R:soc-review]. Transfer learning and domain adaptation have been proposed to carry models across cells, temperatures, and chemistries [R:transfer]. Several authors have warned that random or within-cell splits overestimate performance, and that evaluation must hold out cells or conditions [R:leakage]. Our results add a specific failure case: even leave-one-dataset-out cross-validation overstated transfer because the held-out development cells were too similar in the property that mattered.

**Low-cost sensing.** Robustness of SOC estimation to sensor offset, bias, noise, and quantization has mostly been studied with assumed error injections [R:lowcost-sensor]. We inject the gain, offset, noise, and quantization of a specific low-cost chain (divider plus 12-bit ADC) into every test voltage.

**Preregistration and negative results.** Preregistration, committing hypotheses and analysis plans before seeing test data, is established in clinical and behavioral research and increasingly advocated in machine learning to prevent overfitting to benchmarks [R:prereg]. We are not aware of preregistered evaluations in battery-state estimation.

## III. Problem Setup and Data

### A. Task

A sample is one rest that follows a discharge. The input is the first r seconds of the rest voltage sampled at 1 Hz (r = 300 s primary; 60 and 600 s secondary) and the ambient temperature; the output is SOC. For each test cell, a *registration* test performed once at 25 °C (and, for the two-point method, once at a low temperature) supplies rests with known SOC. Registration samples are never scored.

### B. Sample definition and reference SOC

A rest is a period of at least 300 s with |I| < I_rest = C_nom/150, preceded by a discharge (mean current over the last 60 s below −I_rest) and by at least 300 s of recording. Reference SOC is 1 + Q(t)/Q25, where Q(t) is the charge (negative for discharge) integrated from the most recent full-charge anchor and Q25 is the cell's maximum discharged capacity at 25 °C. Samples with SOC outside (−0.02, 1.02) are dropped. Signals are resampled to 1 Hz.

### C. Measurement-error model and temperature input

Every test voltage passes through a simulated low-cost chain: per-sample gain error N(0, 0.2 %), offset N(0, 5 mV), white noise N(0, 2 mV), and quantization with a 6.2 mV step (12-bit ADC behind a 100 kΩ/15 kΩ divider at 3.3 V), with three error seeds. The ambient temperature input is the chamber's nominal temperature plus N(0, 2 °C) noise.

### D. Datasets

Table I summarizes the data. Development uses five public datasets with one cell each (two for CALCE INR20R) [R:data-lg, R:data-pan, R:data-calce, R:data-mcm]. Test 1 uses LG E66 (one 65 Ah pouch cell) [R:data-e66] and Molicel P42A (12 cylindrical cells) [R:data-p42a]. Test 2 uses the Plett ESC toolbox data (six cells of different chemistries and sizes) [R:data-plett]. None of the test cells were used during development. A third candidate, Univ. Malaya NCR18650B/VTC6, was converted but excluded before any model was run because only 10 of its rests were colder than the available low-temperature registration (Section V-D).

**TABLE I. Datasets (r = 300 s sample counts).**

| Role | Dataset | Cells | Temperatures (°C) | Scored | Registration |
|---|---|---|---|---|---|
| Dev | LG HG2 (NMC) | 1 | −20 … 40 | 244 + 123 ext. | 55 |
| Dev | Panasonic 18650PF (NCA) | 1 | −20 … 25 | 148 + 38 ext. | 65 |
| Dev | CALCE INR20R (NMC) | 2 | 0 … 45 | 19 | 10 |
| Dev | Samsung 30T (NMC) | 1 | −20 … 40 | 126 + 74 ext. | 36 |
| Dev | Turnigy Graphene (LiPo) | 1 | −20 … 40 | 139 + 64 ext. | 45 |
| Test 1 | LG E66 (NMC pouch, 65 Ah) | 1 | −20, −10, 0, 10, 40 | 794 | 14 |
| Test 1 | Molicel P42A (NMC/Si-Gr) | 12 | 5, 40 | 571 | 288 |
| Test 2 | Plett ESC (A123, ATL, E1, E2, P14, SAM) | 6 | −25 … 45 (8 levels) | 658 | 104 + 120 |

*"ext." = temperature-extrapolation fold samples. TODO: confirm temperature ranges per dev dataset from data.*

## IV. Methods

All methods share the interface: given registration rests of the test cell and a test rest, return SOC.

- **B0, global OCV table:** isotonic regression of SOC on end voltage pooled over training cells; no registration.
- **B1, registration lookup:** isotonic regression of SOC on end voltage (mean of the last 15 s) over the test cell's 25 °C registration rests.
- **B2, B1 + linear temperature correction:** SOC = B1 + β·[1, ΔT, ΔT², ΔT·B1], ΔT = T − 25 °C, with four coefficients fitted by least squares on training cells.
- **B3, two-RC extrapolation:** the asymptotic voltage of a two-RC relaxation fit replaces the end voltage in B1.
- **B4, plain gradient boosting:** XGBoost on the same features as S, predicting SOC directly, without registration residual, augmentation, or weighting.
- **S, learned residual correction (proposed in development):** XGBoost (300 trees, depth 3, learning rate 0.05, subsample 0.8, absolute-error loss, monotone in end voltage and relaxation increments) predicts SOC − B1 from the end voltage, five relaxation increments (end minus 5-point means at 4, 9, 29, 59 s and r/2), a late-relaxation ratio, the B1 SOC, and ambient temperature. Training uses overpotential-amplitude augmentation (the relaxation transient is rescaled about a two-RC asymptote by a log-uniform factor in [0.1, 4], six copies), dataset × SOC-bin balance weights, and a bag of five models. S is the simplified variant selected after the ablation in Section V-A (removing per-time-point lookup, k-NN registration features, OCV-shape randomization, and measurement-chain augmentation); the full variant P is reported as secondary.
- **T2, two-point registration lookup:** with SOC_25 and SOC_low from the test cell's 25 °C and low-temperature (T_low) registration tables, SOC = clip(SOC_25 + w·(SOC_low − SOC_25), 0, 1), w = max(0, (T − 25)/(T_low − 25)). There is no training. Of four variants evaluated on development data only (linear in T, linear in 1/T, w clipped to [0, 1], and no extrapolation above 25 °C), the last was chosen because extrapolating the 0–25 °C trend to 40 °C degraded accuracy (Section V-C).

## V. Experiments and Results

### A. Development

Development uses leave-one-dataset-out (LODO) folds over the five datasets, scoring only non-25 °C samples, plus temperature-extrapolation folds (train on −10 to 25 °C, test at −20 and 40 °C). The development metric is the mean of the LODO and extrapolation MAEs at r = 300 s; CIs are bootstrap over samples within datasets (B = 2000).

**TABLE II. Development results (MAE, pp, r = 300 s).**

| Method | Dev metric [95 % CI] | LODO | Temp.-extrap. |
|---|---|---|---|
| B0 global table | 10.76 | 10.66 | 10.87 |
| B1 registration lookup | 3.40 | 3.06 | 3.75 |
| B2 B1 + linear temp. corr. | 2.26 | 1.96 | 2.56 |
| B3 2RC extrapolation | 3.30 | 2.87 | 3.73 |
| B4 plain XGBoost | 3.82 | 3.25 | 4.39 |
| P full learned correction | 2.11 [1.90, 2.32] | 1.87 | 2.35 |
| S simplified (selected) | 2.08 [1.89, 2.27] | 1.91 | 2.24 |

Ablation of P (increase in the development metric when a component is removed): residual learning on top of B1 +1.42, balance weights +0.28, temperature input +0.20, amplitude augmentation +0.13; per-time-point lookup, k-NN features, shape randomization, and chain augmentation contributed nothing or slightly hurt, which motivated S. Because S was chosen after this ablation, its development score is optimistically biased; the preregistered tests are the unbiased evaluation.

### B. Test 1 (preregistered): learned correction vs registration lookup

The protocol (commit 14c47ae), conversion code (d77e5e5), and runner (82f5722) were committed before the single run. Scoring used non-25 °C samples; registration was the 25 °C GITT test (E66) or the 25 °C HCGT test of each cell (P42A). CIs are bootstrap over cells for P42A (12 cells) and over samples for E66 (one cell). Hypotheses: H1, S < B1; H2, S < B2.

**TABLE III. Test 1 (MAE, pp, r = 300 s).**

| Method | LG E66 [95 % CI] | Molicel P42A [95 % CI] | Mean |
|---|---|---|---|
| S | 1.775 [1.68, 1.86] | 1.092 [1.03, 1.16] | 1.434 |
| B1 | 1.738 [1.63, 1.85] | 1.082 [1.00, 1.18] | 1.410 |
| B2 | 1.793 [1.69, 1.89] | 1.143 [1.08, 1.21] | 1.468 |
| P | 1.719 [1.63, 1.81] | 1.161 [1.11, 1.22] | 1.440 |

Paired differences B1 − S: −0.037 [−0.15, 0.08] (E66) and −0.010 [−0.14, 0.11] (P42A); B2 − S: +0.017 [−0.06, 0.10] and +0.051 [−0.02, 0.11]. **Neither H1 nor H2 was supported.** S overestimated SOC on E66 at every temperature (bias +1.0 to +3.2 pp). Shorter rests favored B1 (r = 60 s: 1.63 vs 2.29 pp), and longer rests favored B2 (r = 600 s: 0.96 pp).

### C. Diagnosis: the low-temperature depression is cell-specific

Fig. 2 plots the bias of B1 against temperature. On development cells, B1 underestimated SOC increasingly with cold: −6.57 pp at −20 °C, −3.58 at −10 °C, −1.99 at 0 °C, and −0.05 at 40 °C (pooled LODO samples), with the three development cells measured at −20 °C clustered between −6.1 and −6.9 pp. Replacing the 25 °C table with a same-temperature table (an oracle) reduced B1 from 3.0–4.1 to 1.0–1.4 pp per dataset, whereas building the table from all 25 °C rests left it unchanged, ruling out registration-data quality as the cause. E66's depression was about half as large (−3.31 pp at −20 °C), so S, which learned the development cells' magnitude, overcorrected (+3.23 pp at −20 °C). Weighting the development per-temperature gains by the test temperature mix predicted gains of +0.16 pp (P42A) and +1.15 pp (E66); observed gains were −0.01 and −0.04. Excluding the temperature-extrapolation folds, the preceding current, and the test type did not explain the gap. On development LODO samples, S and B2 were tied (1.85 vs 1.84 pp); S's development advantage over B2 came from the extrapolation folds.

**Two-point lookup on development data.** With T_low = 0 °C (registration from each dataset's 0 °C HPPC test; CALCE INR20R has none and is excluded) and scoring at −20, −10, and 40 °C, T2 reached 1.91 pp vs 1.93 (S), 1.99 (B2), and 3.39 (B1) (Table IV). Linear extrapolation above 25 °C raised the 40 °C error from 1.08 to 1.64 pp, which fixed the no-warm-extrapolation rule. T2 was committed (7d4bbc5) before any test data were touched for this purpose.

**Post hoc check on E66.** Applying the fixed T2 to E66 with its 0 °C GITT as the low registration (0 °C samples excluded) gave 1.34 pp vs 1.81 (S), 1.86 (B1), 1.90 (B2), and 1.77 (P); at −20 °C the bias fell from +3.23 (S) to −0.16 pp. Because E66 had been used in Test 1, this is exploratory.

**TABLE IV. Two-point lookup (MAE, pp, r = 300 s).**

| Data | n | B1 | B2 | S | T2 |
|---|---|---|---|---|---|
| Dev (LODO; −20, −10, 40 °C) | 462 | 3.39 | 1.99 | 1.93 | 1.91 |
| E66 (post hoc; −20, −10, 10, 40 °C) | 631 | 1.86 | 1.90 | 1.81 | 1.34 |

### D. Test 2 (preregistered): two-point lookup on unseen cells

The protocol, conversion, and runner were committed (cd29142) before the single run. Data: Plett ESC dynamic-profile tests, six cells, rests of about 12 min after each profile segment. Registration: each cell's 25 °C and −5 °C dynamic test (T_low = −5 °C is the available temperature closest to 0 °C, ties broken toward colder). Scoring: all rests at −25, −15, 5, 15, 35, and 45 °C (658 rests, 234 colder than T_low). CIs are paired cell-level bootstrap (six cells, B = 2000). Hypotheses: H3, T2 < S; H4, T2 < B1; a hypothesis is supported if the lower CI bound of the paired difference exceeds zero.

**TABLE V. Test 2 (MAE, pp, r = 300 s, 6 cells, 658 rests).**

| Method | All [95 % CI] | Bias | Method − T2 [95 % CI] | Colder than T_low (n = 234) |
|---|---|---|---|---|
| T2 | 5.23 [3.46, 7.41] | −3.30 | — | 11.18 |
| S | 5.80 [3.20, 8.94] | −3.22 | +0.57 [−0.35, 1.60] | 11.70 |
| B1 | 7.97 [4.63, 11.60] | −6.83 | +2.74 [1.08, 4.36] | 17.47 |
| B2 | 6.27 [3.53, 9.53] | −3.96 | +1.04 [−0.02, 2.25] | 12.64 |
| P | 5.80 [3.20, 9.09] | −3.27 | +0.57 [−0.30, 1.62] | 11.67 |

**H4 was supported; H3 was not.** By temperature (Fig. 3b), T2 was the most accurate method at −15 °C (6.64 vs 9.36 pp for S), 5 °C (1.94 vs 3.58), and 15 °C (1.88 vs 2.52); at 35 and 45 °C it equals B1 by construction; at −25 °C, 20 °C below T_low, every method failed (T2 15.34, S 13.84, B1 20.39 pp), with T2's linear extrapolation underestimating the depression. Per cell, T2 beat S on A123, ATL, and E2 and lost slightly on E1, P14, and SAM. Errors were larger than in Test 1 because Test 2 includes −25 °C and two cells with flat LFP-like OCV curves, where a voltage error maps to a large SOC error (Fig. 2c shows the ATL cell's −56 pp B1 bias at −25 °C).

**Post hoc: more registration temperatures.** Registering every available temperature except the test temperature and interpolating piecewise-linearly reduced Plett MAE to 3.19 pp (7.41 at −25 °C) and development MAE to 1.79 pp, but raised E66 MAE to 1.71 pp, where the low-temperature registrations (GITT) and most scored rests (HPPC) came from different test types. More registration temperatures help when the registration test resembles the field rest.

### E. Rest length and computation

MAE decreased with rest length for all methods in Test 2 (T2: 6.26, 5.23, and 4.65 pp at r = 60, 300, and 600 s). Median single-estimate latency on a laptop CPU was 0.5 ms (B1), 2.3 ms (S), and 4.4 ms (P), with a worst case of 42 ms for S, within a 100 ms server budget.

## VI. Discussion

**Why learned transfer failed.** The residual model learned, in effect, the average low-temperature depression of the development cells. LODO cross-validation could not test whether that magnitude transfers, because the held-out development cell always resembled the others in this respect. Test 1's E66 cell had half the depression, and the learned correction became an overcorrection. This is a general hazard of cross-validation over a handful of cells: the unit of generalization (here, a cell's thermal sensitivity) must vary across folds for cross-validation to measure transfer.

**Why two-point registration helps, and where it stops.** A single low-temperature registration measures the test cell's own depression, so no transfer is needed. Interpolation between registration temperatures worked well (Test 2 at 5 and 15 °C; development at −10 °C), and moderate extrapolation helped (−15 °C, 10 °C below T_low). Far extrapolation failed: the depression grows faster than linearly with cold, so at −25 °C a −5 °C registration was insufficient. A station operating in cold climates should register at the coldest expected temperature.

**Practical recommendation.** For a fleet of packs, a one-time 25 °C plus low-temperature registration per pack model (ideally per pack) is cheaper and more reliable than training a cross-cell model, and requires no learning infrastructure. Learned corrections may still help within a single cell model with many training cells, which our data could not test.

## VII. Limitations

- No real drone pack or flight-load data were available. Test rests follow constant-current, pulse, or drive-cycle discharges; Plett's dynamic profiles reach 0.5–4.9 C but are not flight profiles.
- Development data have one cell per dataset (two for CALCE), so development CIs reflect sample, not cell, variability; Test 1 E66 is a single cell from the same laboratory as part of the development data.
- Test 2 has six cells; its cell-level CIs are wide. The Plett ESC data carry no explicit license and are used with citation, without redistribution.
- S was selected after an ablation on development data; T2's variant was selected on development data. Both were frozen before their tests.
- The analyses on E66 and the dense-registration analysis on Plett are post hoc.
- Reference SOC uses 25 °C capacity; at low temperature, the deliverable capacity is smaller, which affects the interpretation of SOC but not the comparison between methods.

## VIII. Conclusion

From a 300 s rest after landing, room-temperature registration lookup estimated SOC on 13 unseen cells to 1.4 pp MAE, and a correction learned on other cells did not improve on it. The development gain of the learned correction came from the low-temperature rest-voltage depression, which is cell-specific. A training-free two-point registration that measures each cell's own depression beat room-temperature lookup in a second preregistered test and matched the learned correction, failing only far below its coldest registration point. Per-cell registration design, not model choice, is the main lever for rest-voltage SOC estimation on unseen cells.

## Data and Code Availability

Public datasets as cited. Code, protocols, and per-sample predictions are in the project repository; protocol commits: Test 1 14c47ae (protocol), d77e5e5 (conversion), 82f5722 (runner); Test 2 cd29142. TODO: public repository URL.

## Figures

- Fig. 1: Study design (`paper/figs/fig_design.png`).
- Fig. 2: Bias of 25 °C lookup (B1) vs temperature per cell; (a) development, (b) Test 1, (c) Test 2 (`fig_bias_vs_temp.png`). Points with fewer than five rests are omitted.
- Fig. 3: MAE vs temperature for B1, B2, S, T2; (a) E66 post hoc, (b) Test 2 (`fig_mae_vs_temp.png`).
- Fig. 4: Rest-voltage traces at eight temperatures near SOC 0.5, Plett cell E2 (`fig_rest_curves.png`).

## References

(Resolved from `paper/refs.md`.)
