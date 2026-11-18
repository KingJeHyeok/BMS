# Rest-Matched Two-Point Registration for Fast State-of-Charge Estimation of Returning Drone Batteries with Low-Cost Sensing

*Draft v2 (2026-11-18), revised after review round 1. Target: IEEE Access. [TEST3] marks values pending the preregistered Test 3.*

## Abstract

Battery stations for drones need the state of charge (SOC) of a returning pack within minutes of landing, at a point when coulomb-counting estimates from low-cost sensors have drifted. The rest voltage after landing is a useful observation, but the rest is short, the temperature varies, and the measurement chain is inexpensive. Temperature-dependent open-circuit-voltage (OCV) models describe the equilibrium voltage. After a few minutes of rest, especially in the cold, the terminal voltage is still far from equilibrium. Data-driven corrections learned on other cells may not transfer to new cells. We propose rest-matched two-point registration (RM2P). Each cell type is registered once at 25 °C and once at a low temperature, using rests of the same length as in the field. The field rest-end voltage is read in both monotone tables, and the two SOC readings are interpolated by ambient temperature, without extrapolation above 25 °C. RM2P has no trained parameters and takes about 1 ms per estimate. We evaluated it on five public development datasets and in three preregistered single-run tests on 23 unseen cells from three laboratories. In Test 2 (six cells, −25 to 45 °C), RM2P reduced mean absolute error relative to 25 °C lookup from 7.97 to 5.23 percentage points (pp) (cell-bootstrap 95 % CI of the reduction [1.08, 4.36]; better in 5 of 6 cells). It was statistically indistinguishable from a learned residual-correction model (5.80 pp). That learned model gained nothing over 25 °C lookup on 13 other unseen cells in Test 1, because the low-temperature rest-voltage depression is cell-specific. In post hoc analyses on Test 2, equilibrium-OCV models from Plett-style OCV tests were less accurate than RM2P, even with hysteresis-branch selection and relaxation extrapolation (best variant 6.24 pp). [TEST3: Test 3 outcome versus 25 °C lookup, the voltage-domain and equilibrium OCV models, and temperature-corrected lookup.] RM2P was most accurate between −15 and 15 °C. Far below the coldest registration temperature, all methods failed.

**Index Terms:** state of charge, open-circuit voltage, rest voltage, relaxation, temperature compensation, lithium-ion battery, battery station, unmanned aerial vehicle, low-cost sensing, preregistration.

## I. Introduction

Battery stations that recharge or swap packs for drones must decide, shortly after each landing, how much charge a returning pack holds. The estimate sets charging priority, determines whether the pack can fly the next mission, and flags packs whose capacity has faded [30], [31]. Coulomb counting during flight is the usual source, but with low-cost Hall-effect current sensors its error grows with sensor offset, gain error, and capacity uncertainty [28], [29]. The rest after landing offers an independent observation: the terminal voltage relaxes toward the OCV, which maps monotonically to SOC [2], [4], [9].

Three properties of this setting defeat reading an equilibrium OCV table. First, the rest available before the station must act lasts minutes, whereas full relaxation takes hours, longer in the cold [7], [12], [13]. Second, the ambient temperature varies from mission to mission, and both the OCV and the residual overpotential after a short rest depend on temperature. At −20 °C a 25 °C table underestimated SOC by 3 to 7 pp on the cells we studied, and by more than 50 pp on one cell at −25 °C (Fig. 2). Third, the voltage is read through an inexpensive analog front end.

Existing remedies fall into three groups:
- **Temperature-dependent OCV models** identify OCV(z, T) from slow tests at several temperatures [1], [7], [8], [10]. They describe the equilibrium voltage.
- **Relaxation models** fit the first minutes of a rest and extrapolate its asymptote [12]–[16].
- **Data-driven models** learn SOC, or a correction to a lookup, from voltage-shape features and temperature [17]–[21]. Their transfer to cells outside the training set is rarely tested under controlled conditions [22]–[26].

We propose rest-matched two-point registration (RM2P), which keeps estimation entirely per cell type. A one-time registration at 25 °C and at one low temperature records rests of the same length r as in the field. Each registration yields a monotone table from rest-end voltage to SOC. In the field, the rest-end voltage is read in both tables, and the two SOC values are interpolated by ambient temperature, without extrapolation above 25 °C. The temperature-indexed lookup structure is not new: it is the two-temperature special case of the temperature-dependent OCV–SOC tables used in the references above. What differs is that the tables are built from field-length, non-equilibrium rests rather than equilibrium OCV tests, and that only two registrations are used.

Our contributions are:
1. **Evidence that rest-matched, non-equilibrium registration outperforms equilibrium-OCV modeling for short rests.** On Test 2 cells, equilibrium OCV(z, T) models built with Plett's OCV-test procedure were 1.0 to 7.0 pp less accurate than RM2P, even with hysteresis-branch selection and two-RC relaxation extrapolation (post hoc). [TEST3: preregistered comparison with C/20 equilibrium OCV.]
2. **RM2P, a training-free estimator with a minimal registration budget:** two registration tests per cell type, an asymmetric extrapolation rule fixed on development data, about 1 ms per estimate, and graceful degradation under temperature-sensor bias.
3. **A preregistered evaluation on 23 unseen cells from three laboratories.** RM2P beat 25 °C lookup in Test 2 and [TEST3]. A learned residual correction, our initial approach, had a cell-dependent gain over 25 °C lookup: none on the 13 cells of Test 1, and 2.2 pp on the six cells of Test 2. Its development gain came from the low-temperature depression of the development cells, whose magnitude did not carry over to new cells.
4. **Analysis of why cross-cell validation overstated transfer.** The development cells happened to share similar low-temperature behavior, so leave-one-dataset-out validation could not reveal cell-to-cell variation.

## II. Related Work

**Temperature-dependent OCV.** The OCV–SOC curve underlies most SOC estimators [2], [4], [9]. The OCV shifts with temperature through the entropy change of intercalation [11]. A common model is OCV(z, T) = OCV0(z) + T·OCVrel(z), identified from slow-rate tests at several temperatures, as in Plett's enhanced self-correcting (ESC) model [1]–[3]. Hysteresis adds a path-dependent term, which is important for LFP [5], [6]. Per-cell OCV–SOC–temperature tables with interpolation across temperature have been used inside model-based estimators [8], [10], and temperature corrections of the OCV have been characterized together with aging [7]. These works describe the equilibrium voltage. RM2P describes the voltage after a rest of the field length, uses two registrations, and is used directly, without a filter. We compare it against equilibrium OCV(z, T) models built with Plett's procedure (post hoc on Test 2; preregistered in Test 3) and against a voltage-domain model of the same form built from the rest-length tables.

**Rest and relaxation-based OCV estimation.** Equivalent-circuit relaxation fits extrapolate the asymptotic voltage from the first minutes of a rest. Other works learn mappings from short rests to OCV, usually validated on one cell type at a few temperatures [12]–[16]. We include two-RC extrapolation (B3) as a baseline and as a front end to the equilibrium models.

**Data-driven SOC estimation and generalization.** Gradient-boosted trees and neural networks estimate SOC from voltage, current, and temperature [17]–[21]. Transfer learning and domain adaptation target cross-cell and cross-temperature use, usually with target-domain data [22], [23]. Random or within-cell splits overestimate performance [24]–[26]. We show that even leave-one-dataset-out validation overstated transfer when the held-out cells were similar in the property that mattered. Cell-to-cell and type-to-type parameter variation is well documented [27].

**Low-cost sensing.** Robustness to sensor offset, noise, and quantization has mostly been studied with assumed error injections [29]. We inject the gain, offset, noise, and quantization of a divider plus 12-bit ADC into every test voltage.

**Drone battery stations.** Automatic battery replacement and recharging stations enable persistent multi-vehicle UAV missions. They require the state of each returning pack to schedule charging and dispatch [30], [31]. SOC estimation for UAV packs has mostly used filter-based estimators during flight [33], and recent eVTOL datasets document mission-profile loads [32]. The post-landing rest, available at every station visit, has received little attention as a standalone observation.

**Preregistration.** Committing hypotheses and analysis plans before seeing test data guards against overfitting evaluation choices [34], [35]. To our knowledge, preregistered evaluations have not been reported in battery-state estimation.

## III. Problem Setup

### A. Task
A sample is one rest that follows a discharge. The input is the first r seconds of rest voltage at 1 Hz (r = 300 s primary; 60 and 600 s secondary) and the ambient temperature T. The output is SOC. Each test cell has registration rests with known SOC at 25 °C and, for two-temperature methods, at one low temperature T_low. Registration samples are never scored.

### B. Sample definition and reference SOC
- A rest is a period of at least 300 s with |I| < I_rest = C_nom/150. It must be preceded by a discharge (mean current over the last 60 s below −I_rest) and by at least 300 s of recording.
- Reference SOC is 1 + Q(t)/Q25. Q(t) is the signed charge since the most recent full-charge anchor, and Q25 is the cell's maximum discharged capacity at 25 °C.
- Samples with SOC outside (−0.02, 1.02) are dropped.

### C. Measurement-error model and temperature input
Every test voltage passes through a simulated low-cost chain with three error seeds:
- per-sample gain error N(0, 0.2 %);
- offset N(0, 5 mV);
- white noise N(0, 2 mV);
- a 6.2 mV quantization step (12-bit ADC behind a 100 kΩ/15 kΩ divider at 3.3 V).

The temperature input is the chamber's nominal temperature plus N(0, 2 °C) noise, emulating a station ambient sensor.

## IV. Proposed Method: RM2P

**Registration.** For a cell type (ideally each pack), run two tests that produce rests of at least r seconds at known SOC across the SOC range: one at 25 °C and one at T_low. Pulse, GITT-type, or dynamic-profile tests all qualify. From each test, form the rest-end voltage ṽ, the mean of the last 15 s of the first r seconds, and fit an isotonic (monotone non-decreasing) regression g_T(ṽ) → SOC. The 15 s mean suppresses quantization and noise.

**Estimation.** For a field rest with end voltage ṽ at ambient temperature T:

s25 = g_25(ṽ), s_low = g_Tlow(ṽ), w = max(0, (T − 25)/(T_low − 25)),

SOC = clip(s25 + w (s_low − s25), 0, 1).

Between T_low and 25 °C this is linear interpolation. Below T_low it extrapolates linearly, and above 25 °C it uses the 25 °C table.

**Design rationale.**
- *Rest-matched tables.* After 300 s, especially in the cold, the voltage remains well below equilibrium (Fig. 4), and after a discharge it sits on the lower hysteresis branch. A table built from rests of the same length after similar discharges absorbs both effects; an equilibrium OCV table does not.
- *SOC-domain interpolation.* RM2P interpolates two SOC readings rather than two voltage curves. In development this choice made no measurable difference compared with interpolating the inverted tables in the voltage domain (Section VI-B). Its advantage appeared only on the Test 2 cells, and only post hoc, so we treat it as a convenience, not a contribution.
- *No warm extrapolation.* Above room temperature, the rest-voltage depression changes little. Extrapolating the 0–25 °C trend upward raised the 40 °C error in development from 1.08 to 1.64 pp.
- *Cost.* Two isotonic lookups and one interpolation; median latency 0.90 ms (P95 1.29 ms) per estimate on a laptop CPU, including table fitting.

The variant was fixed on development data among four candidates (interpolation linear in T or in 1/T, weight clipped to [0, 1], no warm extrapolation). It was committed before any test (commit 7d4bbc5).

## V. Compared Methods

- **B0, global OCV table:** isotonic regression of SOC on end voltage, pooled over training cells; no per-cell registration.
- **B1, 25 °C registration lookup:** g_25(ṽ), the conventional single-temperature approach.
- **B2, temperature-corrected lookup:** B1 + β·[1, ΔT, ΔT², ΔT·B1], with ΔT = T − 25 °C and β fitted by least squares on training cells.
- **B3, two-RC relaxation extrapolation:** the asymptote of a two-RC fit to the rest replaces ṽ in B1.
- **B4, gradient boosting:** XGBoost [17] predicting SOC from rest-shape features and temperature.
- **ESC2, voltage-domain temperature-dependent OCV from rest-length tables:**
  - V_T(z) comes from isotonic regression of ṽ on SOC at 25 °C and at T_low.
  - V(z, T) = V_25(z) + a (V_Tlow(z) − V_25(z)), with a = (T − 25)/(T_low − 25), linear on both sides.
  - SOC solves V(z, T) = ṽ.
  - This is the ESC OCV form [1] identified from two temperatures. Two decomposition variants are also reported: ESC2_cold uses RM2P's warm rule, and ESC2_inv inverts RM2P's own tables, so it differs from RM2P only in the interpolation domain.
- **Equilibrium-OCV models (ESC_eq):**
  - OCV(z, T) is built from slow-rate OCV tests. For Plett data, we follow Plett's processOCV procedure (C/30 discharge and charge, averaged) [2], [45]. For Test 3, we use C/20 discharge pseudo-OCV.
  - Variants: two temperatures (25 °C, T_low) or all available temperatures (OCV0 + T·OCVrel); the averaged curve or the discharge branch only; ṽ or the B3 asymptote as input; with or without RM2P's warm rule.
- **S, learned residual correction** (our initial approach):
  - XGBoost (300 trees, depth 3, learning rate 0.05, subsample 0.8, absolute-error loss, monotone in end voltage and relaxation increments) predicts SOC − B1.
  - Inputs are the end voltage, five relaxation increments (end minus 5-point means at 4, 9, 29 and 59 s and at r/2), a late-relaxation ratio, the B1 SOC, and ambient temperature.
  - Training uses overpotential-amplitude augmentation (a log-uniform factor in [0.1, 4] about a two-RC asymptote, six copies), dataset × SOC-bin weights, and a bag of five.
  - S was selected by ablation (Section VI-A). A fuller variant P is secondary.

## VI. Experiments

### A. Development and the learned baseline

**Data.** Five public datasets: LG HG2 (NMC) [36], [37], Panasonic 18650PF (NCA) [18], [38], CALCE INR20R (NMC, two cells) [8], [9], Samsung 30T (NMC) [39], and Turnigy Graphene (LiPo) [40].
- **Temperatures:** −20, −10, 0, 25 and 40 °C. Panasonic has no 40 °C data, and CALCE has only 0 and 25 °C.
- **Registration:** each dataset's first 25 °C HPPC test (CALCE: incremental OCV).
- **Folds:** leave-one-dataset-out (LODO), plus temperature-extrapolation folds (train −10 to 25 °C, test −20 and 40 °C). The development metric averages the two.
- **CIs:** bootstrap over samples within datasets. With one cell per dataset (two for CALCE), they do not reflect cell-to-cell variation.

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

**Ablation** (increase in error when a component is removed from P):
- residual on B1: +1.42;
- balance weights: +0.28;
- temperature input: +0.20;
- amplitude augmentation: +0.13.

The other components contributed nothing, and removing them defined S.

### B. RM2P in development

**Setup.** T_low = 0 °C, using each dataset's 0 °C HPPC test; CALCE has none and is excluded. Scoring covers −20, −10 and 40 °C (462 LODO rests).

**Results (Table II).**
- RM2P and S were comparable: 1.91 vs 1.93 pp, not significantly different.
- Both beat B1 (3.39 pp) and B2 (1.99 pp).
- RM2P beat the voltage-domain model ESC2 by 0.65 pp [0.47, 0.86]. With the same warm rule (ESC2_cold) the margin was 0.45 pp [0.28, 0.65].
- With the same tables and rule (ESC2_inv), there was no difference (1.88 pp; −0.03 [−0.07, 0.02]).
- In development, then, the advantage over ESC2 comes from the warm rule and the regression direction, not from the interpolation domain.

**TABLE II. Development, two-temperature methods (MAE / bias, pp, r = 300 s, 462 rests).**

| Temp. | n | B1 | B2 | S | ESC2 | ESC2_cold | ESC2_inv | RM2P |
|---|---|---|---|---|---|---|---|---|
| All | 462 | 3.39 / −2.99 | 1.99 / +0.17 | 1.93 / +0.58 | 2.56 / −2.03 | 2.36 / −1.61 | 1.88 / −1.26 | 1.91 / −1.18 |
| −20 °C | 120 | 6.57 | 3.32 | 2.54 | 4.61 | 4.61 | — | 3.20 |
| −10 °C | 163 | 3.60 | 1.76 | 2.07 | 1.99 | 1.99 | — | 1.86 |
| 40 °C | 179 | 1.08 | 1.29 | 1.39 | 1.70 | 1.19 | — | 1.08 |

### C. Test 1 (preregistered): does the learned correction transfer?

Before RM2P existed, we froze S and tested it on LG E66 [41], [42] and Molicel P42A [43], [44].
- **Cells:** E66 is one 65 Ah pouch cell tested at −20, −10, 0, 10 and 40 °C. P42A is 12 cells tested at 5 and 40 °C.
- **Preregistration:** protocol 14c47ae, conversion d77e5e5 and runner 82f5722 were all committed before the single run.
- **Registration:** E66's 25 °C GITT test; each P42A cell's 25 °C HCGT test.
- **Hypotheses:** H1, S < B1; H2, S < B2.

**TABLE III. Test 1 (MAE, pp, r = 300 s; CI over cells for P42A, over samples for E66).**

| Method | E66 (794 rests) | P42A (571 rests, 12 cells) | Mean |
|---|---|---|---|
| S | 1.775 [1.68, 1.86] | 1.092 [1.03, 1.16] | 1.434 |
| B1 | 1.738 [1.63, 1.85] | 1.082 [1.00, 1.18] | 1.410 |
| B2 | 1.793 [1.69, 1.89] | 1.143 [1.08, 1.21] | 1.468 |
| P | 1.719 [1.63, 1.81] | 1.161 [1.11, 1.22] | 1.440 |

**Outcome.** Neither H1 nor H2 was supported. B1 − S was −0.04 [−0.15, 0.08] on E66 and −0.01 [−0.14, 0.11] on P42A.

**Mechanism (Fig. 2).**
- On development cells, B1's bias grew with cold: −6.57 pp at −20 °C, −3.58 at −10 °C, −1.99 at 0 °C, and −0.05 at 40 °C.
- The three development datasets with more than five rests at −20 °C clustered between −6.1 and −6.9 pp.
- E66's depression was half as large (−3.31 pp), so S, which had learned the development magnitude, overcorrected (+3.23 pp).
- A same-temperature oracle table cut per-dataset B1 error from 2.3–4.1 to 1.0–1.4 pp. Rebuilding the table from all 25 °C rests left it unchanged, so registration quality was not the cause.
- Three other candidate explanations did not account for the gap: the extrapolation folds, the preceding current, and the test type.

The depression is a per-cell property, which motivated RM2P. Applied post hoc to E66 with its 0 °C GITT registration (0 °C rests excluded), RM2P reduced MAE to 1.34 pp, against 1.81 for S and 1.86 for B1, and reduced the −20 °C bias to −0.16 pp.

### D. Test 2 (preregistered): RM2P on unseen cells

**Data.** Plett ESC toolbox dynamic tests [2], [45] (CC BY-NC-SA 4.0).
- **Cells:** six cells (A123, ATL, E1, E2, P14, SAM), 2.1 to 19.4 Ah, including two with LFP-like flat OCV curves.
- **Temperatures:** eight, from −25 to 45 °C.
- **Rests:** about 12 min each, following dynamic-profile segments that peak at 0.5 to 4.9 C.

**Design.** Protocol, conversion and runner were committed as cd29142 before the single run.
- **Registration:** each cell's 25 °C and −5 °C tests.
- **Scoring:** 658 rests at the other six temperatures.
- **Hypotheses:** H3, RM2P < S; H4, RM2P < B1.
- **Inference:** paired cell-level bootstrap (B = 2000). A hypothesis is supported if the lower bound of the paired difference exceeds 0.

**TABLE IV. Test 2 (MAE, pp, r = 300 s).**

| Method | All [95 % CI] | Method − RM2P [95 % CI] | −25 °C | −15 °C | 5 °C | 15 °C | 35 °C | 45 °C |
|---|---|---|---|---|---|---|---|---|
| RM2P | **5.23** [3.46, 7.41] | — | 15.34 | **6.64** | **1.94** | **1.88** | 1.84 | 2.14 |
| S | 5.80 [3.20, 8.94] | +0.57 [−0.35, 1.60] | 13.84 | 9.36 | 3.58 | 2.52 | 1.89 | 2.10 |
| B1 | 7.97 [4.63, 11.60] | +2.74 [1.08, 4.36] | 20.39 | 14.29 | 4.27 | 2.53 | 1.84 | 2.14 |
| B2 | 6.27 [3.53, 9.53] | +1.04 [−0.02, 2.25] | 14.86 | 10.22 | 3.84 | 2.58 | 1.90 | 2.63 |
| P | 5.80 [3.20, 9.09] | +0.57 [−0.30, 1.62] | 14.04 | 9.08 | 3.37 | 2.31 | 2.17 | 2.35 |

**Outcome.** H4 was supported; H3 was not.

**Cell-level robustness (post hoc).**
- RM2P beat B1 in 5 of 6 cells (SAM: 2.90 vs 2.68 pp). The exact sign test gives p = 0.22, and the sign-flip permutation test over cells p = 0.06.
- With six cells, the percentile cell bootstrap is anti-conservative, so the preregistered H4 result should be read together with these tests.
- RM2P beat S in 3 of 6 cells (permutation p = 0.41).

**By temperature.**
- RM2P was the most accurate method from −15 to 15 °C.
- At −25 °C, 20 °C below T_low, linear extrapolation under-corrected and every method failed.
- Errors were higher than in Test 1 because of the −25 °C condition and the flat-OCV cells. The ATL cell's B1 bias was −56 pp at −25 °C (Fig. 2c).

**Post hoc comparison with conventional OCV models (Table V).** On the same samples, equilibrium-OCV models built from Plett's OCV tests were much less accurate than RM2P.
- The two-temperature averaged-curve model reached 12.22 pp, and the full eight-temperature OCV0 + T·OCVrel model 12.25 pp. The full model knows the equilibrium OCV at every scored temperature.
- Their bias was negative at every temperature, including 35 and 45 °C (−5 to −6 pp). The rest voltage after a discharge stays below the averaged OCV curve, through residual overpotential and hysteresis.
- Giving the equilibrium model RM2P's advantages narrowed the gap but did not close it. With the discharge branch only, the B3 asymptote and RM2P's warm rule, it reached 6.24 pp; RM2P was better by 1.01 pp and won in 5 of 6 cells.
- The voltage-domain models built from the rest-length tables also trailed RM2P: ESC2 6.04, ESC2_cold 5.85, ESC2_inv 6.35 pp.

**TABLE V. Post hoc, Test 2 samples: OCV-model baselines (MAE, pp, r = 300 s).**

| Method | All | −25 | −15 | 5 | 15 | 35 | 45 °C | Cells where RM2P better |
|---|---|---|---|---|---|---|---|---|
| RM2P | 5.23 | 15.34 | 6.64 | 1.94 | 1.88 | 1.84 | 2.14 | — |
| ESC_eq, 2 temps, averaged curve | 12.22 | 23.72 | 18.53 | 8.98 | 7.41 | 5.83 | 6.56 | 5/6 |
| ESC_eq, 8 temps, averaged curve | 12.25 | 24.21 | 18.98 | 9.17 | 7.40 | 5.44 | 5.89 | 5/6 |
| ESC_eq, 2 temps, discharge branch | 9.61 | 19.22 | 10.43 | 3.11 | 2.90 | 9.71 | 11.37 | 5/6 |
| … + B3 asymptote + warm rule | 6.24 | 16.13 | 7.95 | 2.86 | 2.81 | 2.83 | 3.29 | 5/6 |
| ESC2 (rest-length tables) | 6.04 | 15.30 | 6.79 | 3.07 | 2.43 | 2.59 | 4.68 | — |
| ESC2_inv (RM2P tables, voltage domain) | 6.35 | — | — | — | — | — | — | — |

### E. Test 3 (preregistered): RM2P vs conventional methods [TEST3]

**Data.** McMaster Tesla Model 3 2170 (Panasonic NCA, three cells; CC BY 4.0) [46] and SB LiMotive (one cell; CC BY-SA 4.0) [47], with HPPC tests at −20, −10, 0, 10, 25 and 40 °C.

**Design.**
- **Registration:** 25 °C and 0 °C HPPC.
- **Scoring:** all rests at −20, −10, 10 and 40 °C.
- **Primary hypotheses:** H5, RM2P < B1; H6, RM2P < ESC2; H7, RM2P < B2; H8, RM2P < ESC_eq (C/20, two temperatures). Inference is a paired bootstrap over (cell, temperature) clusters with Holm correction.
- **Amendment (committed before any test-data run, 7eb6e9e):** added H8, the ESC decomposition variants, prespecified subsets (below T_low, interpolation, above 25 °C), per-cell-type reporting with sign consistency, and type-level registration (leave-one-cell-out among the Tesla cells).
- **Scope:** inference is conditional on these two cell types. Tesla rests were logged every 60 s in the raw data, so B3 and S are compared only on the 1 s-logged SB rests.

[TEST3 table and outcomes]

### F. Sensitivity analyses (post hoc)

- **Measurement chain.** Removing the simulated front-end errors improved RM2P by 0.12 pp in development (1.79 vs 1.91) and by 0.36 pp on Test 2 (4.87 vs 5.23). The low-cost chain costs little relative to the temperature effects.
- **Temperature-sensor bias.** A pack is warmer than ambient after flight. With a +10 °C bias added to the temperature input on Test 2, RM2P rose from 5.23 to 5.81 pp, B2 from 6.27 to 7.17, and S from 5.80 to 6.03. With −5 °C, RM2P was 5.26.
- **Load history.** In development, the registration tables come from HPPC tests. Scored rests that followed drive cycles or constant-current discharges were harder for every method: RM2P 3.89 and 3.98 pp, against 1.36 for HPPC rests. RM2P still improved on B1 by 1.4 to 1.5 pp in each group.
- **Rest length.** On Test 2, RM2P's error fell with rest length: 6.26, 5.23 and 4.65 pp at r = 60, 300 and 600 s.
- **More registration temperatures.** Registering every available temperature except the test temperature reduced Test 2 MAE to 3.19 pp, including 7.41 at −25 °C. Where cold operation is expected, the natural extension is a third registration near the coldest operating temperature.
- **Latency.** RM2P 0.90 ms median; S 2.3 ms; P 4.4 ms (worst case for S: 42 ms).

## VII. Discussion

**Why rest-matched tables beat equilibrium OCV models.** The quantity a station sees is a voltage after a few minutes of rest following a discharge. That voltage differs from the equilibrium OCV through residual overpotential, which grows in the cold, and through hysteresis. The equilibrium models in Table V carried a negative bias at every temperature. Relaxation extrapolation and branch selection removed only part of it. Registering with the same kind of rest as in the field captures these effects without modeling them.

**Why per-cell registration beats cross-cell learning here.** The low-temperature depression varies between cells by a factor of two or more (Fig. 2), consistent with documented cell-to-cell and type-to-type parameter variation [27]. A learned model reproduces the average of its training cells, which helped on the Test 2 cells and hurt on E66. A single low-temperature registration measures each cell's own value. Leave-one-dataset-out validation did not expose this because the development cells happened to be similar. Validation must vary the property that drives generalization.

**Station practice.** RM2P fits station commissioning. Register each new pack type at 25 °C and at the coldest planned operating temperature, using the same rest length and a discharge similar to operation. The station then needs only an ambient sensor and two table lookups per landing. Whether one registration per pack type suffices, or each pack needs its own, is examined in Test 3 [TEST3].

## VIII. Limitations

- **Loads.** No real drone pack or flight-load data were available. Test rests follow constant-current, pulse or dynamic-profile discharges; Plett's dynamic profiles are not flight profiles.
- **Far extrapolation.** RM2P extrapolates poorly far below T_low (−25 °C in Test 2).
- **Small cell counts.** Development has one cell per dataset (two for CALCE), and its CIs ignore cell-to-cell variation. E66 comes from the same laboratory as some development data. Test 2 has six cells, and its percentile cell bootstrap is anti-conservative (Section VI-D). Test 3 covers two cell types.
- **Selection on development data.** S was selected by ablation, and RM2P's variant was chosen on development data. Both were frozen before their tests.
- **Post hoc analyses.** The E66 analysis, the OCV-model comparisons on Test 2, and the sensitivity analyses are post hoc.
- **Reference SOC.** It uses the 25 °C capacity. The deliverable capacity in the cold is smaller, which does not affect the comparison between methods.

## IX. Conclusion

RM2P estimates SOC from a short post-landing rest using two per-cell registrations and no training. Its tables are built from field-length rests, not equilibrium OCV tests. In preregistered tests on unseen cells it improved on conventional 25 °C OCV lookup, [TEST3], and was statistically indistinguishable from a learned correction model whose benefit varied between cell sets. In post hoc comparisons, it outperformed equilibrium OCV(z, T) models even when those were given hysteresis-branch selection and relaxation extrapolation. The low-temperature rest-voltage depression is cell-specific. Measuring it per cell, with rests like those seen in the field, is an effective and inexpensive way to handle it.

## Data and Code Availability
- **Datasets:** as cited, under their licenses: CC BY 4.0 for the Mendeley, Borealis, Tesla and OSF datasets unless noted; CC BY-SA 4.0 for SB LiMotive; CC BY-NC-SA 4.0 for Plett ESC. No data are redistributed.
- **Code and protocols:** code, protocols and per-sample predictions are in the project repository. Protocol commits: Test 1 14c47ae (protocol), d77e5e5 (conversion), 82f5722 (runner); Test 2 cd29142; Test 3 f7fe7a6 (draft), 7eb6e9e (amendment), [TEST3] (final). [Public repository URL to be added before submission.]
- **Software:** Python 3.11.9, NumPy 2.4.6, SciPy 1.16.3, scikit-learn 1.9.0, XGBoost 3.2.0, pandas 2.3.3.

## Figures
- Fig. 1: Study design (`paper/figs/fig_design.png`).
- Fig. 2: Bias of 25 °C lookup vs temperature per cell; (a) development, (b) Test 1, (c) Test 2 (`fig_bias_vs_temp.png`). Points with fewer than five rests are omitted.
- Fig. 3: MAE vs temperature for B1, B2, S, ESC2 and RM2P; (a) E66, post hoc; (b) Test 2, with ESC2 post hoc (`fig_mae_vs_temp.png`).
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
