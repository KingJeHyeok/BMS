# References and related-work notes (draft, 2026-11-18)

How this list was checked
- Every DOI below was resolved on 2026-11-18: journal and conference DOIs through the Crossref API, and dataset DOIs (Mendeley, Borealis, OSF) through the DataCite API. Title, authors, venue, volume, pages and year are copied from those records.
- Each entry was also found by web search. Dataset citation requests were read on the repository pages (Mendeley, Borealis, CALCE, PMC).
- Three items have no DOI because none exists: the two Plett books, verified by ISBN in publisher and library records, and the ESCtoolbox, verified by an HTTP 200 response from its URL. No entry is marked UNVERIFIED.
- Entries are grouped by topic. Renumber them in citation order when moving them into the manuscript.
- Status tags: **[V-DOI]** means the DOI was resolved and the metadata matched; **[V-noDOI]** means no DOI exists and the item was verified another way.

## (a) Reference list (IEEE style)

### A. OCV–SOC relationship, temperature dependence, hysteresis

[1] G. L. Plett, "Extended Kalman filtering for battery management systems of LiPB-based HEV battery packs: Part 2. Modeling and identification," *J. Power Sources*, vol. 134, no. 2, pp. 262–276, 2004, doi: 10.1016/j.jpowsour.2004.02.032. **[V-DOI]**
— Introduces the enhanced self-correcting (ESC) cell model: OCV plus low-pass filter states and a hysteresis state. This is the origin of the model family behind our second test data (Plett ESC).

[2] G. L. Plett, *Battery Management Systems, Volume I: Battery Modeling*. Norwood, MA, USA: Artech House, 2015, ISBN 978-1-63081-023-8. **[V-noDOI]** (book; ISBN 978-1-63081-023-8 for print and 978-1-63081-024-5 for the e-book, both confirmed in library records)
— Describes the ESC model and the multi-temperature OCV test. Each cell gets its own OCV(z,T) = OCV0(z) + T·OCVrel(z), fitted from OCV tests at many temperatures (the same form appears in the ESCtoolbox `OCVfromSOCtemp` code). This is the closest prior form of our two-point registration, and the book is the canonical citation for the ESCtoolbox data.

[3] G. L. Plett, *Battery Management Systems, Volume II: Equivalent-Circuit Methods*. Norwood, MA, USA: Artech House, 2015, ISBN 978-1-63081-027-6. **[V-noDOI]** (hardback ISBN confirmed by the publisher and Blackwell's; some catalogs give 2016, but the publisher and print records give 2015)
— Covers Kalman-filter SOC estimation with the ESC model and BMS requirements. Cite it for the model-based alternative to rest-only estimation.

[4] M. Petzl and M. A. Danzer, "Advancements in OCV measurement and analysis for lithium-ion batteries," *IEEE Trans. Energy Convers.*, vol. 28, no. 3, pp. 675–681, 2013, doi: 10.1109/TEC.2013.2259490. **[V-DOI]**
— Compares OCV measurement methods (low-current versus incremental) and their accuracy. This bears on how our 25 °C registration tables are built.

[5] A. Barai, W. D. Widanage, J. Marco, A. McGordon, and P. Jennings, "A study of the open circuit voltage characterization technique and hysteresis assessment of lithium-ion cells," *J. Power Sources*, vol. 295, pp. 99–107, 2015, doi: 10.1016/j.jpowsour.2015.06.140. **[V-DOI]**
— Quantifies OCV hysteresis and how much the result depends on the test method. Our samples are all post-discharge rests, so hysteresis branch is held fixed. We should state that as a limitation.

[6] M. A. Roscher and D. U. Sauer, "Dynamic electric behavior and open-circuit-voltage modeling of LiFePO4-based lithium ion secondary batteries," *J. Power Sources*, vol. 196, no. 1, pp. 331–336, 2011, doi: 10.1016/j.jpowsour.2010.06.098. **[V-DOI]**
— Shows strong OCV hysteresis and a flat OCV in LFP. This is relevant to the two LFP-like cells (A123, ATL) in the Plett ESC test set.

[7] A. Farmann and D. U. Sauer, "A study on the dependency of the open-circuit voltage on temperature and actual aging state of lithium-ion batteries," *J. Power Sources*, vol. 347, pp. 1–13, 2017, doi: 10.1016/j.jpowsour.2017.01.098. **[V-DOI]**
— OCV of C/NMC, C/LFP and LTO/NMC cells from about −20 to 45 °C. The relaxation time needed grows as temperature and SOC fall, and the authors propose an OCV model with a temperature-correction term. This supports our finding that the cold rest-voltage offset is large and differs between cells.

[8] Y. Xing, W. He, M. Pecht, and K. L. Tsui, "State of charge estimation of lithium-ion batteries using the open-circuit voltage at various ambient temperatures," *Appl. Energy*, vol. 113, pp. 106–115, 2014, doi: 10.1016/j.apenergy.2013.07.008. **[V-DOI]**
— Builds an OCV–SOC–temperature table for a cell and uses it inside a UKF. Errors are lower than with a single-temperature table. This is prior art for per-cell multi-temperature OCV tables. CALCE asks users of its INR 18650-20R and A123 data to cite this paper.

[9] F. Zheng, Y. Xing, J. Jiang, B. Sun, J. Kim, and M. Pecht, "Influence of different open circuit voltage tests on state of charge online estimation for lithium-ion batteries," *Appl. Energy*, vol. 183, pp. 513–525, 2016, doi: 10.1016/j.apenergy.2016.09.010. **[V-DOI]**
— Compares low-current OCV tests with incremental OCV tests at several temperatures on the INR 18650-20R. It describes the CALCE INR data in our development set and is the CALCE-requested citation. CALCE also lists W. He, N. Williard, C. Chen, and M. Pecht, *Int. J. Electr. Power Energy Syst.*, vol. 62, pp. 783–791, 2014, doi: 10.1016/j.ijepes.2014.04.059 (verified). Add it as a 46th reference if the journal requires every listed CALCE paper.

[10] Y. Wei and L. Ling, "State-of-charge estimation for lithium-ion batteries based on temperature-based fractional-order model and dual fractional-order Kalman filter," *IEEE Access*, vol. 10, pp. 37131–37148, 2022, doi: 10.1109/ACCESS.2022.3163413. **[V-DOI]**
— Uses an OCV–SOC lookup table for each ambient temperature plus a temperature offset function, and interpolates for untested temperatures (from the abstract and search summaries; full text not read). This is the closest IEEE Access precedent for interpolating registration tables in temperature.

[11] V. V. Viswanathan et al., "Effect of entropy change of lithium intercalation in cathodes and anodes on Li-ion battery thermal management," *J. Power Sources*, vol. 195, no. 11, pp. 3720–3729, 2010, doi: 10.1016/j.jpowsour.2009.11.103. **[V-DOI]**
— Measures entropic dOCV/dT, which depends on SOC and electrode material. This is the thermodynamic part of the temperature shift. The rest of the cold rest-voltage drop is incomplete relaxation.

### B. Rest/relaxation-based OCV estimation and shortened rest

[12] W. Waag and D. U. Sauer, "Adaptive estimation of the electromotive force of the lithium-ion battery after current interruption for an accurate state-of-charge and capacity determination," *Appl. Energy*, vol. 111, pp. 416–427, 2013, doi: 10.1016/j.apenergy.2013.05.001. **[V-DOI]**
— Estimates the equilibrium EMF from the relaxation that follows current interruption, without waiting for full rest. This is the closest problem setting to ours: SOC right after the load stops.

[13] L. Pei, T. Wang, R. Lu, and C. Zhu, "Development of a voltage relaxation model for rapid open-circuit voltage prediction in lithium-ion batteries," *J. Power Sources*, vol. 253, pp. 412–418, 2014, doi: 10.1016/j.jpowsour.2013.12.083. **[V-DOI]**
— A 2RC-type relaxation model with a time-varying diffusion time constant. Reported OCV error is about 1 mV after roughly 20 min. It represents the RC-extrapolation family behind our B3 baseline.

[14] J. Meng, D.-I. Stroe, M. Ricco, G. Luo, M. Swierczynski, and R. Teodorescu, "A novel multiple correction approach for fast open circuit voltage prediction of lithium-ion battery," *IEEE Trans. Energy Convers.*, vol. 34, no. 2, pp. 1115–1123, 2019, doi: 10.1109/TEC.2018.2880561. **[V-DOI]**
— Corrects the OCV prediction segment by segment from short relaxation data. It predicts LFP OCV within about 15 min. It is a rest-time reduction method, usually validated on the same cell type it was tuned on.

[15] Y. Qian et al., "Fast open circuit voltage estimation of lithium-ion batteries using a relaxation model and genetic algorithm," *IEEE Access*, vol. 10, pp. 96643–96651, 2022, doi: 10.1109/ACCESS.2022.3203178. **[V-DOI]**
— Fits a relaxation model with a GA and needs about 10 min of rest instead of more than 2 h. This is a recent IEEE Access example of rest-time reduction.

[16] C.-J. Ko and K.-C. Chen, "Using tens of seconds of relaxation voltage to estimate open circuit voltage and state of health of lithium ion batteries," *Appl. Energy*, vol. 357, Art. no. 122488, 2024, doi: 10.1016/j.apenergy.2023.122488. **[V-DOI]**
— Estimates OCV (and SOH) from tens of seconds of relaxation. It shows that very short rests carry OCV information, which is the same premise as our r = 300 s rest window.

### C. Data-driven SOC estimation and reviews

[17] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in *Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discovery Data Mining*, 2016, pp. 785–794, doi: 10.1145/2939672.2939785. **[V-DOI]**
— The learner used for our residual correction (S_simple) and the generic XGB baseline.

[18] E. Chemali, P. J. Kollmeyer, M. Preindl, R. Ahmed, and A. Emadi, "Long short-term memory networks for accurate state-of-charge estimation of Li-ion batteries," *IEEE Trans. Ind. Electron.*, vol. 65, no. 8, pp. 6730–6739, 2018, doi: 10.1109/TIE.2017.2787586. **[V-DOI]**
— LSTM SOC estimation across ambient temperatures on the Panasonic 18650PF data. It is the first publication listed on the Panasonic dataset page. It is a representative deep-learning SOC model, trained and tested on the same cell type.

[19] C. Vidal, P. Malysz, P. Kollmeyer, and A. Emadi, "Machine learning applied to electrified vehicle battery state of charge and state of health estimation: State-of-the-art," *IEEE Access*, vol. 8, pp. 52796–52814, 2020, doi: 10.1109/ACCESS.2020.2980961. **[V-DOI]**
— Review of ML for SOC and SOH. Cite it for the landscape of data-driven SOC estimation.

[20] D. N. T. How, M. A. Hannan, M. S. H. Lipu, and P. J. Ker, "State of charge estimation for lithium-ion batteries using model-based and data-driven methods: A review," *IEEE Access*, vol. 7, pp. 136116–136136, 2019, doi: 10.1109/ACCESS.2019.2942213. **[V-DOI]**
— Review that compares OCV lookup, model-based and data-driven SOC methods. It places "OCV lookup after rest" among the established methods.

[21] D. Wang, J. Hwang, J. Lee, M. Kim, and I. Lee, "Temperature-based state-of-charge estimation using neural networks, gradient boosting machine and a Jetson Nano device for batteries," *Energies*, vol. 16, no. 6, Art. no. 2639, 2023, doi: 10.3390/en16062639. **[V-DOI]**
— NN and GBM SOC models with temperature as an input, but only over 25–40 °C. It shows that tree-boosting SOC models with temperature inputs exist, but they were not tested on unseen cells or at subzero temperatures.

### D. Cross-cell / cross-temperature generalization, transfer learning, evaluation leakage

[22] C. Vidal, P. Kollmeyer, E. Chemali, and A. Emadi, "Li-ion battery state of charge estimation using long short-term memory recurrent neural network with transfer learning," in *Proc. IEEE Transp. Electrific. Conf. Expo (ITEC)*, 2019, pp. 1–6, doi: 10.1109/ITEC.2019.8790543. **[V-DOI]**
— Transfer learning of an LSTM SOC estimator to a new cell. It needs labeled target-cell data, whereas our setting gives the target cell only a registration table. The LG HG2 dataset page also lists this paper.

[23] L. Shen, J. Li, L. Zuo, L. Zhu, and H. T. Shen, "Source-free cross-domain state of charge estimation of lithium-ion batteries at different ambient temperatures," *IEEE Trans. Power Electron.*, vol. 38, no. 6, pp. 6851–6862, 2023, doi: 10.1109/TPEL.2023.3251568. **[V-DOI]**
— Domain adaptation of SOC models across ambient temperatures. It shows that temperature shift is a recognized generalization problem, handled there by adapting to unlabeled target-temperature data rather than by per-cell registration.

[24] S. Kapoor and A. Narayanan, "Leakage and the reproducibility crisis in machine-learning-based science," *Patterns*, vol. 4, no. 9, Art. no. 100804, 2023, doi: 10.1016/j.patter.2023.100804. **[V-DOI]**
— A taxonomy of leakage that inflates ML performance, with cross-field evidence. It motivates our leakage audit and the held-out, preregistered test.

[25] D. R. Roberts et al., "Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure," *Ecography*, vol. 40, no. 8, pp. 913–929, 2017, doi: 10.1111/ecog.02881. **[V-DOI]**
— Shows that random CV on grouped data overestimates performance and that blocked or grouped CV is needed. Our LODO CV is grouped, yet it still overestimated the gain on new cells, which extends this point.

[26] S. Yan and M. Wiston, "Mission-phase feature learning for eVTOL Li-ion battery prognostics: A leakage-safe cell-held-out benchmark for SOC, SOH, and RUL," *Batteries*, vol. 12, no. 9, Art. no. 322, 2026, doi: 10.3390/batteries12090322. **[V-DOI]**
— A leakage-safe benchmark with held-out cells on the CMU eVTOL data, in which random forest beats deep models. It is the closest battery-ML evaluation-rigor work and is also aviation-related.

[27] M. Dubarry, N. Vuillaume, and B. Y. Liaw, "Origins and accommodation of cell variations in Li-ion battery pack modeling," *Int. J. Energy Res.*, vol. 34, no. 2, pp. 216–231, 2010, doi: 10.1002/er.1668. **[V-DOI]** (Crossref gives the 2009 online date; the volume is 2010)
— Documents cell-to-cell variation and its sources. It supports the cell-specific behavior we found, although our variation is mostly between cell models.

### E. Low-cost sensing and measurement error

[28] X. Lin and A. G. Stefanopoulou, "Analytic bound on accuracy of battery state and parameter estimation," *J. Electrochem. Soc.*, vol. 162, no. 9, pp. A1879–A1891, 2015, doi: 10.1149/2.0791509jes. **[V-DOI]**
— Gives a Cramér–Rao-type bound showing that SOC accuracy is limited by voltage-sensor noise divided by OCV slope. This explains why flat-OCV (LFP) regions and ADC error hurt rest-voltage SOC.

[29] J.-H. Hwang, J.-H. Lee, and I. S. Lee, "Analysis and diagnosis of the effect of voltage and current sensor faults on the state of charge estimation of lithium-ion batteries based on neural networks," *Int. J. Control Autom. Syst.*, vol. 22, no. 5, pp. 1691–1706, 2024, doi: 10.1007/s12555-023-0546-9. **[V-DOI]**
— Injects synthetic noise and bias into the inputs of NN and GBM SOC models and diagnoses faults. It is the closest ML sensor-error study. Its errors are assumed, whereas ours are parameterized from a low-cost measurement chain (STM32 + divider ADC).

### F. Drone / UAV / eVTOL batteries and battery stations

[30] K. A. O. Suzuki, P. Kemper Filho, and J. R. Morrison, "Automatic battery replacement system for UAVs: Analysis and design," *J. Intell. Robot. Syst.*, vol. 65, no. 1–4, pp. 563–586, 2012, doi: 10.1007/s10846-011-9616-y. **[V-DOI]** (Crossref gives the 2011 online date; the issue is 2012)
— Design and analysis of an automatic battery-swap station for UAVs. It sets out the station setting our application assumes.

[31] N. K. Ure, G. Chowdhary, T. Toksoz, J. P. How, M. A. Vavrina, and J. Vian, "An automated battery management system to enable persistent missions with multiple aerial vehicles," *IEEE/ASME Trans. Mechatronics*, vol. 20, no. 1, pp. 275–286, 2015, doi: 10.1109/TMECH.2013.2294805. **[V-DOI]**
— Automated swap and recharge station, with health-aware battery management for multi-UAV persistent missions. The station has to judge the state of each returned pack, which is the decision our SOC estimate feeds.

[32] A. Bills et al., "A battery dataset for electric vertical takeoff and landing aircraft," *Sci. Data*, vol. 10, Art. no. 344, 2023, doi: 10.1038/s41597-023-02180-5. **[V-DOI]**
— eVTOL mission-profile cycling data (CMU) and the aviation battery-duty context. Our paper uses no flight loads, and this reference should be used to state that gap.

[33] H. Zhang, M. Zhou, and X. Lan, "State of charge estimation algorithm for unmanned aerial vehicle power-type lithium battery packs based on the extended Kalman filter," *Energies*, vol. 12, no. 20, Art. no. 3960, 2019, doi: 10.3390/en12203960. **[V-DOI]**
— EKF SOC estimation for UAV Li-Po packs at different temperatures. It is UAV in-flight SOC estimation, which our post-landing, rest-only estimate complements.

### G. Preregistration, reproducibility, negative results

[34] B. A. Nosek, C. R. Ebersole, A. C. DeHaven, and D. T. Mellor, "The preregistration revolution," *Proc. Natl. Acad. Sci. USA*, vol. 115, no. 11, pp. 2600–2606, 2018, doi: 10.1073/pnas.1708274114. **[V-DOI]**
— Separates confirmatory (preregistered) from exploratory analyses. This is the basis for our commit-hash preregistration and our labeling of post hoc analyses.

[35] O. E. Gundersen and S. Kjensmo, "State of the art: Reproducibility in artificial intelligence," in *Proc. AAAI Conf. Artif. Intell.*, vol. 32, no. 1, 2018, doi: 10.1609/aaai.v32i1.11503. **[V-DOI]** (Crossref lists no page numbers, so none are given)
— A survey showing that most AI papers do not document enough to reproduce their results. It motivates our release of code, protocol and run lock.

### H. Datasets used (canonical or requested citations)

[36] P. Kollmeyer, C. Vidal, M. Naguib, and M. Skells, "LG 18650HG2 Li-ion battery data and example deep neural network xEV SOC estimator script," Mendeley Data, V3, 2020, doi: 10.17632/cp3473x7xv.3. **[V-DOI]** (DataCite lists only M. Naguib as creator; the four contributors are taken from the Mendeley page)
— Development data (LG HG2). The page asks users to reference the dataset and lists [37] and [22] as papers using similar data.

[37] C. Vidal, P. Kollmeyer, M. Naguib, P. Malysz, O. Gross, and A. Emadi, "Robust xEV battery state-of-charge estimator design using a feedforward deep neural network," *SAE Int. J. Adv. Curr. Pract. Mobility*, vol. 2, no. 5, pp. 2872–2880, 2020, doi: 10.4271/2020-01-1181. **[V-DOI]**
— The paper the HG2 example script reproduces (FNN SOC estimation, −20 to 40 °C). Cite it together with [36].

[38] P. Kollmeyer, "Panasonic 18650PF Li-ion battery data," Mendeley Data, V1, 2018, doi: 10.17632/wykht8y7tg.1. **[V-DOI]**
— Development data (Panasonic PF). The page asks for "appropriate reference" and lists [18] first among the papers using it.

[39] P. Kollmeyer, "Samsung INR21700 30T 3Ah Li-ion battery data," Mendeley Data, V1, 2020, doi: 10.17632/9xyvy2njj3.1. **[V-DOI]**
— Development data (Samsung 30T). The readme says "it should be appropriately referenced". Confirm that the downloaded copy came from this DOI. The readme in `C:\BMS\data\raw\samsung_30t` matches the content of this dataset.

[40] P. Kollmeyer, "Turnigy Graphene 5000mAh 65C Li-ion battery data," Mendeley Data, V1, 2020, doi: 10.17632/4fx8cjprxm.1. **[V-DOI]**
— Development data (Turnigy Graphene). Its readme carries the same request to reference the data.

[41] L. Uwalaka, Q. Yao, J. Duque, and P. Kollmeyer, "Fast charging and characterization dataset for Porsche Taycan LG E66 battery cell and module," Borealis, V1.0, 2024, doi: 10.5683/SP3/7JP3NM. **[V-DOI]**
— First preregistered test cell (LG E66; −20 to 40 °C; CC BY 4.0). The Borealis page asks users to "use the data citation shown on the dataset page", and the citation given here is that one.

[42] L. Uwalaka, Q. Yao, J. Duque, P. Kollmeyer, and A. Emadi, "Experimental performance analysis of LG E-66 cells from a fast-charging Porsche Taycan battery module," in *Proc. IEEE Transp. Electrific. Conf. Expo (ITEC)*, 2024, pp. 1–6, doi: 10.1109/ITEC60657.2024.10599015. **[V-DOI]**
— The related publication listed on the Borealis page for [41]. Cite both.

[43] M. A. Khan, S. Thatipamula, L. Tresca, L. Xu, A. Trewartha, and S. Onori, "High-power lithium-ion battery characterization dataset for stochastic battery modeling," *Sci. Data*, vol. 12, Art. no. 1506, 2025, doi: 10.1038/s41597-025-05725-y. **[V-DOI]**
— Second preregistered test set: 12 Molicel P42A cells at 5, 25 and 40 °C, intended for studying cell-to-cell variation. This is the canonical data descriptor.

[44] S. Onori, L. Xu, V. S. Thatipamula, M. A. Khan, L. Tresca, and A. Trewartha, "High-power lithium-ion battery characterization dataset for stochastic battery modeling," OSF, 2025, doi: 10.17605/OSF.IO/9CEAV. **[V-DOI]** (creator order as in DataCite)
— Repository record for the P42A data. Cite it together with [43].

[45] G. L. Plett, "ESCtoolbox" (MATLAB toolbox with OCV and dynamic test data for six cells at −25 to 45 °C, supplementary material to [2]), Univ. Colorado Colorado Springs. [Online]. Available: http://mocha-java.uccs.edu/BMS1/CH02/ESCtoolbox.zip (accessed Nov. 18, 2026). **[V-noDOI]** (no DOI or license is stated; the URL answered HTTP 200 on 2026-11-18 with a 1.19 GB zip last modified 2023-07-24)
— Data for the two-point confirmatory test (A123, ATL, E1, E2, P14, SAM). No citation request was found, so cite [2] as the canonical source plus this URL. Do not redistribute the files.

Counts: 45 numbered references. 42 have a DOI that was resolved and checked ([V-DOI]). 3 have no DOI because none exists ([V-noDOI]: [2], [3], [45]). 0 are UNVERIFIED. Optional extra, verified: He et al. 2014, doi: 10.1016/j.ijepes.2014.04.059 (see [9]).

## (b) Positioning

- **The temperature-dependent OCV table itself is not new.** Plett's ESC model [1]–[3], [45] already gives each cell its own OCV(z,T) = OCV0(z) + T·OCVrel(z), fitted from OCV tests at many temperatures. Xing et al. [8] and Wei & Ling [10] use per-cell OCV–SOC–temperature tables, interpolated in temperature in [10]. Farmann & Sauer [7] add a temperature-correction term. Our two-point registration T2_cold is the minimal two-temperature case of this per-cell, linear-in-T structure. It should be presented that way, not as a new model.
- **What differs from that prior work.** Prior tables are built from equilibrium or low-current OCV tests at several temperatures, and their value is shown inside a filter on the same cell. Ours is built from fixed-length (r = 300 s) post-discharge rest voltages, which include incomplete relaxation, using one 25 °C and one cold registration test. It is used directly as a training-free estimator. We found no prior work that asks how few registration temperatures suffice, or that compares such a table with a learned cross-cell correction on unseen cells.
- **Relaxation and short-rest OCV methods** [12]–[16] extrapolate OCV from seconds to minutes of rest, usually tuned and validated on one cell type at one or a few temperatures. Our B3 2RC baseline belongs to this family. The contribution is not a relaxation model. We show that, at low temperature, the remaining error is a cell-specific offset that extrapolation and cross-cell learning do not remove. Farmann & Sauer's [7] finding that relaxation time grows at low T is consistent with this.
- **Data-driven SOC and transfer learning** [18], [21]–[23] are usually evaluated on held-out drive cycles of the same cell, or they adapt with data from the target cell or temperature. Our negative result is complementary. A residual XGBoost [17] trained on other cells looked better in grouped LODO CV, but in a preregistered test on unseen cells (LG E66 [41], Molicel P42A [43]) it gained nothing over plain registration lookup. The learned cold correction, sized to the development cells, over-corrected E66.
- **Evaluation rigor.** Leakage and grouped-CV work [24]–[26] warns that random splits inflate performance. Our grouped (leave-one-dataset-out) CV still overestimated the transferable gain, because of differences in temperature mix and cell-specific cold sensitivity. In this literature search we found no battery-SOC study that preregistered a one-shot test on held-out cells (commit-hash protocol [34]). We can claim that cautiously ("to our knowledge") as a methodological contribution.
- **Claims we can honestly make.** (1) A preregistered held-out-cell comparison of learned residual correction against per-cell registration lookup for SOC from rest voltage alone. (2) Evidence that the cold rest-voltage offset varies between cell models (dev cells versus E66 at −20 °C), so cross-cell learning cannot stand in for cold data on the target cell. (3) In a second preregistered test (Plett ESC data [45], 6 cells), a training-free two-point registration beat 25 °C lookup: MAE 5.23 versus 7.97 %p, paired CI of the difference [+1.08, +4.36] (H4 supported). It was statistically tied with the frozen learned model: 5.23 versus 5.80, paired CI [−0.35, +1.60] (H3 not supported). (4) The practical recommendation that follows: a station should spend effort on one extra cold registration per cell type, not on a cross-cell model.
- **Claims to avoid.** Novelty of temperature-dependent OCV tables or of linear-in-T interpolation ([2], [8], [10]). Novelty of rest-time reduction ([12]–[16]). Superiority of two-point registration over the learned model (H3 was not supported). The E66 two-point result (1.34 vs 1.81 vs 1.86) may only be reported as post hoc. Validation under drone flight loads ([32] shows that real eVTOL duty differs from the loads we tested), and robustness to real low-cost sensors beyond the injected error model ([28], [29]).
