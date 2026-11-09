"""PreToolUse 가드: 잠긴 평가기·데이터·지시문 수정과 홀드아웃 접근을 막는다 (exit 2 = 차단)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKED = [ROOT / "eval", ROOT / "data", ROOT / ".claude", ROOT / "program.md", ROOT / "results.tsv",
          Path("C:/BMS/data")]
HOLDOUT = re.compile(r"holdout", re.I)
WRITE_OPS = re.compile(r"(>|>>|\btee\b|sed\s+-i|\brm\b|\bmv\b|\bcp\b|Set-Content|Out-File|Add-Content|"
                       r"Remove-Item|Move-Item|Copy-Item|open\(|write_text|\.write\(|checkout\s+--|restore\b)", re.I)
LOCKED_WORDS = re.compile(r"(eval[/\\]|data[/\\]|program\.md|results\.tsv|\.claude|BMS[/\\]data)", re.I)


def block(msg):
    print(f"[guard] 차단: {msg}. program.md 규칙: estimator.py만 고친다.", file=sys.stderr)
    sys.exit(2)


def under(p, roots):
    try:
        q = Path(p)
        q = (q if q.is_absolute() else ROOT / q).resolve()
    except Exception:  # noqa: BLE001
        return False
    return any(q == r.resolve() or r.resolve() in q.parents for r in roots)


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ev = json.load(sys.stdin)
    tool, inp = ev.get("tool_name", ""), ev.get("tool_input", {}) or {}
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        if under(inp.get("file_path", ""), LOCKED):
            block(f"잠긴 경로 수정 시도 {inp.get('file_path')}")
    elif tool in ("Read", "Grep", "Glob"):
        target = " ".join(str(inp.get(k, "")) for k in ("file_path", "path", "pattern"))
        if HOLDOUT.search(target):
            block("홀드아웃 데이터 접근")
    elif tool in ("Bash", "PowerShell"):
        cmd = inp.get("command", "")
        if HOLDOUT.search(cmd):
            block("홀드아웃 관련 명령")
        if re.search(r"\bpip\b|\bconda\b|uv\s+add|install", cmd, re.I):
            block("패키지 설치 금지")
        if re.search(r"git\s+(push|remote)|--no-verify", cmd):
            block("원격 git 작업 금지")
        if LOCKED_WORDS.search(cmd) and WRITE_OPS.search(cmd):
            allowed = re.fullmatch(r"\s*python\s+-I\s+eval/run\.py(\s+.*)?", cmd)
            if not allowed:
                block("잠긴 파일을 쓰거나 지우는 명령")
    sys.exit(0)


if __name__ == "__main__":
    main()
