# results/ — generated output

> **이 디렉터리는 source of truth가 아니다.**
> `.gitignore`가 `results/*`를 제외하며, 이 README만 추적된다.
> 권위 있는 경로는 [`../docs/repository/SOURCE_OF_TRUTH.md`](../docs/repository/SOURCE_OF_TRUTH.md)를 본다.

## 내용과 재생성 방법

| 경로 | 재생성 |
|---|---|
| `iaa/round1/`, `iaa/round2/`, `iaa/round2_gold/` | `python scripts/compute_iaa.py --stage 1 --round {1,2}` |
| `iaa/iaa_stage1_report.md`, `iaa_stage1_disagreements.md` | 〃 |
| `adjudication/adjudication_queue.{json,csv}` | ⚠️ **재생성 불가** — 아래 참조 |
| `adjudication/tier0_violations.csv` | `python scripts/tier0_check.py --round 2 --out results/adjudication` |
| `nsclc_*.xlsx` (표본틀·후보 선정) | `notebooks/01_aact_nsclc_sampling_frame.py`, `02_protocol_selection.py` |
| `review_log_*.xlsx`, `review_*.xlsx` | `python pipeline/review_session.py --trial <NCT>` |

## ⚠️ adjudication_queue.json 은 재생성 불가

`scripts/build_adjudication_queue.py`는 실행할 때마다 **S4 감사표본을 재추첨**한다.
시드는 고정이지만 표본틀은 고정이 아니며, 이 표본은 논문 Methods에 보고된다.
따라서 이 파일을 잃으면 판정에 실제로 쓰인 작업목록을 복원할 수 없다.

exact 사본이 아래에 동결되어 있다:

```
evidence/stage1/adjudication_v1_2_2_2026-09-07/queue/adjudication_queue.json
  sha256 a42b471c36c5f155d28e64b65b8e768c3e74c71e43edba03d61e1a27a2f427c8
```

작업 **순서만** 바꾸려면 `scripts/reorder_adjudication_queue.py`를 쓴다
(`priority` 열만 다시 쓰고 행 집합이 동일함을 assert한다).

## 알아둘 것

- `iaa/round2_gold/`의 GOLD 대비 수치는 **74-item 시점**(2026-09-03)에 생성된 것으로, 현재 113-item
  증거집합과 다르다. 최신 상태는 [`../docs/CURRENT_STATUS.md`](../docs/CURRENT_STATUS.md)를 본다.
- 이 디렉터리의 마크다운 리포트에는 워크스페이스 **로컬 절대경로**가 기록된다. git 미추적이라 유출
  경로는 아니지만, 내용을 다른 곳으로 복사할 때는 확인한다.
- 여기 있는 숫자를 논문에 옮겨 적지 말 것. 초록 숫자는 동결 export에서 **생성**한다.
