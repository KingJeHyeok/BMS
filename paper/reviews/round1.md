# Review, round 1: "Rest-Matched Two-Point Registration for Fast State-of-Charge Estimation of Returning Drone Batteries with Low-Cost Sensing"

Reviewer for IEEE Access. Manuscript `paper/manuscript.md` (draft v1, 2026-11-18), figures in `paper/figs/`, evidence in the repository at HEAD `0a0cf32`. Section VI-E (Test 3) is pending and marked [TEST3]. Its missing numbers are not counted against the paper. Its preregistered design (`analysis/final4_test_protocol.md`, `analysis/final4_test.py`) is reviewed under R4.

## 1. Decision

**Decision: Major revision**

## 2. Summary

The paper estimates the SOC of a battery from the rest voltage at the end of a short (300 s) post-discharge rest, read through a simulated low-cost voltage chain, at varying ambient temperature. The proposed RM2P builds two per-cell isotonic tables from rest-end voltage to SOC: one at 25 °C and one at a low temperature, both using rests of the field length. It interpolates the two SOC readings linearly in temperature and does not extrapolate above 25 °C. A cross-cell learned residual corrector (S), developed first, gave no gain over 25 °C lookup in preregistered Test 1 (13 cells). The authors trace this to a cell-specific low-temperature rest-voltage depression. In preregistered Test 2 (six Plett ESC cells), RM2P beat 25 °C lookup (7.97 → 5.23 pp, paired CI [1.08, 4.36]) but not S (H3 unsupported). A third preregistered test against a voltage-domain two-temperature model (ESC2), B1 and B2 on four McMaster cells is pending.

## 3. Strengths

- The preregistration discipline is real and checkable. Protocol, conversion and runner commits precede each run (Test 1: 14c47ae/d77e5e5/82f5722 before results 4828587; Test 2: cd29142 at 15:59:33, run at 16:00, results 7cd97d6 at 16:01). The runners refuse a second run (`RUN_DONE`) and a dirty tree.
- Unsupported hypotheses (H1, H2, H3) are reported plainly. Post hoc analyses (E66 two-point, ESC2 on Test 2, dense registration) are labeled as such.
- The Test 1 failure analysis (`analysis/b1_gap.md`) is a genuinely useful negative result. It shows that leave-one-dataset-out CV hid a cell-specific property because the development cells happened to agree on it (−6.1 to −6.9 pp at −20 °C).
- The method is simple, training-free and cheap. That suits embedded or station use, and anyone can reimplement it.
- Every number I checked is traceable to a file in `analysis/`, and nearly all match (Section 6).
- The references are real. All ten I checked resolve with correct metadata.

## 4. Required changes

**R1. Novelty is overstated relative to multi-temperature OCV/SOC lookup practice.**
- *Problem.* The paper's own refs.md describes Wei & Ling [10] as using "an OCV–SOC lookup table for each ambient temperature … and interpolat[ing] for untested temperatures". Xing et al. [8] build an OCV–SOC–temperature table. A 2-D table SOC = f(V, T) with bilinear interpolation is standard BMS firmware practice. With two temperature nodes, that table is RM2P's "SOC-domain interpolation". Contribution 1 lists SOC-domain interpolation as a design novelty, and Section II does not position RM2P against [8], [10] or 2-D LUT practice.
- *Why it matters.* IEEE Access requires a clear statement of what is new. As written, a reader familiar with BMS practice will see RM2P as a two-node 2-D LUT.
- *Resolution.* State explicitly that temperature-indexed lookup tables with interpolation are prior art. Reframe the contribution as follows:
  - (a) Tables built from rests of the field length (non-equilibrium) rather than equilibrium OCV.
  - (b) The minimum number of temperature nodes, and the asymmetric extrapolation rule.
  - (c) The preregistered evidence, including the cross-cell transfer finding.
- Claim (a) needs the evidence requested in R2. The domain claim needs the decomposition in R3.

**R2. The genuinely conventional baseline is missing: an equilibrium temperature-dependent OCV model.**
- *Problem.* "Rest-matched" is the core design claim: "an equilibrium OCV table cannot" absorb the overpotential (Section IV, Contribution 1). No method in the paper uses an equilibrium OCV.
  - B1, B2, ESC2 and RM2P all use rest-end-voltage tables.
  - B3 builds its table from 2RC asymptotes of the same rests.
  - ESC2 is called "the ESC OCV form", but it is built from the rest-matched tables, not from slow OCV tests. Plett's ESC model identifies OCV0(z) and OCVrel(z) from slow-rate OCV tests at many temperatures [1, 2].
- *Why it matters.* Without this baseline, the paper does not show that rest matching beats what the literature does: temperature-dependent equilibrium OCV, optionally combined with relaxation extrapolation. Novelty and significance hinge on this comparison.
- *Resolution.* Add a post hoc comparison, labeled as such, on Test 2. The Plett ESCtoolbox ships the slow OCV tests (and identified OCV0/OCVrel models) for all six cells at all eight temperatures. Report three variants:
  - (i) The full multi-temperature ESC OCV(z, T), inverted at ṽ.
  - (ii) The same model with ṽ replaced by the B3 asymptote.
  - (iii) A two-temperature (25 °C, −5 °C) equilibrium version.
- Do the same on development data wherever slow or incremental OCV tests exist. This cannot replace any preregistered outcome, but it is needed to support Contribution 1.

**R3. The RM2P vs ESC2 comparison is confounded, and the manuscript omits the control the authors already computed.**
- *Problem.* `analysis/esc_compare.py` defines ESC2 with two-sided linear extrapolation. It also defines ESC2_cold, with the same warm-side rule as RM2P, "to isolate the domain difference". Only ESC2 is reported.
  - (i) **Warm extrapolation.** Dev: ESC2 2.56 vs ESC2_cold 2.36 (RM2P 1.91). Test 2: 6.04 vs 5.85 (RM2P 5.23). Roughly a third of the dev gap comes from the extrapolation rule, not from the domain of interpolation.
  - (ii) **Regression direction.** ESC2 fits voltage on SOC and inverts. RM2P fits SOC on voltage. At T ≥ 25 °C, ESC2_cold should therefore reduce to B1 but does not:
    - Plett 35 °C: 2.71 vs 1.84.
    - Plett 45 °C: 3.38 vs 2.14.
    - Dev 40 °C: 1.19 vs 1.08.
  - The gap at the 25 °C node alone is about 0.9 pp on Test 2. That is comparable to the whole RM2P–ESC2 difference (0.81 pp).
  - On the cold side, where the flat-OCV mechanism should act, ESC2 and RM2P are nearly equal. Test 2: −25 °C 15.30 vs 15.34; −15 °C 6.79 vs 6.64. E66: 1.35 vs 1.34 overall.
- *Why it matters.* The Discussion paragraph "Why SOC-domain interpolation beats voltage-domain models", Contribution 1 and the abstract attribute the gap to the interpolation domain and to flat OCV segments. The evidence does not isolate that mechanism.
- *Resolution.*
  - Report ESC2_cold alongside ESC2 everywhere ESC2 appears: Table II, the Test 2 text, Fig. 3 and the abstract.
  - Add an ESC2 variant whose V_T(z) is the inverse of the same g_T tables, so that it equals g_25 and g_low exactly at the two nodes, with the same warm rule. Report the decomposition: extrapolation rule / regression direction / interpolation domain.
  - Report it per cell, flat-OCV cells (A123, ATL) vs the others, to test the flat-segment mechanism directly.
  - Rewrite the Discussion so it claims only what this decomposition supports.

**R4. Test 3 preregistration: sound in structure, but fix these points before the single run.**
- *What is sound:*
  - The method is frozen (TwoPointCold, 7d4bbc5).
  - The comparators are fixed, and all are reported regardless of outcome.
  - The bootstrap is paired, with the same draws for every method.
  - Holm correction covers three primary hypotheses, with a directional success criterion.
  - There is a single-run guard, a clean-tree check, and a dev dry run.
  - The data are unseen by development and Tests 1–2.
  - The S fairness caveat is stated.
  - My check of the Holm implementation in `final4_test.py` found it correct.
- *Problems:*
  - (a) **The preregistration is not complete yet.** `analysis/prepare_final4.py` is untracked. `final4_data_notes.md` does not exist. `C:/BMS/data/holdout_final4/` contains only `raw/`, so conversion has not been run. Protocol §6.2 requires the protocol, converter and runner in one commit. The manuscript cites "[TEST3]" for the hash.
    - Make that commit before the run and cite it.
    - Any change from the draft in f7fe7a6 must be listed as a dated amendment made before any model run.
  - (b) **H6's comparator inherits R3's confounds, and it was chosen after the ESC2/ESC2_cold results on dev, E66 and Plett were seen.** ESC2 extrapolates above 25 °C, and 4 of the 16 (cell, temperature) clusters are at 40 °C, where dev and Plett show ESC2 losing mainly through that rule.
    - Before the run, amend H6 to use the node-consistent ESC2 with the same warm rule described in R3.
    - Alternatively, keep H6 but preregister ESC2_cold and the node-consistent variant as secondary comparisons, plus an H6 sensitivity restricted to T < 25 °C.
    - Otherwise a "supported" H6 will not support the paper's domain claim.
  - (c) **Pre-specify the subsets.** At 40 °C, RM2P ≡ B1 by construction, so those clusters contribute exactly zero to H5. Pre-specify these secondary subsets: the 10 °C interpolation range; below T_low (−10 and −20 °C, the latter 20 °C below T_low, the regime where everything failed in Test 2); and 40 °C. State in the protocol that H5 is effectively decided on 12 clusters.
  - (d) **Unit of inference.** The design has 16 clusters from two cell types: three near-replicate Tesla cells and one SB cell. The pooled MAE is dominated by Tesla. Resampling (cell, temperature) clusters treats temperatures within a cell as independent.
    - State that inference is conditional on these cell types, not on new cell types.
    - Pre-specify per-cell-type results (Tesla mean, SB) and the sign consistency across cells.
  - (e) **Logging-resolution artifacts.** Tesla rests were logged at 60 s and interpolated to 1 Hz (prepare_final4 docstring). B3's 2RC fit (τ1 ∈ [1, 30] s) is therefore fitted to a linearly interpolated curve and is not meaningful on Tesla.
    - Pre-specify that B3, like S, is interpreted only where raw_n60 ≥ 30.
    - State in the protocol and paper that this subset (Table D) is the SB cell only: Tesla raw_n60 is 2.
  - (f) **Test types.** The protocol scores "all tests" at −20, −10, 10 and 40 °C, which can include drive-cycle and C/20 rests. The manuscript says "HPPC tests".
    - Specify which test types are scored.
    - Pre-specify a by-test-type breakdown: HPPC registration vs HPPC scoring is the most favorable case for any registration method, and drive-cycle rests probe load-history mismatch.
  - (g) **Per-type registration is not tested.** Section VII recommends registering "each new pack type", but every test registers the same cell it scores. Tesla has three cells of one type.
    - Preregister a secondary leave-one-cell-out registration: tables from one Tesla cell, scored on the other two.
    - This directly tests the deployment claim.
  - (h) **Licensing.** The SB data are CC BY-SA 4.0 (Borealis/DataCite), not CC BY. Record this in the protocol and the Data Availability section.

**R5. Several claims are not supported, or are contradicted, by the authors' own results.**
- *Problem:*
  - (i) "Cross-cell learned correction does not transfer" (abstract, Contribution 2, Discussion) is contradicted by Test 2. There S beat B1 by 2.17 pp (5.80 vs 7.97), and B2 also beat B1 (6.27). The correct statement is that the gain of a cross-cell correction is cell-dependent and unpredictable from LODO validation: zero on Test 1, large on Test 2.
  - (ii) "Matched the learned model" (abstract, conclusion) rests on a non-significant difference with CI [−0.35, 1.60]. That is not evidence of equivalence.
  - (iii) "RM2P was best overall" in development (Section VI-B): RM2P 1.91 vs S 1.93, S − RM2P +0.02 [−0.21, 0.26]. RM2P was not best at −20 °C (S 2.54) or at −10 °C (B2 1.76).
  - (iv) Contribution 4's "robustness to a simulated 12-bit divider front end" has no supporting experiment. All results include the chain, and no result compares clean vs corrupted input.
  - (v) "Runs in under 1 ms" and "0.5 ms (RM2P, B1)": `analysis/latency.py` measures S, P, B1 and B2 only. RM2P calls RegLookup twice, so its median is probably near 1 ms.
- *Why it matters.* IEEE Access requires that conclusions follow from the evidence.
- *Resolution:*
  - (i) Rewrite Contribution 2 and the Discussion as described above.
  - (ii) Report the CI, or run a post hoc equivalence test with a stated margin.
  - (iii) Change "best overall" to "comparable to S and B2".
  - (iv) Add a post hoc clean-vs-chain comparison on dev and Test 2 (labeled), or drop the claim.
  - (v) Measure RM2P's latency.

**R6. Number and presentation errors (must be fixed).**
- The abstract's "reduced development error from 3.40 to 2.11 pp" refers to P. The model tested in Test 1 (S) scored 2.08 (results.md; Table I). Contribution 2's "1.3 pp" is computed from S, so use 2.08.
- Section VI-C says "A same-temperature oracle table cut B1 from 3.0–4.1 … pp per dataset". `b1_gap.md`'s table gives 2.31 (Turnigy), 2.99 (Samsung), 3.15 (LG) and 4.08 (Panasonic), so the range is 2.3–4.1. The same applies to "rebuilding … changed nothing" (2.38–4.09).
- Table II's header promises MAE / bias, but bias is missing for B2 and for all per-temperature rows.
- Fig. 1 lacks Test 3. The Fig. 3 caption still says "TODO: add ESC2" although the figure includes it. Remove all TODO placeholders.

**R7. Practical relevance: the temperature input and load history are not examined.**
- *Problem.* RM2P's estimate is weighted by temperature, but the input is the chamber setpoint plus N(0, 2 °C). A returning drone pack is warmer than the ambient air after a high-rate flight, and a station sensor reads ambient. Test 1 already showed nominal "5 °C" P42A cells at 6–15 °C (final_results.md, Table F).
- Likewise, the "rest-matched" premise assumes field rests follow loads similar to the registration test. In Test 2, the preceding load also varies with temperature: final3_data_notes.md records 0.25–1C at −25 °C vs 1.5–4.9C at 25 °C and above. Flight loads are not represented at all.
- *Why it matters.* The title and abstract target drone stations. A temperature bias of 5–10 °C at T_low = 0 °C moves the interpolation weight by 0.2–0.4.
- *Resolution.* Add two post hoc analyses (labeled):
  - (i) RM2P/B2/S error vs temperature-input bias (e.g., −5, +5, +10 °C) and vs noise SD, on dev and Test 2. Then give guidance on which temperature to feed (ambient vs pack surface).
  - (ii) Load-history mismatch on dev: tables from HPPC, scored separately on HPPC rests and on drive-cycle rests at the same temperatures.
- Scope the title and abstract claims accordingly: no pack-level, flight-load or cell-imbalance data.

**R8. Reproducibility and data availability.**
- *Problem.* "TODO: public URL". No license statement per dataset.
- *Resolution.*
  - Provide a public repository URL in which the cited commit hashes resolve, together with per-sample predictions and conversion scripts.
  - List each dataset's license: Tesla CC BY 4.0; SB CC BY-SA 4.0; Plett ESC no license (state that only conversion code is distributed); and each development dataset.
  - State the Python and package versions.

**R9. Statistical reporting for small numbers of cells.**
- *Problem:*
  - The Test 2 CIs come from a percentile bootstrap over six cells, which under-covers at this size.
  - The development CIs (Table I/II) are sample-level within single-cell datasets and ignore between-cell variance. This is mentioned in results.md but not in the paper.
- *Resolution:*
  - Add the per-cell paired differences for Test 2. RM2P beat B1 in 5 of 6 cells; SAM is the exception at 2.90 vs 2.68.
  - Add an exact sign or permutation test across cells as a post hoc sensitivity analysis.
  - State in the Table I/II captions that the CIs do not reflect cell-to-cell variation.

## 5. Optional suggestions

1. **Measurement model.** The 6.2 mV step corresponds to a ~25 V full-scale divider (a 6S pack), yet it is applied to single-cell voltage. Gain and offset are drawn independently per sample, whereas real devices have a persistent offset. Registration voltages are left uncorrupted. Justify these choices, or add a variant with a fixed per-device offset: on flat OCV segments, a persistent 5 mV offset produces a bias, not noise.
2. **Fig. 4.** The −5 and 5 °C colors, and the 15 and 25 °C colors, are hard to tell apart. A marker for the equilibrium OCV at that SOC would support the claim that the voltage is "well below equilibrium".
3. **Operational metrics.** Report errors that matter to a station: the P95 and maximum error, and the fraction of estimates within ±5 pp. These are already computed in the results files.
4. **Section VI-A.** S is no longer the proposed method, so the S ablation could move to an appendix to keep the focus on RM2P.
5. **Recommendation.** The dense-registration bound (3.19 pp; 7.41 at −25 °C) suggests registering at the coldest operating temperature. Discuss the cost of registration (chamber time, number of rests) as part of the station-commissioning argument.
6. **Related work.** Consider citing recent relaxation-based SOC/SOH work, e.g., "Relax, Estimate, and Track: A simple battery state-of-charge and state-of-health estimation method" (2024, arXiv 2408.01127). Verify the bibliographic details first.
7. **Title.** No drone data were used, so consider a title nearer the evidence, e.g., "… for Battery Stations". "Fast" is also vague.
8. **Mechanism paragraph.** Note that E66 comes from the same laboratory as four development datasets. The Test 3 cells do too.

## 6. Verification log

**Numbers checked against repository files (all match unless noted).**

| Manuscript item | Source | Result |
|---|---|---|
| Table I, all 21 values (B0–B4, P, S; dev metric, LODO, extrapolation; P/S CIs) | results.md, Table 1 and the simplified row | match |
| 676 LODO + 299 extrapolation rests | results.md, data-scale table (244+148+19+126+139; 123+38+0+74+64) | match |
| Ablation +1.42, +0.28, +0.20, +0.13 | results.md, Table 2 | match |
| Table II, all values (n, B1, B2, S, ESC2, RM2P, biases) | two_point_dev.md and esc_compare.md (r = 300) | match |
| ESC2 − RM2P 0.65 [0.47, 0.86]; 40 °C 1.08 → 1.64 | esc_compare.md; two_point_dev.md (T2 at 40 °C) | match |
| Table III, all values; H1 differences | final_results.md, Tables A and B | match |
| B1 bias −6.57 / −3.58 / −1.99 / −0.05; E66 −3.31; S +3.23 | b1_gap.md | match |
| Oracle "3.0–4.1 → 1.0–1.4" | b1_gap.md table | **mismatch** (2.31–4.08); see R6 |
| E66 post hoc 1.34 / 1.81 / 1.86; −0.16 | two_point_e66.md (r = 300) | match |
| Table IV, all values and paired CIs; H3/H4 outcomes | final3_results.md | match |
| ESC2 6.04; RM2P better by 0.81 [0.55, 1.08] | esc_compare.md (Plett, r = 300) | match |
| ATL B1 bias −56 pp at −25 °C | recomputed from final3_out/B1_reg_lookup.npz: −56.01 (n = 10) | match |
| r-dependence 6.26 / 5.23 / 4.65 | final3_results.md, Table B | match |
| Dense registration 3.19; 7.41 at −25 °C | multi_reg.md | match |
| Latency: S 2.3, P 4.4, worst case 42 ms, B1 0.5 ms | paper_outline.md §6.6, latency.py | match; **RM2P not measured** (R5) |
| Abstract "3.40 to 2.11" for the model tested in Test 1 | results.md | **mismatch**: S = 2.08; 2.11 is P (R6) |
| 6.2 mV quantization | 3.3 V/4096 × 115/15 = 6.18 mV; eval/run.py `corrupt` | match |
| Test 2 data description (2.1–19.4 Ah; 0.5–4.9C; ~12 min rests; 658 rests) | final3_data_notes.md, final3_test_protocol.md | match |

**Preregistration (git log).**
- Test 1: 14c47ae → d77e5e5 → 82f5722, then the run at 82f5722 (final_results.md header), then results in 4828587. In order.
- Test 2: cd29142 (15:59:33), then the run at 16:00 on cd29142, then results in 7cd97d6 (16:01:27). In order.
- RM2P variant fixed in 7d4bbc5, before Test 2. It was motivated by analysis of Test 1 data, which the paper discloses.
- ESC2 (b33c5ab) was created after Test 2 and is correctly labeled post hoc.
- Test 3: draft protocol and runner in f7fe7a6. Converter untracked, conversion not run, no results. Not yet a complete preregistration (R4a).

**References checked (web or Crossref/DataCite).**
- [10] Wei & Ling, IEEE Access 10:37131–37148, 2022, doi 10.1109/ACCESS.2022.3163413. Correct; first author Ying Wei.
- [14] Meng et al., IEEE TEC 34(2):1115–1123, 2019. Correct.
- [15] Qian et al., IEEE Access 10:96643–96651, 2022, doi 10.1109/ACCESS.2022.3203178. Correct.
- [16] Ko & Chen, Appl. Energy 357, 2024. Correct (title, authors, volume).
- [26] Yan & Wiston, Batteries 12(9):322, 2026. Correct per Crossref (published 2026-08-24).
- [29] Hwang, Lee & Lee, IJCAS 22(5):1691–1706, 2024, doi 10.1007/s12555-023-0546-9. Correct.
- [31] Ure et al., IEEE/ASME TMECH 20(1):275–286, 2015. Correct.
- [33] Zhang, Zhou & Lan, Energies 12(20):3960, 2019. Correct.
- [43] Khan et al., Sci. Data 12:1506, 2025. Correct.
- [46] Kollmeyer et al., Tesla Model 3 2170 dataset, Borealis 2023, CC BY 4.0. Correct.
- [47] Kollmeyer & Skells, SB LiMotive, Borealis 2023. Correct; license is CC BY-SA 4.0 (R4h, R8).
- No fabricated or wrong references found.

**Code checks.**
- `final3_test.TwoPointCold` matches the formula in Section IV.
- `variants.RegLookupTemp` matches the B2 description.
- `final4_test.ESC2` matches esc_compare's ESC2: two-sided extrapolation, voltage fitted on SOC.
- `final4_test.holm` is correct.
- Registration rests are not passed through `corrupt()`; only scored rests are (Optional 1).

Pass: no
