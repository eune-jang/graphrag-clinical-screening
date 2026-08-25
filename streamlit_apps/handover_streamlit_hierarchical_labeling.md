# handover: Streamlit Stage 1 계층 라벨링 개편

**목적**: Stage 1 annotation 앱을 단층 구조에서 **재귀 계층 구조**로 개편. 혼합 로직 문장(예: A AND (B1 OR B2))을 계층별로 라벨링할 수 있게 하고, guideline v1.2의 text_span 세그먼트 배열·substring 검증을 UI에 반영.

**작업 전 필독**:
- `pipeline/schema/annotation_guideline_v1_2.md` — 특히 "판단 순서"(재귀 ④), "Text_span 작성 원칙", "child_logic 표기"
- `ontology_spec_v1_2_3_patch.md` — 변경 6 (text_span 배열화)
- `validators.py` — validate_prompt1 (저장 시 검증과 정렬 필요)
- 기존 Streamlit 앱 코드 전체 (구조 파악 후 아래 요구사항을 기존 코드에 맞게 적용. 화면 위젯은 최대한 재사용하고 전면 재작성하지 말 것)

---

## 1. 핵심 설계: 작업 큐 모델

**원칙: 한 화면 = 한 항목 = 한 계층의 splitting 판정.** 중첩 트리를 한 화면에 그리지 않는다 (annotator마다 입력 깊이가 달라져 IAA 잡음 발생).

```
동작 흐름:
1. 큐에서 항목 pop → 판정 화면 표시
2. annotator가 splitting_decision + (split이면) child 조각들 입력 → 저장
3. 저장 시:
   - composite_split / macro_aggregate → 각 child를 새 항목으로 큐에 push
   - nested_exception → main 조각만 새 항목으로 push (예외 조각은 push 안 함, §4)
   - none → leaf 확정, push 없음
4. 큐가 빌 때까지 반복
```

- **큐 순서는 DFS** (child를 parent 바로 다음에 배치). annotator가 문맥을 유지한 채 하위 판정을 이어가도록.
- 모든 child는 예외 없이 큐에 들어간다. "더 나눌 것 같은 child만 선별 재투입"은 금지 — 재량이 다시 생김. 대부분의 child는 none 클릭 한 번으로 종료되므로 비용 낮음.

## 2. ID 체계 (필수)

경로 기반 계층 ID. child_id는 계층 내에서 a, b, c…이고, 전체 ID는 dot-join:

```
NCT..._I3          (루트 criterion)
NCT..._I3.a        (1차 child)
NCT..._I3.b
NCT..._I3.b.a      (2차 child — 이전 논의의 b1)
NCT..._I3.b.b      (2차 child — 이전 논의의 b2)
```

- ID는 저장 후 불변. IAA 짝짓기(EHJ vs DYK 항목 정렬)와 `parent_criterion_id`(Neo4j ingest의 IS_PART_OF 소스)가 이 ID에 의존.
- 각 항목 레코드에 `depth`(0부터), `parent_criterion_id`(루트는 없음) 저장.

## 3. 판정 화면 구성

기존 입력 위젯 재사용 + 아래 추가/변경:

**상단 컨텍스트 패널 (신규, 필수)**
- 루트 criterion 원문 전문 표시
- 현재 항목의 경로 breadcrumb (예: `I3 › b`)
- 현재 항목의 text_span 세그먼트를 원문 위에 **하이라이트**로 렌더링 (모든 세그먼트가 연속 substring이므로 가능 — v1.2 대원칙의 UI 활용). parent 체인의 스팬은 옅은 색, 현재 항목 스팬은 진한 색.

**text_span 입력 (변경)**
- child당 세그먼트 **배열** 입력: 세그먼트 추가/삭제 버튼, 각 세그먼트는 텍스트 입력
- **실시간 substring 검증**: 입력값이 루트 원문의 substring이 아니면 즉시 오류 표시(빨간 테두리 + "원문에 없는 문자열"). 저장 차단.
- 경계 soft-warning (저장은 허용, 경고만): 세그먼트가 리스트 마커("1)", "a.", "-")로 시작하거나 쉼표·세미콜론·마침표로 끝나면 노란 경고 "경계 규칙 확인: 선행 마커/후행 구두점 제외 원칙"
- 편의 기능: 원문 텍스트에서 드래그 선택 → 세그먼트로 추가할 수 있으면 이상적. Streamlit 기본으로 어려우면 st.text_input + 검증으로 충분 (선택 컴포넌트는 옵션).

**child_logic (변경)**
- composite_split / macro_aggregate 선택 시: **필수 입력** (AND/OR 라디오, 기본 선택 없음 — 명시 강제)
- nested_exception / none 선택 시: 필드 **비활성화** (입력 불가)

**cohort_scope**
- 선택 입력 (쉼표 구분 문자열 → 리스트). 비어 있으면 필드 자체를 저장 레코드에서 **생략** (null·빈 array 저장 금지 — v1.2 convention)

**notes**
- 기존 유지. IB 위임 케이스 등 "thresholds delegated to {문서}" 기록용.

## 4. nested_exception 특수 처리

- 조각 입력란 라벨을 "child"가 아니라 **main 조각 / 예외 조각(exception span)**으로 구분 표시
- 예외 조각은 트리거 표현("except" 등)부터 시작해야 함 — soft-warning으로 안내
- 저장 시: **main 조각만 큐에 push** (판단 순서 ②→③: 예외 분리 후 main에 남은 구조를 다시 판정. 대부분 none). **예외 조각은 push하지 않음** — child Criterion이 아니라 Stage 5 입력이며 Neo4j에서 INCLUDES_EXCEPTION relation으로 변환됨.
- child_logic 비활성화 (§3)

## 5. 저장 데이터 스키마

항목당 레코드 (flat list로 저장, 계층은 ID·parent로 표현):

```json
{
  "criterion_id": "NCT03800134_I3.b",
  "parent_criterion_id": "NCT03800134_I3",
  "depth": 1,
  "source_text": "<이 항목이 판정한 텍스트 = parent에서 물려받은 세그먼트 결합>",
  "splitting_decision": "macro_aggregate",
  "child_logic": "OR",
  "sub_criteria": [
    { "child_id": "a", "text_span": ["not a woman of childbearing potential (WOCBP)"] },
    { "child_id": "b", "text_span": ["a WOCBP who agrees to follow contraceptive guidance ..."] }
  ],
  "cohort_scope": ["C", "F"],
  "notes": ""
}
```

- `text_span`은 **항상 array of strings** (세그먼트 1개여도 배열)
- 기존 gold set(문자열 text_span, 단층)은 **마이그레이션 스크립트**로 변환: 문자열 → 1개짜리 배열, depth=0/parent 없음 부여. 원본 파일은 절대 덮어쓰지 말고 `_migrated` 사본 생성.
- 저장은 항목 단위 증분 저장 (중단 후 재개 가능해야 함 — 큐 상태 포함 세션 복원)

## 6. 저장 시 검증 (validators.py와 정렬)

- split 계열 → sub_criteria ≥ 2, 각 child 세그먼트 ≥ 1, 모든 세그먼트 substring 통과
- composite/macro → child_logic 필수
- nested_exception → main 1개 + 예외 조각 ≥ 1
- none → sub_criteria 없음
- 실패 시 저장 차단 + 필드별 오류 메시지
- `validators.py`의 validate_prompt1도 동일 규칙으로 갱신할 것 (text_span 배열 타입 검사, substring 검사 — 원문 텍스트를 인자로 받도록 시그니처 확장, child_logic 필수 검사)

## 7. 진행률·완료 정의

- criterion 완료 = 해당 루트의 모든 하위 항목이 저장되고 큐에 남은 자손이 없음
- 사이드바에 trial별 진행률: 루트 기준 완료 수 / 전체 + 큐 잔여 항목 수

## 8. 인수 테스트 (구현 후 이 3건으로 확인)

1. **KEYNOTE-671 I3 (혼합 로직, 2-pass)**: 1차에서 composite_split(AND, a·b) 저장 → b가 큐에 재등장 → 2차에서 macro_aggregate(OR, b.a·b.b) 저장 → a, b.a, b.b가 none으로 종료. 최종 flat list에 항목 5개(I3, I3.a, I3.b, I3.b.a, I3.b.b), leaf 3개.
2. **vitiligo 케이스 (nested_exception)**: main·예외 조각 저장 → main만 큐 재등장 → none 종료. 예외 조각은 큐에 나타나지 않음. child_logic 필드 비활성 확인.
3. **IB 위임 케이스**: "Adequate bone marrow reserve ... (please refer to IB)" → none + notes 입력만으로 종료. sub_criteria 강제 없음 확인.

추가로: 원문에 없는 문자열 입력 시 저장 차단, "1)" 시작 세그먼트에 경고 표시 확인.

## 9. 하지 말 것

- 기존 gold set 파일 덮어쓰기 (마이그레이션은 사본으로)
- 한 화면 중첩 트리 UI
- child_logic 기본값 자동 선택 (명시 강제가 목적)
- text_span 자동 정규화 (공백 정리, 따옴표 변환 등 — 원문 그대로가 원칙)
- 판정 화면 레이아웃 불필요한 변경 (annotator 재적응 비용)

## 10. 열린 결정 (구현과 무관하게 진행 가능, 기본값으로 구현)

- 기존 8개 trial 라벨의 재귀 재라벨링 여부: **기본값 = 하지 않음** (신규 trial부터 적용, 기존은 마이그레이션 사본 + 혼합 로직 케이스만 추후 수동 보정). 코퍼스 내 혼합 로직 빈도 조사 후 재결정 예정.
- IAA 계산의 계층 정렬 방식(`compute_iaa.py`): 이번 작업 범위 아님. 단, 이 스키마(경로 ID + depth)가 그 전제이므로 ID 안정성만 보장할 것.
