"""루프 유지 hook.
  SessionStart: results.tsv 현재 행 수를 기록한다.
  Stop: 목표 미달이고 이번 세션 run이 MAX_RUNS 미만이며 STOP 파일이 없으면 종료를 막는다(exit 2).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_RUNS, TARGET = 40, 3.0
MARK = ROOT / ".claude" / "session_start.txt"
TSV = ROOT / "results.tsv"


def rows():
    if not TSV.exists():
        return []
    lines = TSV.read_text(encoding="utf-8").splitlines()
    head = lines[0].split("\t")
    return [dict(zip(head, line.split("\t"))) for line in lines[1:] if line]


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ev = json.load(sys.stdin)
    if ev.get("hook_event_name") == "SessionStart":
        MARK.write_text(str(len(rows())), encoding="utf-8")
        return
    if (ROOT / "STOP").exists():
        return
    R = rows()
    start = int(MARK.read_text()) if MARK.exists() else len(R)
    done = len(R) - start
    best = min((float(r["primary_mae"]) for r in R if r.get("status") in ("baseline", "improved")
                and r.get("primary_mae")), default=99)
    if best <= TARGET or done >= MAX_RUNS:
        return
    # 안전장치: 직전 차단 이후 새 run이 하나도 없으면(막혀서 헛도는 경우) 종료를 허용한다
    state = ROOT / ".claude" / "loop_state.txt"
    last = int(state.read_text()) if state.exists() else -1
    if ev.get("stop_hook_active") and last == len(R):
        return
    state.write_text(str(len(R)), encoding="utf-8")
    print(f"[loop] 아직 종료 조건이 아니다: 이번 세션 run {done}/{MAX_RUNS}, 최고 {best:.3f} (목표 {TARGET}). "
          "program.md 루프의 다음 시도를 계속하라. 사람에게 묻지 마라.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
