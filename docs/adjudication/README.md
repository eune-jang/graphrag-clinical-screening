# Adjudication — 문서 index

> 판정 관련 문서는 역사적 이유로 `iaa_pipeline_spec/`에 있다. **파일을 옮기지 않았고**,
> 이 문서가 무엇을 어떤 순서로 읽어야 하는지만 정리한다.

## 읽는 순서

| # | 문서 | 역할 |
|---|---|---|
| 1 | [`iaa_pipeline_spec/streamlit_status_and_gaps_2026-08-25.md`](../../iaa_pipeline_spec/streamlit_status_and_gaps_2026-08-25.md) | **여기서 시작.** 구현 상태 vs 문서, 미해결 gap, 검증 로그 |
| 2 | [`iaa_pipeline_spec/adjudication_guide_v2_over_v1.md`](../../iaa_pipeline_spec/adjudication_guide_v2_over_v1.md) | 판정자용 가이드 **v2** + v1→v2 변경표. **§2-0이 기준표준을 고정**한다 |
| 3 | [`iaa_pipeline_spec/adjudication_handover.md`](../../iaa_pipeline_spec/adjudication_handover.md) | 설계 근거. §3 작업목록 A–D, §10 구현 기록 |
| 4 | [`iaa_pipeline_spec/audit_streamlit_v1.md`](../../iaa_pipeline_spec/audit_streamlit_v1.md) | **blinding 아키텍처 (누출 A1–A7). UI 코드를 건드리기 전에 필독** |
| 5 | [`../guidelines/stage1/CURRENT.md`](../guidelines/stage1/CURRENT.md) | 기준표준 문서 우선순위 index |
| 6 | [`../../evidence/stage1/adjudication_v1_2_2_2026-09-07/README.md`](../../evidence/stage1/adjudication_v1_2_2_2026-09-07/README.md) | 최신 동결 증거 번들 |

`adjudication_guide_v2_notion.md`는 2의 Notion용 축약 사본이다.

## 구현

| 경로 | 역할 |
|---|---|
| `iaa_pipeline/adjudication.py` | 판정 로직 — gold/gap/span/tier/검증. **113 gold를 생성한 코드** |
| `iaa_pipeline/streamlit_app.py` | 판정 UI (사이드바: Role = Adjudicator, Round = 2) |
| `scripts/build_adjudication_queue.py` | 층화 작업목록. ⚠️ 실행할 때마다 **S4 감사표본 재추첨** |
| `scripts/reorder_adjudication_queue.py` | 기존 큐의 **순서만** 변경 (행 집합 불변 assert) |
| `scripts/tier0_check.py` | tier-0 스펙 위반 위생 점검 |
| `scripts/export_adjudicated_dataset.py` | committed GOLD → 날짜별 동결 export + MANIFEST |
| `tests/test_adjudication.py` | 50 tests |

## 핵심 원칙

- 판정은 **다수결이 아니다.** 단일 판정자(`GOLD`)가 동결 기준표준에 대해 내리는 정오 판단이다.
- 어노테이터 일치가 정답을 뜻하지 않는다 → 일치 항목도 감사한다.
- 해소 불가 항목은 억지 라벨 대신 **tier-3 gap ticket**으로 남긴다.
- `record_type`이 export의 모든 줄에서 gold와 gap ticket을 구분한다.
- **blinding은 서명 수준에서 강제된다.** `render_adjudication_form_blind`는 `peer_records`를 받지 않고,
  blind pass 중에는 peer envelope을 **읽지 않는다**(숨기는 것이 아니다).

## 데이터 흐름 — 되돌아가지 않는다

```
iaa_workspace/{trial}/stage1/round2/          committed envelope (git 미추적, live source)
  → results/adjudication/adjudication_queue.json   층화 작업목록 (재생성 불가)
  → STAGE1_GOLD_{N}items_{date}/                   날짜별 동결 export + MANIFEST (sha256)
  → evidence/stage1/adjudication_v1_2_2_{date}/    동결 증거 번들 (+ queue + envelope 사본)
  → docs/amia_stage1_*.md                          동결 export에서 재계산한 숫자
```

모든 freeze는 **새 날짜 디렉터리**다. 기존 디렉터리를 수정하지 않는다.
