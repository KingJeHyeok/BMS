# 초록 초안 (11-18)

2점 등록 확증 시험(Plett ESC 6셀, 커밋 cd29142) 결과를 반영했다(11-18). H4(< B1) 지지, H3(< 학습 보정) 지지 안 됨.
NCR18650B는 등록 온도보다 추운 표본이 10개뿐이라 확증 시험에서 뺐다(`final2_data_notes.md`).

## 국문

드론 스테이션에서는 귀환한 배터리의 충전 상태(SOC)를 착륙 직후 휴지 전압만으로 빠르게 추정할 수 있어야 한다.
비행 중 저가 센서로 적분한 전류는 오프셋과 용량 오차 때문에 표류하기 때문이다.
본 연구는 휴지 300 s의 전압과 주변 온도로 SOC를 추정하는 문제를 정의했다. 입력에는 저가 측정 체인 오차(이득·오프셋·잡음·양자화)를 넣었다.
이 문제에서 셀마다 실온 등록 시험 하나를 쓰는 단순 OCV 표 조회와, 다른 셀에서 학습한 잔차 보정 모델을 비교했다.
개발에는 공개 데이터 5종(셀 6개)을 썼다. 학습 보정 모델은 데이터셋 하나 빼기 교차검증에서 표 조회보다 MAE를 1.3 %p 줄였다(2.1 대 3.4 %p).
그러나 개발에 쓰지 않은 두 데이터셋(LG E66 1셀, Molicel P42A 12셀, 표본 1,365개)에서 모델을 미리 고정하고 한 번만 실행한 사전 등록 시험에서는 이득이 사라졌다(1.43 대 1.41 %p, 차이의 95 % 신뢰구간이 0을 포함).
원인을 분석한 결과, 이득은 거의 전부 저온 전압 강하의 보정에서 나왔다. 저온 강하의 크기는 셀마다 달랐는데(−20 °C에서 SOC 편향 −6.6 대 −3.3 %p), 학습 셀끼리는 서로 비슷해서 교차검증이 이 차이를 드러내지 못했다.
이를 바탕으로 학습 없이 25 °C와 0 °C 등록 시험 두 개를 온도로 내삽하는 2점 등록 조회를 제안했다. 개발 데이터에서는 학습 보정과 같은 오차를 냈다(1.91 대 1.93 %p). 학습 보정이 실패한 E66 셀에 사후 적용하자 MAE가 1.81에서 1.34 %p로 줄었고, −20 °C 편향은 +3.2에서 −0.2 %p로 줄었다.
다른 연구실의 셀 6개(−25 ~ 45 °C)로 사전 등록한 확증 시험에서, 2점 등록 조회의 MAE는 25 °C 표 조회보다 2.7 %p 낮았다(5.2 대 8.0 %p, 95 % CI [1.1, 4.4]). 학습 보정과의 차이(5.2 대 5.8 %p)는 유의하지 않았다.
−15 ~ 15 °C에서는 2점 등록이 가장 정확했다. 그러나 저온 등록보다 20 °C 더 추운 −25 °C에서는 모든 방법의 오차가 14 %p를 넘었다.
예측 1건은 2–5 ms로 서버 탑재 조건(100 ms)을 만족했다.
결과는 휴지 전압 SOC 추정에서 셀 고유의 저온 특성을 학습 모델이 다른 셀로 옮기기 어렵다는 것을 보인다. 운용에서는 셀별 등록 시험 설계가 모델 선택보다 중요하다.

**주제어:** 충전 상태 추정, 휴지 전압, 개방 회로 전압, 드론 스테이션, 교차 셀 일반화, 사전 등록 평가

## English

Drone battery stations need the state of charge (SOC) of a returning pack from the rest voltage right after landing, because current integration with low-cost sensors drifts with offset and capacity errors.
We estimate SOC from a 300 s rest-voltage trace and ambient temperature under a simulated low-cost measurement chain (gain, offset, noise, quantization). We compare open-circuit-voltage lookup on one room-temperature registration test per cell with a residual model learned on other cells.
On five public development datasets (six cells), the learned correction lowered leave-one-dataset-out MAE from 3.4 to 2.1 %p.
In a preregistered, single-run test on two unseen datasets (LG E66, 1 cell; Molicel P42A, 12 cells; 1,365 rests), the gain vanished: 1.43 vs 1.41 %p, with the paired 95 % CI including zero.
The development gain came almost entirely from correcting the low-temperature voltage drop. This drop is cell-specific (SOC bias at −20 °C of −6.6 vs −3.3 %p), and it was nearly identical across the development cells, so cross-validation could not reveal the variation.
We therefore propose a training-free two-point registration lookup that interpolates 25 °C and 0 °C registration tables in temperature. It matches the learned model on development data (1.91 vs 1.93 %p). Applied post hoc to E66, where the learned model failed, it reduced MAE from 1.81 to 1.34 %p and the −20 °C bias from +3.2 to −0.2 %p.
In a preregistered confirmatory test on six cells from another laboratory (−25 to 45 °C), two-point lookup reduced MAE versus room-temperature lookup by 2.7 %p (5.2 vs 8.0 %p, 95 % CI [1.1, 4.4]), but did not differ significantly from the learned model (5.2 vs 5.8 %p). It was the most accurate method from −15 to 15 °C, while all methods exceeded 14 %p error at −25 °C, 20 °C below the low registration point.
Inference takes 2–5 ms per prediction.
For rest-voltage SOC estimation, per-cell registration design matters more than the choice of learned model.

## 메모
- 수치 출처: `results.md`(dev 2.11·3.40), `final_results.md`(1.434·1.410), `b1_gap.md`(−6.57·−3.31), `two_point_dev.md`(T2_cold 1.91, r = 300), `two_point_e66.md`(사후, 0 °C 제외 1.34 대 1.81), `final3_results.md`(확증 5.23·5.80·7.97), `paper_outline.md` 6.6(지연).
- T2_cold는 dev에서 변형 4개(T 선형, 1/T, w 자르기, 따뜻한 쪽 외삽 안 함) 중 골랐다. 본문에 밝힌다.
- 초록 길이: 국문 약 1,000자, 영문 약 230단어. 투고처 규정(보통 150–250단어)에 맞춰 줄인다.
