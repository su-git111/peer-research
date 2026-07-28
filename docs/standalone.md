# Claude 없이 실행하기 (Standalone 모드)

Cowork는 두 가지 방식으로 돌릴 수 있습니다.

| 방식 | 실행 주체 | 특징 |
|------|-----------|------|
| **에이전트 모드** | Claude Code | 회고·계획을 "제안"하고, 논문을 요약하고, 대화로 조정. 판단이 필요한 일에 강함. |
| **독립 모드** | `cowork.py` (파이썬) | LLM 없이 결정론적으로 실행. 자동 스케줄에 적합. 무료·오프라인(논문 조회만 인터넷). |

두 모드는 **같은 마크다운 파일**을 읽고 씁니다. 섞어 써도 됩니다 (예: 자동은 독립 모드, 다듬기는 에이전트 모드).

## 무엇이 LLM 없이 되고, 무엇이 낮춰지는가

| 기능 | 독립 모드 동작 |
|------|----------------|
| 주간 회고 | 지난주 daily 파일에서 완료/미완을 **자동 집계** (LLM 불필요) |
| 미완 이월 | 어제 미완 항목을 오늘로 **자동 복사** (LLM 불필요) |
| 야간 계산 | 큐의 명령을 **그대로 실행**·로그·exit code 기록 (LLM 불필요) |
| 논문 모니터링 | Europe PMC API로 **최신 논문 목록**을 가져옴. 요약(LLM) 대신 제목·저자·날짜·링크 나열 |
| 대시보드 | 이미 순수 파이썬 |
| Top 3 제안·오전/오후/밤 배치 | 빈 칸으로 생성 → **사용자가 채움** (판단은 사람 몫) |

즉 "집계·실행·수집"은 자동, "판단·제안"은 사람이 채우는 스캐폴드로 남깁니다.

## 명령

```bash
python cowork.py daily      # 오늘 체크리스트 생성 (어제 미완 이월)
python cowork.py weekly     # 이번주 계획 생성 (지난주 회고 자동 집계)
python cowork.py night      # 큐 작업 실행 + 논문 조회 → 아침 리포트
python cowork.py close      # 완료 업무를 포트폴리오에 기록
python cowork.py dashboard  # 대시보드만 다시 생성
python serve.py             # 클릭 가능한 대시보드 (로컬 서버) — 체크박스를 눌러 저장
```

의존성은 **파이썬 표준 라이브러리만** 사용합니다(계산 데모 스크립트만 numpy). 이미 있는 파일은 덮어쓰지 않습니다.

## 클릭으로 체크하기 (인터랙티브 대시보드)

`python serve.py`(또는 봇 메뉴 **[6] 대시보드 열기**)를 실행하면 `http://localhost:8787` 에 대시보드가 뜨고, **체크박스를 클릭하면 해당 마크다운 파일의 `[ ]`↔`[x]` 가 바로 갱신**됩니다. 마크다운이 여전히 단일 소스이고, 서버는 클릭받은 파일·줄의 체크 문자만 바꿉니다(경로 traversal·비-md·잘못된 줄은 차단, 127.0.0.1 바인딩). 정적 파일(`dashboard.html`)로 그냥 열면 읽기 전용입니다.

## 자동 스케줄 (Windows 작업 스케줄러)

Claude 앱 없이, PC만 켜져 있으면(절전 중이면 깨워서) 자동 실행됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File schedule_setup.ps1
```

이 스크립트가 작업 3개를 등록합니다: **Cowork Weekly**(월 08:30), **Cowork Daily**(매일 08:45), **Cowork Night**(매일 23:35). 로그인 상태에서 실행되며 절전 시 `WakeToRun`으로 깨웁니다.

제거:
```powershell
powershell -ExecutionPolicy Bypass -File schedule_setup.ps1 -Remove
```

> 에이전트 모드의 Claude 스케줄과 독립 모드의 작업 스케줄러를 **둘 다** 켜면 하루 두 번 생성될 수 있습니다. 한쪽만 쓰세요.

## 야간 큐 · 논문 워치리스트

- `night/queue.md` 의 '실행 대기'에 밤에 돌릴 명령을 한 줄씩 추가하면 `night` 실행 시 처리됩니다. 삭제·전송 등 파괴적 명령은 자동 '보류'.
- `night/watchlist.md` 의 각 줄은 **Europe PMC 검색 쿼리**입니다. 정확도를 위해 구문은 큰따옴표로, 조건은 `AND`로 묶으세요. 예: `"spatial transcriptomics" AND niche`, `"CellCharter"`.
