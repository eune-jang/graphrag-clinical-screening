# Decision records (ADR)

> 방법론적 결정을 **결정문 단위로** 남기는 곳. 2026-09-08 신설, 아직 비어 있다.

## 왜 필요한가

지금까지 결정 근거는 freeze 문서·핸드오버 문서·코드 주석에 흩어져 있다.
예를 들어 "cohort_scope는 표면형 유지"라는 결정은 `pipeline/schema/cohort_standard_unit_proposal_v0.md`
상단 인용구에만 있고, "child_logic을 composite/macro 양쪽 필수로" 결정은 v1.2.3 패치 본문에만 있다.
결정이 파일에 종속되면 그 파일이 superseded될 때 근거도 같이 묻힌다.

## 형식

파일명: `NNNN-kebab-case-title.md` (예: `0001-explicit-child-logic.md`)

각 결정문에 반드시 포함:

- **problem** — 무엇이 문제였는가
- **decision** — 무엇으로 결정했는가
- **rationale / evidence** — 근거. 가능하면 데이터·판정 기록 인용
- **date / status** — `proposed` / `accepted` / `superseded by NNNN`
- **affected files**
- **normative or implementation-only** — 규범(가이드라인/스펙) 변경인지, 구현만인지

마지막 항목이 핵심이다. **규범 변경은 새 guideline 버전을 요구하고, 구현 변경은 그렇지 않다.**

## 후보 주제 (아직 작성 전)

기존 문서에 흩어져 있는 결정들:

- explicit `child_logic` (v1.2.3 변경 1)
- segmented `text_span` (v1.2.3 변경 6)
- nested exception의 그래프 표현 — `INCLUDES_EXCEPTION`, 자식 Criterion 노드 아님
- gold vs gap ticket 정책 — 억지 라벨 대신 tier-3 gap
- 판정 증거 위계 (Tier 0–3)
- cohort_scope 표면형 유지 / per-child 배치
- `XOR` 제거 (30 trial에서 0회)
- 단일 blind pass 판정 설계

## 하지 말 것

- 결정문을 사후에 고쳐 쓰지 말 것. 바뀌었으면 새 번호를 만들고 이전 것을 `superseded by`로 표시한다.
- 이미 동결된 가이드라인/스펙 본문을 결정문으로 대체하지 말 것. 결정문은 **근거 기록**이지 규범 본문이 아니다.
