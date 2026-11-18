# 2점 등록 확증 시험 데이터 변환 노트: Plett ESC toolbox (11-18)

변환: `python -I analysis/prepare_final3.py` → `C:/BMS/data/holdout_final3/rest_final3.npz`(882개).
배치는 `rest_final.npz`와 같다(rest_V 1800, pre_V·pre_I 300, meta 열 같음). meta 끝에 `is_reg2`(bool)를 붙였다.
모델(추정기·기준선)은 돌리지 않았다. 아래는 모두 모델 없는 점검이다.

## 원천과 범위
- Plett, *Battery Management Systems Vol. I* 보조 자료 `ESCtoolbox.zip`(UCCS).
  DYN 48개와 25 °C OCV 6개를 HTTP range로 받았다 → `raw/plett_esctoolbox/`.
- **라이선스:** zip 안의 README.txt에 "copyright (c) 2015 Gregory L. Plett (UCCS), CC BY-NC-SA 4.0, educational and informational purposes"라고 적혀 있다. 비영리 연구 논문에서 인용하며 쓰는 것은 가능하다. 재배포한다면 같은 라이선스를 따라야 하므로 데이터는 재배포하지 않고 출처만 밝힌다.
- dataset = `Plett_ESC`, cell = A123 · ATL · E1 · E2 · P14 · SAM(각 1셀).
  chem은 A123·ATL = `LFP`(전압 창으로 추정), 나머지 = `Li-ion`(화학계 미확인).
- 온도: −25, −15, −5, 5, 15, 25, 35, 45 °C. 셀·온도마다 DYN 파일 1개다.

## prepare_final.py와 다른 점·구체 규칙
1. **부호:** Plett는 방전이 +이다. `I = −current`, 장비 Ah = `chgAh − disAh`로 바꿔 넣고, 그 뒤로는 `prepare_final.clean`·`anchor`·`samples`를 그대로 쓴다.
   장비 Ah와 전류 적분의 최대 차이는 0.001–0.09 Ah(용량의 0.6 % 이하)다.
2. **script1만 쓴다.** script1은 시험 온도에서 돈다: 25 °C 만충 → 시험 온도에서 담금 → 1C로 약 90 %까지 → 동적 프로파일과 약 12분 휴지를 번갈아 약 10 %까지.
   script2(잔량 방전)와 script3(충전)은 Plett 프로토콜상 25 °C에서 돌기 때문에 넣지 않았다.
3. **기준점:** 모든 파일에서 script1이 만충 휴지에서 시작한다(V0 ≥ vmax − 0.08, 전류 ≈ 0).
   그래서 dev 규칙 "파일 시작이 만충"으로 기준점 1개가 생긴다(t0 = 파일 시작). 따로 정의한 기준점은 없다.
4. **셀 기준 용량:** Plett 25 °C OCV 시험의 script1(C/30, 만충 → Vmin) + script2(25 °C 잔량 방전) 순방전 Ah.
   A123 2.073, ATL 19.445, E1 9.128, E2 5.212, P14 14.941, SAM 2.175 Ah. script1만 쓰면 0.6–1.5 % 작다.
   - 점검: 첫 휴지 SOC가 모든 셀·온도에서 0.889–0.900이다. 프로토콜의 "90 %까지 방전"과 맞는다.
5. **I_REST** = 기준 용량 / 150(공칭 용량 정보 없음). vmax = 25 °C OCV script1 시작 전압.
6. **온도:** meas_temp는 NaN이다(셀 온도 채널 없음). nom_src = `filename`(파일 이름의 N/P 온도).
7. **등록:** is_reg = 25 °C DYN 파일(셀당 하나, 16–18개). is_reg2 = −5 °C DYN 파일(17–27개).
   −5 °C는 0 °C에 가장 가까운 온도 중 5 °C와 동률이라, 추운 쪽을 고르는 규칙으로 정했다. 둘이 겹치는 표본은 없다.

## 표본 수 (SOC 범위 밖으로 빠진 것 0개)

| 셀 | −25 | −15 | −5 (reg2) | 5 | 15 | 25 (reg) | 35 | 45 |
|---|---|---|---|---|---|---|---|---|
| A123 | 24 | 24 | 18 | 19 | 18 | 18 | 18 | 18 |
| ATL | 10 | 15 | 18 | 17 | 17 | 17 | 16 | 16 |
| E1 | 16 | 17 | 22 | 17 | 17 | 17 | 17 | 16 |
| E2 | 17 | 19 | 18 | 20 | 18 | 18 | 18 | 17 |
| P14 | 18 | 17 | 17 | 17 | 16 | 16 | 16 | 16 |
| SAM | 37 | 20 | 27 | 22 | 22 | 18 | 18 | 18 |

- 채점 후보 658개. 그중 등록 온도(−5 °C)보다 추운 −25·−15 °C가 **234개**다. 등록: reg25 104개, reg2 120개.

## 점검 (셀 × 온도, `prepare_final3.py` 출력)
- **SOC 범위:** 상한은 모두 0.889–0.900이다(90 % 위의 휴지는 없다).
  하한은 0.03–0.15. 예외는 ATL −25 °C(0.52), −15 °C(0.26)와 E1 −25 °C(0.28), E2 −25 °C(0.22)로, 차단 전압에 먼저 닿는다.
- **V300–SOC Spearman:** 0.988(ATL −25 °C) – 1.000. LFP 두 셀도 0.995 이상이다.
- **raw_n60:** 59–61. 모두 실제 1 s 기록이다.
- **휴지 길이:** 중앙값 719 s, 최소 300–309 s(파일 마지막 휴지 일부).
- **직전 전류:** 직전 60 s 평균은 0.05–0.11C다. 직전 300 s 최대 방전 전류(중앙값)는 온도에 따라 다르다(프로파일 크기가 온도별로 다름).
  - −25 °C: 0.25–1.0C
  - −15 °C: 0.3–1.0C
  - −5 °C: 0.5–3.0C
  - 25 °C 이상: 1.5–4.9C
  - 그래서 저온 채점 표본은 등록(25 °C) 표본보다 약한 동적 부하 뒤의 휴지다.
- **첫 휴지:** 1C 정전류 방전 뒤다. 나머지는 동적 프로파일 뒤다.

## 사전 등록 때 정할 것
- 기준 온도 25 °C, 2점 등록의 T_low = −5 °C(dev는 0 °C였다. T2_cold 식의 T_low만 바뀐다).
- 주 채점 = −25·−15 °C(등록보다 추운 쪽). 보조 = 5·15·35·45 °C.
- CI는 6셀 셀 단위 부트스트랩.
- ATL −25 °C는 SOC가 0.52 이상만 있다. 그대로 두고 보고하자는 것이 제안이다.

## ESC 모델 파일 (11-18 추가, 심사자 요청: 평형 OCV 기준선)
- **ESCtoolbox.zip에는 미리 맞춘 모델 파일이 없다.** 중앙 디렉터리 413개 항목을 모두 확인했다: OCV_Files 252개, DYN_Files 160개, README.txt.
  `.m` 스크립트도, `<CELL>model.mat`·`<CELL>model-ocv.mat`도 들어 있지 않다.
  README에 따르면 모델은 사용자가 `runProcessOCV.m`(→ `A123model-ocv.mat` 등)과 `runProcessDynamic.m`(→ `A123model.mat` 등)을 돌려 직접 만든다.
  그런데 그 .m 파일들도 이 zip에는 없다.
- **Plett가 맞춘 모델이 배포된 셀은 E2 하나뿐이다.** BMS Vol. II 보조 자료에서 찾았다:
  - `http://mocha-java.uccs.edu/BMS2/CH3/ESCEKF.zip`(ESCSPKF.zip에도 같은 파일) → `models/E2model_BMS2_ESCEKF.mat`
  - `http://mocha-java.uccs.edu/BMS2/CH2/PCMSCM.zip` → `models/E2model_BMS2_PCMSCM.mat`(dOCV0·dOCVrel만 없고 나머지 값은 같다)
  - batterysim/esctoolbox-python 저장소에도 맞춘 모델 파일은 없다(A123 CSV와 코드뿐).
  - 나머지 5셀(A123, ATL, E1, P14, SAM)의 모델은 배포된 것을 찾지 못했다.
    평형 OCV 기준선을 6셀 모두에 쓰려면 원시 OCV 시험으로 Plett의 processOCV 절차를 다시 구현해야 한다.
- **원시 OCV 시험:** 6셀 × 8개 온도의 .mat 48개(39 MB)를 받았다 → `raw/plett_esctoolbox/ocv/`(xlsx는 받지 않음).
- **E2 모델 필드:** `OCV0, OCVrel, SOC, OCV, SOC0, SOCrel, OCVeta, OCVQ, name, temps, etaParam, QParam, GParam, M0Param, MParam, R0Param, RCParam, RParam, dOCV0, dOCVrel`.
  - temps = −25, −15, −5, 5, 15, 25, 35, 45.
  - SOC 격자 201점(0–1), OCV0 3.031–4.145 V, OCVrel −0.0006–0.0005 V/°C.
  - OCV 격자 178점(2.49–4.26 V), SOC0 −0.019–1.042, SOCrel −0.0012–0.0006.
  - QParam 5.117–5.156 Ah. 우리 25 °C 기준 용량 5.212 Ah와 1–2 % 다르다(용량 정의 차이).
  - OCV(SOC 0.5) = 3.9288 V(25 °C), 3.9240 V(−5 °C). 계산식은 Plett의 OCVfromSOCtemp: OCV0 + T·OCVrel.
- 점검 스크립트(추정기 실행 아님): `python -I analysis/tmp/v2b_esc_model_check.py [models 폴더]`.
- **기준선으로 쓸 때 주의 (누설):**
  - 동적 파라미터(R0Param, RParam 등)는 8개 온도 전부의 DYN 파일, 즉 우리 채점 파일 자체로 맞춘 것이다(temps 8개).
  - OCV 관계(OCV0 + T·OCVrel)는 아래 "평형 OCV 곡선"의 점검에서 보듯 **5–45 °C OCV 시험만으로** 맞춘 것으로 보인다.
    그래서 −25·−15·−5 °C에서는 선형 외삽이다.
  - 이 모델을 그대로 쓰면 채점 온도의 정보(동적 파라미터)가 섞이고, 저온 등록 온도(−5 °C)의 OCV는 쓰지 않는다.
    2점 등록과 같은 조건의 비교가 아니다.

## 평형 OCV 곡선 (11-18 추가)
- 변환: `python -I analysis/prepare_ocv_final3.py` → `C:/BMS/data/holdout_final3/ocv_eq.npz`(6셀 × 8개 온도 = 48곡선). 모델·추정기는 돌리지 않았다.
- **배열:** `cell`, `temp_c`, `soc_grid`(201점, 0..1), `V`(48×201, 평형 OCV), `V_dis`(48×201, IR 보정 방전 곡선만, 민감도용).
  점검용으로 `eta`, `dV50`, `split_z`, `zchg_max`, `zdis_min`, `q25`, `q25_plett`도 저장했다. `notes`에 방법 요약이 있다.
- **Plett processOCV에서 그대로 따른 것:**
  - script1(T에서 C/30 방전, step 2)과 script3(T에서 C/30 충전, step 2)를 쓴다.
  - 쿨롱 효율: eta25 = 25 °C 파일 총 방전/총 충전. eta_T = (총 방전 − eta25·(s2 + s4 충전)) / (s1 + s3 충전). 충전 Ah에 곱한다.
  - IR 보정: step 2 시작·끝의 전압 점프. 방전 곡선에는 더하고 충전 곡선에서는 빼며, 처음→끝을 선형으로 섞는다. min(IR1D, 2·IR2C) 같은 상한 규칙도 같다.
  - SOC: 방전 z = 1 − disAh/Q(첫 점을 1로), 충전 z = eta_T·chgAh/Q(첫 점을 0으로).
  - 결합: z < z_s에서는 충전 − z·ΔV, z > z_s에서는 방전 + (1 − z)·ΔV(ΔV = z_s에서의 충전−방전 차). 201점 격자에 선형 보간하고, 격자 밖은 선형 외삽한다(interp1 'extrap'과 같음).
- **단순화·차이:**
  1. **SOC 기준 용량** = rest_final3의 Q25(25 °C OCV s1+s2 순방전, eta 없이). Plett 식의 Q25(충전에 eta25를 곱함)와는 0.01 % 이내다(예: E2 5.2117 대 5.2127 Ah).
  2. **결합점 z_s:** Plett는 0.5로 고정한다. 저온에서 충전 곡선이 z = 0.5에 못 미치면 0.5에서의 ΔV가 외삽이 되어 곡선이 깨진다(E2 −25 °C: 충전 z 최대 0.37, ΔV50 = 13 V로 발산).
     그래서 z_s = min(0.5, 충전 z 최대 − 0.02)로 내렸다. **바뀐 곡선은 E2 −25 °C 하나(z_s = 0.35)이고**, 나머지 47개는 Plett와 같은 0.5다. ATL −25 °C는 충전 z 최대가 0.54로 겨우 넘는다.
  3. Plett는 온도별 곡선을 OCV0 + T·OCVrel로 최소제곱 근사해 모델에 넣는다. 여기서는 **근사 전의 온도별 곡선**(rawocv에 해당)을 그대로 저장했다.
  4. 저온 곡선은 덜 믿을 만하다. 저온일수록 ΔV(충전−방전 과전압 차)가 커서, 반으로 나누는 가정의 오차가 커진다.
     −25 °C의 ΔV: A123 110, ATL 470, E1 132, E2 295(z_s 0.35에서), P14 84, SAM 193 mV. 25 °C에서는 3–45 mV다.
  5. SAM의 −5·5 °C는 ΔV50이 음수(−7.5, −4.8 mV)다. IR 보정이 과전압보다 조금 크게 잡힌 것으로 보인다. 크기가 작아 그대로 뒀다.
- **E2 점검 (우리 곡선 − Plett 모델 OCV0 + T·OCVrel, mV, SOC 0.05–0.95):**

| T (°C) | −25 | −15 | −5 | 5 | 15 | 25 | 35 | 45 |
|---|---|---|---|---|---|---|---|---|
| 최대 | 53.3 | 23.8 | 10.2 | 1.9 | 2.9 | 2.2 | 3.0 | 2.7 |
| 평균 | 25.7 | 11.7 | 4.6 | 0.9 | 1.2 | 0.5 | 0.8 | 0.7 |

  - 전체 SOC 0–1로 보면 5–45 °C의 최대가 2.2–8.5 mV다(양 끝 외삽 구간).
  - 우리 Q로 SOC를 환산해도 결과는 거의 같다(±0.1 mV).
  - **5–45 °C 곡선만으로 우리가 OCV0·OCVrel을 직접 맞추면 Plett 값과 OCV0 최대 0.2 mV, OCVrel 최대 0.007 mV/°C 차이**다.
    8개 온도 전부로 맞추면 16.7 mV, −25 °C만 빼면 9.6 mV 차이가 난다.
    → 구현은 Plett와 사실상 같다. **Plett의 E2 OCV 모델은 5–45 °C만으로 맞춘 것이고**, 저온 차이(10–53 mV)는 그 선형 외삽과 실제 저온 곡선의 차이다.
- **기준선 설계 시사점 (판단은 사전 등록 때):**
  - 평형 OCV 기준선을 "등록 온도의 OCV 시험만" 쓰는 조건(25 °C, 또는 25 + −5 °C)으로 만들 수 있다.
  - `ocv_eq.npz`에는 채점 온도(−25, −15 °C 등)의 곡선도 들어 있다. 기준선에 쓰면 오라클(그 온도의 OCV를 아는 경우)이 되므로 상한으로만 보고해야 한다.
