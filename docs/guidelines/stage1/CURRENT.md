# Stage 1 — 규범 문서 index / precedence

> **최종 갱신**: 2026-09-08
> 이 문서는 **index**다. 실제 가이드라인·스펙 파일은 원래 위치(`pipeline/schema/`)에 그대로 있다.
> 여기서는 "무엇이 어떤 지위인가"만 정의한다.

---

## 1. Historical adjudication normative basis

113-item Stage 1 판정은 **아래 셋을 기준으로** 수행되었다. 이 조합이 판정의 기준표준이다.

| 지위 | 문서 | 비고 |
|---|---|---|
| ontology base | [`pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md`](../../../pipeline/schema/ontology_full_specification_unified_v1_2_2_ko.md) | **v1.2.2** 본문 |
| ontology alignment patch | [`pipeline/schema/ontology_spec_v1_2_3_patch.md`](../../../pipeline/schema/ontology_spec_v1_2_3_patch.md) | **v1.2.3**. 본문에 **미병합** — 위 문서와 **반드시 함께** 읽는다 |
| Stage 1 annotation guideline | [`pipeline/schema/annotation_guideline_v1_2_2_notion.md`](../../../pipeline/schema/annotation_guideline_v1_2_2_notion.md) | **v1.2.2 판정 동결본**. 규칙 ID(`§1-1`, `§T2-3`, `§C1-1` …)의 출처, 부록 3이 색인 |

세 문서 모두 **immutable**이다. 판정 중 발견된 개정 필요 사항은 문서를 고치는 대신
판정 기록의 `rule_status=conflict` / `gap`으로 남겼다.

v1.2.3 패치에서 가장 자주 문제되는 두 가지:

- **변경 1** — `child_logic`이 `composite_split`과 `macro_aggregate` **양쪽 모두**에 필수. 기본값 생략 없음.
- **변경 6** — `text_span`이 문자열이 아니라 **인접 구간의 배열**.

---

## 2. Latest frozen evidence

**113-item Stage 1 adjudication set** — [`evidence/stage1/adjudication_v1_2_2_2026-09-07/`](../../../evidence/stage1/adjudication_v1_2_2_2026-09-07/)

113 gold / 0 gap / 8 trials. 수치와 해시는 [`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) §3.

---

## 3. 반드시 지켜야 할 경계

> - **113-item set은 v1.3에 맞춰 정렬된(v1.3-harmonized) gold가 아니다.**
> - **Canonical Core v1.3.0은 아직 이 저장소에 반입되지 않았다.**
> - **v1.3 development prompt도 아직 반입되지 않았다.**
> - **향후 v1.3이 도입되어도 historical record를 다시 쓰지 않는다.**

이 경계가 중요한 이유: 기존 규칙으로 해소된 항목과 v1.3이 새로 추가한 규칙으로 해소된 항목이
구분 가능해야 한다. historical record를 v1.3으로 마이그레이션하면 그 구분이 사라지고,
"v1.3이 무엇을 개선했는가"를 증거로 말할 수 없게 된다.

v1.3이 도입될 때는 **새 날짜의 별도 evidence 디렉터리**를 만든다. 이 디렉터리를 고치지 않는다.

---

## 4. 버전 계보 — 무엇을 인용할 것인가

| 문서 | 지위 | 인용 |
|---|---|---|
| `annotation_guideline_v1_2_2_notion.md` | **현행 동결본** | ✅ **이것을 인용한다** |
| `annotation_guideline_v1_2_1.md` | superseded (2026-08-25 동결) | 규칙 내용 동일, **규칙 ID 없음** → v1.2.2로 인용 |
| `annotation_guideline_v0_2_stage1 (1).md` | legacy v0.2 (2026-05-11) | ❌ 인용 금지. §6 경고 참조 |
| `stage1_iaa_review_and_guideline_v1_1.md` | Round 2 IAA 검토 기록 | 가이드라인 본문 **아님** |
| `ontology_full_specification_unified_v1_2_2_ko.md` | **현행 온톨로지 본문** | ✅ v1.2.3 패치와 **함께** |
| `ontology_spec_v1_2_3_patch.md` | **현행 정합성 패치** | ✅ 위와 함께 |
| `ontology_full_specification_v1.2.1.md` | superseded | lineage 용도 |
| `ontology_v1.2.1.json` | **dead reference** | ❌ authoritative 아님 — enum 정본은 `pipeline/config.py` |

> ⚠️ **파일명 함정**: v1.2.2 가이드라인의 정본은 `_notion` 접미사가 붙은 파일이 **유일본**이다.
> "Notion 사본이니 부차적"이라고 오해하지 말 것. 접미사 제거 rename은 참조 스캔 없이 하지 않는다.

---

## 5. 판정 방법 — 보존해야 할 것

판정은 다수결도 어노테이터 합의도 아니다. 증거 위계에 근거한 **정오 판단**이다.

```
Tier 0  온톨로지/스펙의 구조적 제약만으로 결정
Tier 1  외부 임상 권위
Tier 2  CRC / 운영 스크리닝 로직
Tier 3  미해결 → gap ticket (억지로 gold로 만들지 않는다)
```

- 어노테이터 일치가 정답을 뜻하지 않는다. 둘 다 틀릴 수 있다 → 일치 항목도 감사했다.
- 113-item set에는 Tier-3 gap이 **0건** 남았다.
- 판정은 **단일 blind pass**로 수행되었다([`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) §3).

---

## 6. 알려진 stale pointer — 미해결

`pipeline/REVIEW.md:368`과 `pipeline/REVIEW_notion.md:433`이
`schema/annotation_guideline_v0_2_stage1 (1).md`를 **"annotation guideline (현재 stage 1)"** 으로
가리키고 있다. **v0.2는 현재 Stage 1 가이드라인이 아니다** — §1의 v1.2.2가 맞다.

`iaa_pipeline_spec/streamlit_status_and_gaps_2026-08-25.md`도 이 파일을 "⛔ 구버전(v0.2), 혼동 위험"으로
이미 표시하고 있다.

이 포인터를 고치는 것은 리뷰어가 실제로 참조할 문서를 바꾸는 일이라 **사람 승인 대기 중**이다.
그때까지 이 index가 우선한다.

---

## 7. 관련 문서

- [`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) — 진행 상태, 최신 수치, known drift
- [`../../repository/SOURCE_OF_TRUTH.md`](../../repository/SOURCE_OF_TRUTH.md) — 권위 우선순위 전체 표
- [`iaa_pipeline_spec/adjudication_guide_v2_over_v1.md`](../../../iaa_pipeline_spec/adjudication_guide_v2_over_v1.md) §2-0 — 판정자용 기준표준 정의
- [`iaa_pipeline_spec/adjudication_handover.md`](../../../iaa_pipeline_spec/adjudication_handover.md) — 판정 설계 근거
