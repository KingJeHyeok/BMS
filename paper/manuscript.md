# Rest-Matched Two-Point Registration for Fast State-of-Charge Estimation of Returning Drone Batteries with Low-Cost Sensing

*Draft v1 (2026-11-18), methods framing. Target: IEEE Access. [TEST3] marks values pending the preregistered Test 3.*

## Abstract

Battery stations for drones must estimate the state of charge (SOC) of a returning pack within minutes of landing, when coulomb-counting estimates from low-cost sensors have drifted. The rest voltage after landing is an attractive observation, but the rest is short, the temperature varies, and the measurement chain is inexpensive. Existing options either read a room-temperature open-circuit-voltage (OCV) table, which ignores the large low-temperature depression of the rest voltage, or correct it with a model learned on other cells, which we show does not transfer to new cells. We propose rest-matched two-point registration (RM2P). Each cell type is registered once at 25 °C and once at a low temperature with rests of the same length as in the field. SOC is read from both tables and interpolated in the SOC domain by temperature, without extrapolation above 25 °C. RM2P needs no training data and runs in under 1 ms. We evaluated it with a development phase on five public datasets and three preregistered single-run tests on 23 unseen cells from three laboratories. A learned residual-correction model that reduced development error from 3.40 to 2.11 percentage points (pp) gave no gain over room-temperature lookup on 13 unseen cells (1.43 vs 1.41 pp), because the low-temperature depression is cell-specific. On six unseen cells spanning −25 to 45 °C, RM2P reduced mean absolute error relative to room-temperature lookup from 7.97 to 5.23 pp (paired 95 % CI of the reduction [1.08, 4.36]) and matched the learned model without any training (5.80 pp; difference not significant). Against a conventional voltage-domain temperature-dependent OCV model built from the same two registrations, RM2P was more accurate in development (2.56 vs 1.91 pp) and [TEST3]. RM2P was most accurate between −15 and 15 °C; far below the coldest registration temperature, all methods failed.

**Index Terms:** state of charge, open-circuit voltage, rest voltage, temperature compensation, lithium-ion battery, battery station, unmanned aerial vehicle, low-cost sensing, preregistration.

## I. Introduction

Battery stations that recharge or swap packs for drones must decide, shortly after each landing, how much charge a returning pack holds. That decision sets charging priority, determines whether the pack can fly the next mission, and flags packs whose capacity has faded [30, 31, 33]. Coulomb counting during flight is the usual source, but with low-cost Hall-effect current sensors its error grows with sensor offset, gain error, and capacity uncertainty [28, 29]. The rest after landing offers an independent observation: the terminal voltage relaxes toward the OCV, which maps monotonically to SOC [2, 4, 9].

Three properties of this setting defeat the textbook approach of reading an equilibrium OCV table. First, the rest available before the station must act lasts minutes, whereas full relaxation takes hours, especially in the cold [12, 13]. Second, ambient temperature varies between missions, and both the OCV and the residual overpotential after a short rest depend strongly on temperature; at −20 °C, a 25 °C table underestimated SOC by 3–7 pp on the cells we studied, and by more than 50 pp on one cell at −25 °C. Third, the voltage is read through an inexpensive analog front end.

Existing remedies fall into three groups. Temperature-dependent OCV models identify OCV(z, T) from slow tests at several temperatures and invert it for a measured voltage [1, 2, 7, 8, 10]; they model the equilibrium voltage, not the voltage after a short rest. Relaxation models fit the first minutes of a rest and extrapolate its asymptote [12, 13, 14, 15, 16]. Data-driven models learn SOC, or a correction to a lookup, from voltage-shape features and temperature [17, 18, 19, 20, 21]; their transfer to cells outside the training set is rarely tested under controlled conditions [22, 23, 24, 25, 26].

We propose rest-matched two-point registration (RM2P), which keeps estimation entirely per cell type. A one-time registration is run at 25 °C and at one low temperature, recording rests of the same length r as in the field. Each registration yields a monotone table from the rest-end voltage to SOC. In the field, the measured rest-end voltage is read in both tables, and the two SOC values are interpolated by ambient temperature in the SOC domain, without extrapolation above 25 °C. RM2P has no trained parameters.

Our contributions are:
1. **RM2P**, a training-free rest-voltage SOC estimator for battery stations. It combines rest-matched registration tables (so temperature-dependent incomplete relaxation is captured, not just the equilibrium OCV), SOC-domain temperature interpolation (more robust than inverting a voltage-domain model on flat OCV segments), and an asymmetric extrapolation rule.
2. **Evidence that the leading alternative, cross-cell learned correction, does not transfer,** with a mechanism. In a preregistered test on 13 unseen cells, a residual gradient-boosting model with a 1.3 pp development gain gave no gain over room-temperature lookup. The low-temperature rest-voltage depression is cell-specific, and leave-one-dataset-out cross-validation over similar cells did not reveal this.
3. **Preregistered superiority tests.** RM2P beat room-temperature lookup on six unseen cells from another laboratory (Test 2), matched the learned model without training, and was compared with a conventional voltage-domain temperature-dependent OCV model, temperature-corrected lookup, and two-RC relaxation extrapolation on four further unseen cells (Test 3). Every protocol was committed before its test run.
4. **Deployment characteristics:** sub-millisecond inference, robustness to a simulated 12-bit divider front end, and a registration procedure suited to station commissioning.

## II. Related Work

**Temperature-dependent OCV.** The OCV–SOC curve underlies most SOC estimators [2, 4, 9]. The OCV shifts with temperature through the entropy change of intercalation [11]. Its temperature dependence is commonly modeled as OCV(z, T) = OCV0(z) + T·OCVrel(z), identified from slow-rate tests at several temperatures, as in Plett's enhanced self-correcting (ESC) model [1, 2, 3]. Hysteresis adds a path-dependent term, important for LFP [5, 6]. These models describe the equilibrium voltage. RM2P differs in three ways: its tables describe the voltage after a rest of the field length, it interpolates in the SOC domain, and it needs only two registrations. We compare against a voltage-domain model of the ESC form built from the same two registrations (ESC2).

**Rest and relaxation-based OCV estimation.** Equivalent-circuit relaxation fits extrapolate the asymptotic voltage from the first minutes of a rest; learned mappings from short rests to OCV have also been proposed [12, 13, 14, 15, 16]. We include a two-RC extrapolation baseline (B3).

**Data-driven SOC estimation and generalization.** Gradient-boosted trees and neural networks estimate SOC from voltage, current, and temperature histories [17, 18, 19, 20, 21]. Transfer learning and domain adaptation target cross-cell and cross-temperature use [22, 23]. Random or within-cell splits are known to overestimate performance [24, 25, 26]. We show that even leave-one-dataset-out validation overstated transfer when the held-out cells were similar in the property that mattered.

**Low-cost sensing.** Robustness to sensor offset, noise, and quantization has mostly been studied with assumed error injections [29]. We inject the gain, offset, noise, and quantization of a divider plus 12-bit ADC into every test voltage.

**Drone battery stations.** Automatic battery replacement and recharging stations enable persistent multi-vehicle UAV missions and require the state of each returning pack to schedule charging and dispatch [30, 31]. SOC estimation for UAV packs has mostly used filter-based estimators during flight [33], and recent eVTOL datasets document mission-profile loads [32]. The post-landing rest, available at every station visit, has received little attention as a standalone observation.

**Preregistration.** Committing hypotheses and analysis plans before seeing test data guards against overfitting evaluation choices [34, 35]. We are not aware of preregistered evaluations in battery-state estimation.

## III. Problem Setup

### A. Task
A sample is one rest following a discharge. The input is the first r seconds of rest voltage at 1 Hz (r = 300 s primary; 60 and 600 s secondary) and the ambient temperature T; the output is SOC. Each test cell has registration rests with known SOC at 25 °C and, for RM2P and ESC2, at one low temperature T_low. Registration samples are never scored.

### B. Sample definition and reference SOC
A rest is a period of at least 300 s with |I| < I_rest = C_nom/150, preceded by a discharge (mean current over the last 60 s below −I_rest) and at least 300 s of recording. Reference SOC is 1 + Q(t)/Q25, where Q(t) is the signed charge since the most recent full-charge anchor and Q25 the cell's maximum discharged capacity at 25 °C. Samples with SOC outside (−0.02, 1.02) are dropped.

### C. Measurement-error model and temperature input
Every test voltage passes through a simulated low-cost chain: per-sample gain error N(0, 0.2 %), offset N(0, 5 mV), white noise N(0, 2 mV), and a 6.2 mV quantization step (12-bit ADC behind a 100 kΩ/15 kΩ divider at 3.3 V). Three error seeds are used. The temperature input is the chamber's nominal temperature plus N(0, 2 °C) noise, emulating a station ambient sensor.

## IV. Proposed Method: RM2P

**Registration.** For a cell type (ideally each pack), run two registration tests that produce rests of at least r seconds at known SOC across the SOC range: one at 25 °C and one at T_low. Pulse, GITT-type, or dynamic-profile tests all qualify; the rests should follow discharges similar to field use. From each test, form the rest-end voltage ṽ = mean of the last 15 s of the first r seconds, and fit an isotonic (monotone non-decreasing) regression g_T(ṽ) → SOC. The 15 s mean suppresses quantization and noise.

**Estimation.** For a field rest with end voltage ṽ at ambient temperature T:

s25 = g_25(ṽ), s_low = g_Tlow(ṽ), w = max(0, (T − 25)/(T_low − 25)),

SOC = clip(s25 + w (s_low − s25), 0, 1).

Between T_low and 25 °C this is linear interpolation; below T_low it extrapolates linearly; above 25 °C it uses the 25 °C table.

**Design rationale.**
- *Rest-matched tables.* After 300 s, especially in the cold, the voltage remains well below equilibrium (Fig. 4). A table built from rests of the same length absorbs this temperature-dependent overpotential; an equilibrium OCV table cannot.
- *SOC-domain interpolation.* Interpolating two SOC readings avoids inverting an interpolated voltage curve, which amplifies errors where the OCV is flat (dV/dz small, e.g. LFP plateaus).
- *No warm extrapolation.* Rest-voltage depression changes little above room temperature; extrapolating the 0–25 °C trend upward degraded accuracy in development (Section VI-B).
- *Cost.* Two isotonic lookups and one interpolation: 0.5 ms per estimate on a laptop CPU.

The variant was fixed on development data among four candidates (interpolation linear in T or 1/T, weight clipped to [0, 1], no warm extrapolation) and committed before any test (commit 7d4bbc5).

## V. Compared Methods

- **B0, global OCV table:** isotonic SOC vs end voltage pooled over training cells; no per-cell registration.
- **B1, 25 °C registration lookup:** g_25(ṽ). The conventional single-temperature approach.
- **B2, temperature-corrected lookup:** B1 + β·[1, ΔT, ΔT², ΔT·B1], ΔT = T − 25 °C, with β fitted by least squares on training cells.
- **B3, two-RC relaxation extrapolation:** the asymptote of a two-RC fit to the rest replaces ṽ in B1.
- **B4, gradient boosting:** XGBoost predicting SOC from rest-shape features and temperature.
- **ESC2, voltage-domain temperature-dependent OCV:** from the same two registrations, V_T(z) is obtained by isotonic regression of ṽ on SOC at 25 °C and T_low; V(z, T) = V_25(z) + a (V_Tlow(z) − V_25(z)), a = (T − 25)/(T_low − 25); SOC solves V(z, T) = ṽ. This is the ESC OCV form [1, 2] identified from two temperatures.
- **S, learned residual correction:** XGBoost (300 trees, depth 3, learning rate 0.05, subsample 0.8, absolute-error loss, monotone in end voltage and relaxation increments) predicting SOC − B1 from the end voltage, five relaxation increments (end minus 5-point means at 4, 9, 29, 59 s and r/2), a late-relaxation ratio, the B1 SOC, and ambient temperature. It is trained with overpotential-amplitude augmentation (log-uniform factor in [0.1, 4] about a two-RC asymptote, six copies), dataset × SOC-bin weights, and a bag of five. This was our initial approach. It was selected by ablation (Section VI-A); a fuller variant P is reported as secondary.

## VI. Experiments

### A. Development and the learned baseline

**Data.** Five public datasets: LG HG2 (NMC), Panasonic 18650PF (NCA), CALCE INR20R (NMC, two cells), Samsung 30T (NMC), and Turnigy Graphene (LiPo). They cover −20 to 40 °C (CALCE: 0 and 25 °C) [8, 9, 18, 36, 37, 38, 39, 40]. Registration is each dataset's first 25 °C HPPC (CALCE: incremental OCV) test. Development folds are leave-one-dataset-out (LODO) plus temperature-extrapolation folds (train −10 to 25 °C, test −20 and 40 °C); the development metric averages the two.

**TABLE I. Development (MAE, pp, r = 300 s; 676 LODO + 299 extrapolation rests).**

| Method | Dev metric [95 % CI] | LODO | Extrap. |
|---|---|---|---|
| B0 | 10.76 | 10.66 | 10.87 |
| B1 | 3.40 | 3.06 | 3.75 |
| B2 | 2.26 | 1.96 | 2.56 |
| B3 | 3.30 | 2.87 | 3.73 |
| B4 | 3.82 | 3.25 | 4.39 |
| P | 2.11 [1.90, 2.32] | 1.87 | 2.35 |
| S | 2.08 [1.89, 2.27] | 1.91 | 2.24 |

Ablation (increase when removed): residual on B1 +1.42, balance weights +0.28, temperature input +0.20, amplitude augmentation +0.13; other components contributed nothing, which defined S.

### B. RM2P in development

With T_low = 0 °C (each dataset's 0 °C HPPC; CALCE excluded for lack of one) and scoring at −20, −10, and 40 °C (462 LODO rests), Table II compares RM2P with the alternatives on identical samples. RM2P was best overall. It beat ESC2, built from the same registrations, by 0.65 pp [0.47, 0.86]. Extrapolating above 25 °C (the linear-in-T variant) raised the 40 °C error from 1.08 to 1.64 pp.

**TABLE II. Development, two-temperature methods (MAE / bias, pp, r = 300 s).**

| Temp. | n | B1 | B2 | S | ESC2 | RM2P |
|---|---|---|---|---|---|---|
| All | 462 | 3.39 / −2.99 | 1.99 | 1.93 / +0.58 | 2.56 / −2.03 | **1.91** / −1.18 |
| −20 °C | 120 | 6.57 | 3.32 | 2.54 | 4.61 | 3.20 |
| −10 °C | 163 | 3.60 | 1.76 | 2.07 | 1.99 | 1.86 |
| 40 °C | 179 | 1.08 | 1.29 | 1.39 | 1.70 | 1.08 |

### C. Test 1 (preregistered): does the learned correction transfer?

Before RM2P existed, we froze S and tested it on LG E66 (one 65 Ah pouch cell; −20 to 40 °C) [41, 42] and Molicel P42A (12 cells; 5 and 40 °C) [43, 44]. The protocol was committed as 14c47ae, the conversion as d77e5e5, and the runner as 82f5722, all before the single run. Hypotheses: H1, S < B1; H2, S < B2.

**TABLE III. Test 1 (MAE, pp, r = 300 s; CI over cells for P42A, samples for E66).**

| Method | E66 (794 rests) | P42A (571 rests, 12 cells) | Mean |
|---|---|---|---|
| S | 1.775 [1.68, 1.86] | 1.092 [1.03, 1.16] | 1.434 |
| B1 | 1.738 [1.63, 1.85] | 1.082 [1.00, 1.18] | 1.410 |
| B2 | 1.793 [1.69, 1.89] | 1.143 [1.08, 1.21] | 1.468 |
| P | 1.719 [1.63, 1.81] | 1.161 [1.11, 1.22] | 1.440 |

Neither H1 (B1 − S: −0.04 [−0.15, 0.08] on E66; −0.01 [−0.14, 0.11] on P42A) nor H2 was supported.

**Mechanism (Fig. 2).** On development cells, B1's bias grew with cold: −6.57 pp at −20 °C, −3.58 at −10 °C, −1.99 at 0 °C, −0.05 at 40 °C. The three development datasets measured at −20 °C with more than five rests clustered between −6.1 and −6.9 pp. E66's depression was half as large (−3.31 pp), so S, which had learned the development magnitude, overcorrected (+3.23 pp). A same-temperature oracle table cut B1 from 3.0–4.1 to 1.0–1.4 pp per dataset, while rebuilding the table from all 25 °C rests changed nothing, so registration quality was not the cause. Other candidate causes failed to explain the gap: the extrapolation folds, the preceding current, and the test type. The depression is a per-cell property, and only a per-cell measurement captures it. This motivated RM2P. Applied post hoc to E66 with its 0 °C GITT registration, RM2P reduced MAE to 1.34 pp (S 1.81, B1 1.86; 0 °C rests excluded), and the −20 °C bias to −0.16 pp.

### D. Test 2 (preregistered): RM2P on unseen cells

**Data.** Plett ESC toolbox dynamic tests [2, 45]: six cells (A123, ATL, E1, E2, P14, SAM; 2.1–19.4 Ah, including two with LFP-like flat OCV curves), eight temperatures from −25 to 45 °C, with rests of about 12 min after dynamic-profile segments peaking at 0.5–4.9 C. Registration used each cell's 25 °C and −5 °C tests (T_low = the temperature closest to 0 °C, ties toward colder). Scoring used 658 rests at the other six temperatures. The protocol, conversion, and runner were committed as cd29142 before the single run. Hypotheses: H3, RM2P < S; H4, RM2P < B1 (paired cell-level bootstrap, six cells, B = 2000; supported if the lower bound of the paired difference exceeds 0).

**TABLE IV. Test 2 (MAE, pp, r = 300 s).**

| Method | All [95 % CI] | Method − RM2P [95 % CI] | −25 °C | −15 °C | 5 °C | 15 °C | 35 °C | 45 °C |
|---|---|---|---|---|---|---|---|---|
| RM2P | **5.23** [3.46, 7.41] | — | 15.34 | **6.64** | **1.94** | **1.88** | 1.84 | 2.14 |
| S | 5.80 [3.20, 8.94] | +0.57 [−0.35, 1.60] | 13.84 | 9.36 | 3.58 | 2.52 | 1.89 | 2.10 |
| B1 | 7.97 [4.63, 11.60] | +2.74 [1.08, 4.36] | 20.39 | 14.29 | 4.27 | 2.53 | 1.84 | 2.14 |
| B2 | 6.27 [3.53, 9.53] | +1.04 [−0.02, 2.25] | 14.86 | 10.22 | 3.84 | 2.58 | 1.90 | 2.63 |
| P | 5.80 [3.20, 9.09] | +0.57 [−0.30, 1.62] | 14.04 | 9.08 | 3.37 | 2.31 | 2.17 | 2.35 |

**H4 was supported; H3 was not.** RM2P was the most accurate method from −15 to 15 °C. At −25 °C, 20 °C below T_low, linear extrapolation under-corrected and every method failed. Absolute errors were higher than in Test 1 because of the −25 °C condition and the flat-OCV cells (ATL B1 bias −56 pp at −25 °C, Fig. 2c). Post hoc, on the same samples, ESC2 reached 6.04 pp (RM2P better by 0.81 [0.55, 1.08]).

### E. Test 3 (preregistered): RM2P vs conventional methods [TEST3]

**Data.** Tesla Model 3 2170 (Panasonic NCA, three cells) [46] and SB LiMotive (one cell) [47], from McMaster University: HPPC tests at −20, −10, 0, 10, 25, and 40 °C. Registration used 25 °C and 0 °C HPPC; scoring used all rests at −20, −10, 10, and 40 °C. Hypotheses: H5 RM2P < B1, H6 RM2P < ESC2, H7 RM2P < B2. Inference uses a paired bootstrap over (cell, temperature) clusters with Holm correction. B3 and S are reported without hypotheses; S is fair only where the rest's first 60 s are truly logged at 1 s.

[TEST3 table and outcomes]

### F. Rest length, computation, and more registration points

RM2P's error fell with rest length (Test 2: 6.26, 5.23, and 4.65 pp at r = 60, 300, and 600 s). Median latency was 0.5 ms (RM2P, B1), 2.3 ms (S), and 4.4 ms (P); the worst case for S was 42 ms. Post hoc, registering every available temperature except the test temperature reduced Test 2 MAE to 3.19 pp, including 7.41 at −25 °C. A third registration near the coldest operating temperature is therefore the natural extension where cold operation is expected.

## VII. Discussion

**Why per-cell registration beats cross-cell learning here.** The quantity that matters most, the rest-voltage depression at low temperature, varies between cells by a factor of two or more (Fig. 2), consistent with known cell-to-cell and type-to-type variation in battery parameters [27]. A learned model can only reproduce the average of its training cells. A single low-temperature registration measures the cell's own value. Leave-one-dataset-out validation did not expose the problem because the development cells happened to be similar; validation must vary the property that drives generalization.

**Why SOC-domain interpolation beats voltage-domain models.** ESC2 interpolates voltage curves and then inverts them. Where the curve is flat, small voltage errors produce large SOC errors, and quantization makes this worse. RM2P interpolates two already-inverted readings, so the flat-region error is not compounded.

**Station practice.** RM2P fits station commissioning: register each new pack type at 25 °C and at the coldest planned operating temperature, using the same rest length as in operation. The station then needs only an ambient sensor and two lookups per landing.

## VIII. Limitations

- No real drone pack or flight-load data were available. Test rests follow constant-current, pulse, or dynamic-profile discharges, and Plett's dynamic profiles are not flight profiles.
- RM2P extrapolates poorly far below T_low (−25 °C in Test 2).
- Development data have one cell per dataset (two for CALCE), and E66 comes from the same laboratory as some development data.
- Test 2 has six cells, so its cell-level CIs are wide. The Plett ESC data carry no explicit license and are cited without redistribution.
- S was selected after an ablation, and RM2P's variant on development data; both were frozen before their tests. The E66 and dense-registration analyses are post hoc.
- Reference SOC uses the 25 °C capacity. The deliverable capacity in the cold is smaller; this does not affect the comparison between methods.

## IX. Conclusion

RM2P estimates SOC from a short post-landing rest using two per-cell registrations and no training. In preregistered tests on unseen cells, it improved on conventional room-temperature OCV lookup and matched a learned correction model that itself failed to transfer to new cells, and [TEST3]. The low-temperature rest-voltage depression is cell-specific; measuring it per cell, rather than learning it from other cells, is the effective and inexpensive way to handle it.

## Data and Code Availability
Datasets as cited. Code, protocols, and per-sample predictions are in the project repository. Protocol commits: Test 1 14c47ae (protocol), d77e5e5 (conversion), 82f5722 (runner); Test 2 cd29142; Test 3 [TEST3]. TODO: public URL.

## Figures
- Fig. 1: Study design (`paper/figs/fig_design.png`). TODO: add Test 3 box.
- Fig. 2: Bias of 25 °C lookup vs temperature per cell (`fig_bias_vs_temp.png`); points with fewer than five rests omitted.
- Fig. 3: MAE vs temperature, (a) E66 post hoc, (b) Test 2 (`fig_mae_vs_temp.png`). TODO: add ESC2.
- Fig. 4: Rest-voltage traces at eight temperatures near SOC 0.5, Plett cell E2 (`fig_rest_curves.png`).

## References

[1] G. L. Plett, "Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs: Part 2. Modeling and identification," *J. Power Sources*, vol. 134, no. 2, pp. 262–276, 2004, doi: 10.1016/j.jpowsour.2004.02.032.

[2] G. L. Plett, *Battery Management Systems, Volume I: Battery Modeling*. Norwood, MA, USA: Artech House, 2015, ISBN 978-1-63081-023-8.

[3] G. L. Plett, *Battery Management Systems, Volume II: Equivalent-Circuit Methods*. Norwood, MA, USA: Artech House, 2015, ISBN 978-1-63081-027-6.

[4] M. Petzl and M. A. Danzer, "Advancements in OCV measurement and analysis for lithium-ion batteries," *IEEE Trans. Energy Convers.*, vol. 28, no. 3, pp. 675–681, 2013, doi: 10.1109/TEC.2013.2259490.

[5] A. Barai, W. D. Widanage, J. Marco, A. McGordon, and P. Jennings, "A study of the open circuit voltage characterization technique and hysteresis assessment of lithium-ion cells," *J. Power Sources*, vol. 295, pp. 99–107, 2015, doi: 10.1016/j.jpowsour.2015.06.140.

[6] M. A. Roscher and D. U. Sauer, "Dynamic electric behavior and open-circuit-voltage modeling of LiFePO4-based lithium ion secondary batteries," *J. Power Sources*, vol. 196, no. 1, pp. 331–336, 2011, doi: 10.1016/j.jpowsour.2010.06.098.

[7] A. Farmann and D. U. Sauer, "A study on the dependency of the open-circuit voltage on temperature and actual aging state of lithium-ion batteries," *J. Power Sources*, vol. 347, pp. 1–13, 2017, doi: 10.1016/j.jpowsour.2017.01.098.

[8] Y. Xing, W. He, M. Pecht, and K. L. Tsui, "State of charge estimation of lithium-ion batteries using the open-circuit voltage at various ambient temperatures," *Appl. Energy*, vol. 113, pp. 106–115, 2014, doi: 10.1016/j.apenergy.2013.07.008.

[9] F. Zheng, Y. Xing, J. Jiang, B. Sun, J. Kim, and M. Pecht, "Influence of different open circuit voltage tests on state of charge online estimation for lithium-ion batteries," *Appl. Energy*, vol. 183, pp. 513–525, 2016, doi: 10.1016/j.apenergy.2016.09.010.

[10] Y. Wei and L. Ling, "State-of-charge estimation for lithium-ion batteries based on temperature-based fractional-order model and dual fractional-order Kalman filter," *IEEE Access*, vol. 10, pp. 37131–37148, 2022, doi: 10.1109/ACCESS.2022.3163413.

[11] V. V. Viswanathan et al., "Effect of entropy change of lithium intercalation in cathodes and anodes on Li-ion battery thermal management," *J. Power Sources*, vol. 195, no. 11, pp. 3720–3729, 2010, doi: 10.1016/j.jpowsour.2009.11.103.

[12] W. Waag and D. U. Sauer, "Adaptive estimation of the electromotive force of the lithium-ion battery after current interruption for an accurate state-of-charge and capacity determination," *Appl. Energy*, vol. 111, pp. 416–427, 2013, doi: 10.1016/j.apenergy.2013.05.001.

[13] L. Pei, T. Wang, R. Lu, and C. Zhu, "Development of a voltage relaxation model for rapid open-circuit voltage prediction in lithium-ion batteries," *J. Power Sources*, vol. 253, pp. 412–418, 2014, doi: 10.1016/j.jpowsour.2013.12.083.

[14] J. Meng, D.-I. Stroe, M. Ricco, G. Luo, M. Swierczynski, and R. Teodorescu, "A novel multiple correction approach for fast open circuit voltage prediction of lithium-ion battery," *IEEE Trans. Energy Convers.*, vol. 34, no. 2, pp. 1115–1123, 2019, doi: 10.1109/TEC.2018.2880561.

[15] Y. Qian et al., "Fast open circuit voltage estimation of lithium-ion batteries using a relaxation model and genetic algorithm," *IEEE Access*, vol. 10, pp. 96643–96651, 2022, doi: 10.1109/ACCESS.2022.3203178.

[16] C.-J. Ko and K.-C. Chen, "Using tens of seconds of relaxation voltage to estimate open circuit voltage and state of health of lithium ion batteries," *Appl. Energy*, vol. 357, Art. no. 122488, 2024, doi: 10.1016/j.apenergy.2023.122488.

[17] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in *Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discovery Data Mining*, 2016, pp. 785–794, doi: 10.1145/2939672.2939785.

[18] E. Chemali, P. J. Kollmeyer, M. Preindl, R. Ahmed, and A. Emadi, "Long short-term memory networks for accurate state-of-charge estimation of Li-ion batteries," *IEEE Trans. Ind. Electron.*, vol. 65, no. 8, pp. 6730–6739, 2018, doi: 10.1109/TIE.2017.2787586.

[19] C. Vidal, P. Malysz, P. Kollmeyer, and A. Emadi, "Machine learning applied to electrified vehicle battery state of charge and state of health estimation: State-of-the-art," *IEEE Access*, vol. 8, pp. 52796–52814, 2020, doi: 10.1109/ACCESS.2020.2980961.

[20] D. N. T. How, M. A. Hannan, M. S. H. Lipu, and P. J. Ker, "State of charge estimation for lithium-ion batteries using model-based and data-driven methods: A review," *IEEE Access*, vol. 7, pp. 136116–136136, 2019, doi: 10.1109/ACCESS.2019.2942213.

[21] D. Wang, J. Hwang, J. Lee, M. Kim, and I. Lee, "Temperature-based state-of-charge estimation using neural networks, gradient boosting machine and a Jetson Nano device for batteries," *Energies*, vol. 16, no. 6, Art. no. 2639, 2023, doi: 10.3390/en16062639.

[22] C. Vidal, P. Kollmeyer, E. Chemali, and A. Emadi, "Li-ion battery state of charge estimation using long short-term memory recurrent neural network with transfer learning," in *Proc. IEEE Transp. Electrific. Conf. Expo (ITEC)*, 2019, pp. 1–6, doi: 10.1109/ITEC.2019.8790543.

[23] L. Shen, J. Li, L. Zuo, L. Zhu, and H. T. Shen, "Source-free cross-domain state of charge estimation of lithium-ion batteries at different ambient temperatures," *IEEE Trans. Power Electron.*, vol. 38, no. 6, pp. 6851–6862, 2023, doi: 10.1109/TPEL.2023.3251568.

[24] S. Kapoor and A. Narayanan, "Leakage and the reproducibility crisis in machine-learning-based science," *Patterns*, vol. 4, no. 9, Art. no. 100804, 2023, doi: 10.1016/j.patter.2023.100804.

[25] D. R. Roberts et al., "Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure," *Ecography*, vol. 40, no. 8, pp. 913–929, 2017, doi: 10.1111/ecog.02881.

[26] S. Yan and M. Wiston, "Mission-phase feature learning for eVTOL Li-ion battery prognostics: A leakage-safe cell-held-out benchmark for SOC, SOH, and RUL," *Batteries*, vol. 12, no. 9, Art. no. 322, 2026, doi: 10.3390/batteries12090322.

[27] M. Dubarry, N. Vuillaume, and B. Y. Liaw, "Origins and accommodation of cell variations in Li-ion battery pack modeling," *Int. J. Energy Res.*, vol. 34, no. 2, pp. 216–231, 2010, doi: 10.1002/er.1668.

[28] X. Lin and A. G. Stefanopoulou, "Analytic bound on accuracy of battery state and parameter estimation," *J. Electrochem. Soc.*, vol. 162, no. 9, pp. A1879–A1891, 2015, doi: 10.1149/2.0791509jes.

[29] J.-H. Hwang, J.-H. Lee, and I. S. Lee, "Analysis and diagnosis of the effect of voltage and current sensor faults on the state of charge estimation of lithium-ion batteries based on neural networks," *Int. J. Control Autom. Syst.*, vol. 22, no. 5, pp. 1691–1706, 2024, doi: 10.1007/s12555-023-0546-9.

[30] K. A. O. Suzuki, P. Kemper Filho, and J. R. Morrison, "Automatic battery replacement system for UAVs: Analysis and design," *J. Intell. Robot. Syst.*, vol. 65, no. 1–4, pp. 563–586, 2012, doi: 10.1007/s10846-011-9616-y.

[31] N. K. Ure, G. Chowdhary, T. Toksoz, J. P. How, M. A. Vavrina, and J. Vian, "An automated battery management system to enable persistent missions with multiple aerial vehicles," *IEEE/ASME Trans. Mechatronics*, vol. 20, no. 1, pp. 275–286, 2015, doi: 10.1109/TMECH.2013.2294805.

[32] A. Bills et al., "A battery dataset for electric vertical takeoff and landing aircraft," *Sci. Data*, vol. 10, Art. no. 344, 2023, doi: 10.1038/s41597-023-02180-5.

[33] H. Zhang, M. Zhou, and X. Lan, "State of charge estimation algorithm for unmanned aerial vehicle power-type lithium battery packs based on the extended Kalman filter," *Energies*, vol. 12, no. 20, Art. no. 3960, 2019, doi: 10.3390/en12203960.

[34] B. A. Nosek, C. R. Ebersole, A. C. DeHaven, and D. T. Mellor, "The preregistration revolution," *Proc. Natl. Acad. Sci. USA*, vol. 115, no. 11, pp. 2600–2606, 2018, doi: 10.1073/pnas.1708274114.

[35] O. E. Gundersen and S. Kjensmo, "State of the art: Reproducibility in artificial intelligence," in *Proc. AAAI Conf. Artif. Intell.*, vol. 32, no. 1, 2018, doi: 10.1609/aaai.v32i1.11503.

[36] P. Kollmeyer, C. Vidal, M. Naguib, and M. Skells, "LG 18650HG2 Li-ion battery data and example deep neural network xEV SOC estimator script," Mendeley Data, V3, 2020, doi: 10.17632/cp3473x7xv.3.

[37] C. Vidal, P. Kollmeyer, M. Naguib, P. Malysz, O. Gross, and A. Emadi, "Robust xEV battery state-of-charge estimator design using a feedforward deep neural network," *SAE Int. J. Adv. Curr. Pract. Mobility*, vol. 2, no. 5, pp. 2872–2880, 2020, doi: 10.4271/2020-01-1181.

[38] P. Kollmeyer, "Panasonic 18650PF Li-ion battery data," Mendeley Data, V1, 2018, doi: 10.17632/wykht8y7tg.1.

[39] P. Kollmeyer, "Samsung INR21700 30T 3Ah Li-ion battery data," Mendeley Data, V1, 2020, doi: 10.17632/9xyvy2njj3.1.

[40] P. Kollmeyer, "Turnigy Graphene 5000mAh 65C Li-ion battery data," Mendeley Data, V1, 2020, doi: 10.17632/4fx8cjprxm.1.

[41] L. Uwalaka, Q. Yao, J. Duque, and P. Kollmeyer, "Fast charging and characterization dataset for Porsche Taycan LG E66 battery cell and module," Borealis, V1.0, 2024, doi: 10.5683/SP3/7JP3NM.

[42] L. Uwalaka, Q. Yao, J. Duque, P. Kollmeyer, and A. Emadi, "Experimental performance analysis of LG E-66 cells from a fast-charging Porsche Taycan battery module," in *Proc. IEEE Transp. Electrific. Conf. Expo (ITEC)*, 2024, pp. 1–6, doi: 10.1109/ITEC60657.2024.10599015.

[43] M. A. Khan, S. Thatipamula, L. Tresca, L. Xu, A. Trewartha, and S. Onori, "High-power lithium-ion battery characterization dataset for stochastic battery modeling," *Sci. Data*, vol. 12, Art. no. 1506, 2025, doi: 10.1038/s41597-025-05725-y.

[44] S. Onori, L. Xu, V. S. Thatipamula, M. A. Khan, L. Tresca, and A. Trewartha, "High-power lithium-ion battery characterization dataset for stochastic battery modeling," OSF, 2025, doi: 10.17605/OSF.IO/9CEAV.

[45] G. L. Plett, "ESCtoolbox" (MATLAB toolbox with OCV and dynamic test data for six cells at −25 to 45 °C, supplementary material to [2]), Univ. Colorado Colorado Springs. [Online]. Available: http://mocha-java.uccs.edu/BMS1/CH02/ESCtoolbox.zip (accessed Nov. 18, 2026).

[46] P. J. Kollmeyer, F. Khanum, M. Naguib, and A. Emadi, "Tesla Model 3 2170 Li-ion cell dataset and battery SOC estimation blind modeling tool," Borealis, 2023, doi: 10.5683/SP3/ZVTR4B.

[47] P. J. Kollmeyer and M. Skells, "Multi temperature Li-ion battery data - SB LiMotive 5Ah," Borealis, 2023, doi: 10.5683/SP3/LFPKAS.
