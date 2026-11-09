# autoresearch (T1 귀환 SOC)

이 폴더는 알고리즘 개선 루프 전용 작업 공간이다. 세션을 시작하면 `program.md`를 읽고 그 루프를 따른다.

- 고칠 파일은 `estimator.py` 하나다. 진행은 `python -I eval/run.py`가 `improved`로 판정한 커밋으로만 센다.
- 계속할지 묻지 않는다. 사용자 입력이 필요 없는 일은 끝까지 하고 한 번에 보고한다.
- 감사·문헌 조사는 서브에이전트(`leakage-auditor`, `lit-scout`)에게 맡긴다.
- 배경(왜 T1인가): `C:\BMS\reports\` 연구 설계서 v3, 시나리오 S.
