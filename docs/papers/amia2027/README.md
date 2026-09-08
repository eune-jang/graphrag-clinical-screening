# AMIA 2027 — 제출 당시 산출물 index

> **최종 갱신**: 2026-09-08
> **목적**: **AMIA 제출 당시의 결과**와 **post-AMIA 전건 판정 결과(113건)** 를 명확히 분리한다.
> **이 문서는 index다.** 아래 파일들은 참조가 많아 **이동하지 않았다** — 원래 위치에 그대로 있다.

---

## 1. 왜 분리가 필요한가

AMIA 초록은 **74-item 시점**의 결과로 제출되었다. 그 뒤 판정이 계속되어 113건으로 확대되었다.

두 숫자는 **경쟁하는 진실이 아니라 서로 다른 시점의 스냅샷**이다.
`docs/amia_stage1_numbers.md`처럼 파일명에 버전이 없는 생성물이 조용히 113으로 덮어써지면,
초록에 실린 숫자를 다시 추적할 수 없게 된다.

> **이번 단계에서 74-item 숫자 문서를 113-item으로 재생성하지 않는다.**
> 최신 113-item 상태는 [`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md)에서만 요약한다.

---

## 2. 계보 — 61 → 74 → 113

criterion_id 집합이 **완전히 중첩**한다(실측 확인).

```
AMIA_2027_STAGE1_GOLD_61items_2026-09-01/   60 gold + 1 gap ticket   선행본(불완전)
        ⊆
AMIA_2027_STAGE1_GOLD_61items_2026-09-02/   61 gold · 0 gap · S1 36 + S4 25
        ⊆
AMIA_2027_STAGE1_GOLD_74items_2026-09-03/   74 gold · 0 gap · S1 49 + S4 25   ← AMIA 제출 시점
        ⊆
evidence/stage1/adjudication_v1_2_2_2026-09-07/   113 gold · 0 gap · S1+S2+S3+S4
```

113 − 74 = **39건** (S2 35 + S3 4).

`61items_2026-09-01`은 `WITH_TEXT` `.txt` 1개가 누락된 4파일 선행본이며 09-02가 이를 대체한다.
**셋 다 삭제하지 않는다.** 113이 최신이라는 것은 삭제 사유가 아니다.

---

## 3. AMIA 제출 시점 산출물 (historical snapshot — 갱신하지 않음)

| 경로 | 내용 | 기준 시점 | git |
|---|---|---|---|
| `AMIA_2027_STAGE1_GOLD_61items_2026-09-01/` | 60 gold + 1 gap, 4 files | 09-01 | 추적 |
| `AMIA_2027_STAGE1_GOLD_61items_2026-09-02/` | 61 gold, 0 gap | 09-02 | 추적 |
| `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/` | **74 gold, 0 gap — 제출본** | 09-03 | 추적, tag `amia2027-stage1-gold-74items-20260903` |
| `docs/amia2027_gold_freeze_2026-09-02.md` | 61건 freeze 기록 | 09-02 | 추적 · **immutable** |
| `docs/amia2027_gold_freeze_2026-09-03.md` | 74건 freeze 기록 | 09-03 | 추적 · **immutable** |
| `docs/amia_stage1_numbers.md` | 초록 숫자 (**74-item 기준**) | 09-03 | 추적 · generated · **stale** |
| `docs/amia_stage1_trajectories.md` | Table 1 R1→R2 궤적 (**74-item 기준**) | 09-03 | 추적 · generated · **stale** |
| `docs/amia2027_work_summary.md` | 연구 상태 서술 (표본 funnel, 영역별 상태) | 09-03 | 추적 |
| `AMIA_ABSTRACT_EVIDENCE_PACK.md` (저장소 루트) | 초록 근거 감사 기록. 08-24 감사 + 09-03 재감사 | 09-03 | 추적 |
| `AMIA_2027_ABSTRACT_REVIEW_BUNDLE_2026-08-24.zip` (루트) | 리뷰용 번들 (evidence pack + IAA json + 큐 + 코드) | 08-24 | **미추적** |

`amia_stage1_numbers.md` / `trajectories.md`는 **generated**이지만, 지금은 **AMIA 제출 시점의
historical snapshot 역할**을 겸하고 있다. 이것이 이번 단계에서 재생성하지 않는 이유다.

---

## 4. Post-AMIA 최신 상태

| 경로 | 내용 |
|---|---|
| `evidence/stage1/adjudication_v1_2_2_2026-09-07/` | **canonical frozen evidence** — 113 gold / 0 gap / 8 trials |
| `STAGE1_GOLD_113items_2026-09-07/` | 동일 payload의 artifact discovery 사본 |
| `docs/CURRENT_STATUS.md` | 113-item 수치 요약 (여기서만 최신 상태를 서술) |

파일명에서 `AMIA_2027_` 접두어가 빠진 것은 초록 제출이 끝났기 때문이며,
**AMIA 전용 산출물에는 AMIA 명칭을 유지하는 것이 정상**이다.
`scripts/amia_stage1_*.py`의 이름도 그대로 둔다 — 일반화 여부는 별도 판단이 필요하다.

---

## 5. 향후 이 디렉터리를 실제 저장 위치로 쓸 경우

`docs/papers/amia2027/frozen_submission/` 같은 구조로 실제 이동하려면 **먼저 참조를 정리해야 한다.**
현재 이동하지 않은 이유:

- `docs/amia_stage1_numbers.md`는 8곳에서 참조된다 — 그중 `docs/amia2027_gold_freeze_2026-09-02.md`와
  `-03.md`는 **immutable**이라 링크를 고칠 수 없다.
- `docs/amia2027_gold_freeze_2026-09-03.md`도 6곳에서 참조된다(같은 문제).
- 즉 이동하면 **동결 문서 안의 링크가 깨지고, 그 문서를 고칠 수 없다.**

이동보다 이 index로 가리키는 편이 안전하다.

---

## 6. 해석 주의

- 전체 코퍼스 어노테이터 κ(=0.650, n=172)와 판정 강화 부분집합의 gold 대비 정확도는
  **서로 다른 것을 측정한다.** 같은 척도처럼 나란히 비교하지 말 것.
- 113-item 판정은 **단일 blind pass**다. 2-pass revealed 판정으로 사후 서술하지 말 것.
- 기존 8개 IAA trial은 held-out Round 3으로 쓸 수 없다(어노테이터가 판정 과정에서 노출됨).
- 초록에 들어가는 숫자는 **생성하고, 옮겨 적지 않는다.**
