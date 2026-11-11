# 최종 테스트용 공개 데이터셋 후보 (11-11 조사)

조건: (1) 여러 SOC에서 휴지 ≥300 s, 휴지 첫 60 s를 1 s 이하로 기록 (2) 25 °C 외 온도, 같은 셀 (3) 25 °C 등록 시험(HPPC·펄스 OCV·GITT)
(4) 전류·용량 시험으로 기준 SOC 계산 가능 (5) 공개. 샘플링은 README가 아니라 실제 파일로 확인했다.

## 추천

| 순위 | 데이터셋 | 셀 | 온도 (°C) | 휴지 (실측 확인) | 1–5 | 크기·라이선스 |
|---|---|---|---|---|---|---|
| 1 | **LG E66 (Porsche Taycan 셀)**, McMaster, Borealis doi:10.5683/SP3/7JP3NM | 65 Ah 파우치 NMC | −20, −10, 0, 10, 25, 40 | GITT: 0.3C 방전 뒤 2 h 휴지 × 14 SOC, **실제 1 s**. HPPC 1 h 휴지는 10 s, 10 min 휴지는 처음 50 s만 1 s | 전부 충족 | 셀 zip 152 MB, CC BY 4.0 |
| 2 | **Molicel INR21700-P42A**, Stanford (Khan·Onori, Sci Data 2025), OSF doi:10.17605/OSF.IO/9CEAV | 4.2 Ah NMC/Si-Gr, **셀 12개** | 5(표면 온도 11.7–13.8 → 실제 ≈12?), 25, 40 | C/5 방전 뒤 1 h 휴지 × 9 SOC, 펄스 뒤 30 min, **실제 1 s** | 2만 부분(≤0 °C 없음) | HCGT .mat 온도당 16 MB, CC BY 4.0, 다운로드 느림 |
| 3 | **Univ. Malaya NCR18650B / VTC6**, Mendeley doi:10.17632/29kw38kzwj.1 | NCA 18650 (VTC6는 NMC) | −5, 5, 25(파일 안에서는 30 °C로 표기), 45 | 0.4C 방전 뒤 30 min 휴지 × 10 SOC, 실제 1 s (25*·5 °C 확인) | 표기 오류 확인 필요 | RAR5 103 MB, CC BY 4.0 |

보조(실제 팩 확인용): **NASA HIRF Edge 540** — 직렬 LiPo 팩, 200 Hz, 비행 같은 부하 뒤 휴지 4.5–15 min. 하지만 SOC는 약 40–50 % 하나뿐이고 온도 변화와 OCV 시험이 없음.

## 탈락 (주 사유)
- 휴지 기록이 성김: Tesla 2170·SB LiMotive(McMaster, 1 h 휴지 60 s·10 s, 1 Hz로 보간됨), Stroebl Samsung 50E(10 s), CMU eVTOL(30 s), HNEI 이완 벤치마크(5 s), KIT LG HG2(2 s, 쓰고 있는 셀과 같은 모델)
- 25 °C 시험만 있음: Imperial LG M50T, Chen 2020 LG M50, Turku, RWTH, 4TU 35E
- 중간 SOC 휴지 없음: TU Berlin M50LT, Pozzato M50T, Catenaro·Onori
- 공개 안 됨 또는 접근 막힘: Aalborg Zheng(제한), Bayreuth, mediaTUM, Michigan Mohtat
- 드론 실비행: DJI M100(착륙 뒤 기록 끊김), KIOS M300(휴지 없음)

## 주의
- 추천 3개 모두 휴지 직전 전류가 작음(C/5–0.4C). 비행 부하(수 C) 뒤보다 과전압이 작아서 실제보다 쉬운 시험일 수 있음.
- McMaster 계열의 "1 Hz"는 보간일 수 있음 → dev 데이터도 영향 받음 (backlog 참고).
