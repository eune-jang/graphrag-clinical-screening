# 0001 — Stage 1 v1.3 method import

**date**: 2026-09-08
**status**: accepted
**normative or implementation-only**: **import record — normative artifact admitted, no implementation changed**

---

## problem

Stage 1 판정이 v1.2.2 기준표준으로 완료된 뒤, 후속 방법론 v1.3이 저장소 **밖에서** 설계되었다.
PHASE 1 감사와 PHASE 2 문서화는 두 산출물이 저장소에 **존재하지 않음**을 확인하고 기록했다
(파일명 검색 0건, `primary_rule_id`·`recursion_targets`·`TARGET_SEGMENTS` 등 0 파일, H0–H6 언급이 핸드오프 문서에만 존재).

그 상태에서는 두 가지가 불가능했다.

1. v1.3 규범을 인용할 수 없다 — 저장소 안에 근거 바이트가 없다.
2. "현행 규범"과 "historical 판정 기준"을 구분할 수 없다 — 구분할 대상 하나가 없기 때문이다.

## decision

두 외부 아티팩트를 **바이트 동일 사본**으로 반입하고, 저장소 파일명은 **버전은 유지하되 lifecycle 상태 접미사는 제거**한다.
코드는 변경하지 않는다.

### 반입 매핑

**external source identity ≠ repository canonical filename.** 매핑을 여기 기록한다.

| | Artifact A | Artifact B |
|---|---|---|
| **external source filename** | `stage1_v1_3_canonical_core_v1_3_0_FROZEN_2026-09-07.md` | `stage1_v1_3_llm_prompt_v1_3_1_DEV_2026-09-08_CORRECTED.txt` |
| **external source path** (반입 시점) | `/Users/jang-eunhye/stage1_v1_3_import/` | 동일 |
| **repository destination** | `docs/guidelines/stage1/canonical_core_v1_3_0.md` | `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt` |
| **size** | 29,944 bytes (535 lines) | 33,440 bytes (809 lines) |
| **SHA-256 before import** | `16e56569b7570acea8b50aaab82d31292d7421c8fe650fdbe960be1f09f0f0fe` | `dfce30245473b8f69627d5030cb772be3ef84f8e23957b09d170e6ac288590f9` |
| **SHA-256 after import** | `16e56569b7570acea8b50aaab82d31292d7421c8fe650fdbe960be1f09f0f0fe` | `dfce30245473b8f69627d5030cb772be3ef84f8e23957b09d170e6ac288590f9` |
| **byte-identical import** | **YES** (`cmp` 동일) | **YES** (`cmp` 동일) |
| **artifact role** | Stage 1 Canonical Core — 현행 Stage 1 방법론 규범 명세 | v1.3.0을 프롬프트로 구현한 개발용 아티팩트 |
| **normative status** | **NORMATIVE** (v1.3.0으로 동결) | **NON-NORMATIVE** (개발 아티팩트) |

외부 파일명의 `FROZEN` / `DEV` / `CORRECTED` / 날짜는 **lifecycle provenance**이므로 위 표에 보존한다.
저장소 파일명에는 넣지 않는다 — 상태는 변하고 파일명은 변하면 참조가 깨진다.
상태 선언은 파일 내용과 [`../guidelines/stage1/CURRENT.md`](../guidelines/stage1/CURRENT.md)가 담당한다.

### 반입 provenance

- **import date**: 2026-09-08
- **provided by**: project owner
- **source location/status at time of import**: **저장소 외부** (`/Users/jang-eunhye/stage1_v1_3_import/`, git 미추적)
- **외부 원본 처리**: 읽기 전용. 편집·개명·이동·재포맷하지 않았고 반입 후에도 원본 위치에 그대로 있다.
- **freeze author / approver**: **파일에 인코딩되어 있지 않다.** Canonical Core는 `Status: FROZEN normative specification (v1.3.0)`과
  freeze declaration을 담고 있으나 **동결 주체·승인자 이름은 없다.** DEV 프롬프트도 `Revised 2026-09-08 after review of the 09-07 draft`라고만 적혀 있고 검토자를 명시하지 않는다.
  추정하지 않는다.
- **내용 재구성 금지 준수**: 두 파일은 위 절대경로의 바이트만을 출처로 한다. 핸드오프 문서·대화·기존 요약에서 내용을 재구성하지 않았다.

## rationale / evidence

### 왜 두 층을 다른 권위로 두는가

Canonical Core는 스스로 이렇게 선언한다:

> H0–H6 hierarchy, X1–X7 cross-cutting rules, label semantics, split/merge boundaries,
> child-logic semantics, and criterion-locality rules are frozen in v1.3.0.

그리고 버전 정책에서 **v1.3.x 비규범 패치**(문구·예시·JSON 검증 세부)와 **v1.4 규범 변경**(H/X 의미·우선순위·경계·child-logic 동작)을 명시적으로 분리한다.

DEV 프롬프트는 스스로를 이렇게 규정한다:

> This file is a v1.3.1 DEVELOPMENT prompt (non-normative patch of the v1.3.0 baseline …).
> No H/X rule meaning changed.

즉 **둘의 권위 수준을 같게 두면 안 된다.** 프롬프트 문구 변경이 규범 변경으로 오인되거나, 그 반대가 되면
"최종 프롬프트 동결 후 모델 계열 간 비교" 설계 자체가 무너진다.

### 왜 코드를 함께 고치지 않는가

v1.3.0을 반입한다고 런타임이 v1.3을 따르게 되는 것은 아니다. 반입과 구현을 한 커밋에 섞으면
"규범이 도착한 시점"과 "구현이 따라간 시점"을 사후에 분리할 수 없다.
구현 격차는 [`../project_state/stage1_v1_3_implementation_gap.md`](../project_state/stage1_v1_3_implementation_gap.md)에 **재고 조사로만** 기록한다.

## relationship to historical 113-item evidence

**113-item historical gold ≠ v1.3-harmonized gold.**

113건은 아래 기준으로 생성된 증거다. 이 사실은 v1.3 반입으로 바뀌지 않는다.

- ontology v1.2.2
- ontology v1.2.3 alignment patch
- Stage 1 annotation guideline v1.2.2

Canonical Core 자신도 같은 경계를 긋는다:

> The frozen 113-item v1.2.2 evidence set should remain unchanged;
> any later v1.3-harmonized reference set should be versioned separately.

Canonical Core의 **legacy rule ID → v1.3 canonical-family 매핑표**는 분석·provenance recoding용이며,
historical record의 `rule_id`를 다시 쓰기 위한 것이 **아니다**. 원래 `rule_id`는 보존하고, 비교가 필요하면
파생 필드(`canonical_rule_family`)를 별도로 붙인다.

**historical 구현 앵커**: historical 판정 동작을 재현하려면 `iaa_pipeline/adjudication.py`의
**tag `stage1-adjudication-complete-2026-09-08` 시점 버전**을 쓴다.
작업 트리의 현재 파일은 Phase 4 이후 진화할 수 있으므로 영구 불변으로 선언하지 않는다.

## relationship to current runtime

**런타임은 아직 v1.3을 따르지 않는다.**

- `pipeline/prompts/prompt_1_splitting.txt`는 **변경하지 않았다.** 구 프로덕션 프롬프트이며,
  새 개발 프롬프트가 생겼다는 이유로 v1.3으로 재라벨하지 않는다.
- 반입된 DEV 프롬프트는 프로덕션 로더가 읽지 않는다. `pipeline/llm_client.py:86-93`의 `filename_map`과
  `iaa_pipeline/stage_runner.py:107-112`의 후보 경로는 **모두 명시적 파일명**이며 디렉터리를 glob하지 않는다.
  `pipeline/prompts/development/` 하위는 어떤 코드에서도 참조되지 않는다(검증 완료).
- 따라서: **development artifact imported; runtime activation deferred to Phase 4.**

## affected files

추가:
- `docs/guidelines/stage1/canonical_core_v1_3_0.md`
- `pipeline/prompts/development/stage1/stage1_prompt_v1_3_1.txt`
- `docs/decisions/0001-stage1-v1-3-method-import.md` (이 문서)
- `docs/project_state/stage1_v1_3_implementation_gap.md`

갱신(포인터·상태만):
- `docs/guidelines/stage1/CURRENT.md`
- `docs/repository/SOURCE_OF_TRUTH.md`
- `docs/CURRENT_STATUS.md`

변경하지 않음: 모든 historical basis 문서, 동결 증거, 61/74/113 스냅샷, 모든 실행 코드.

## backward compatibility

이 ADR 자체는 하위호환을 깨지 않는다 — 실행 경로에 아무것도 연결하지 않았기 때문이다.
호환성 위험은 Phase 4에서 발생하며, 목록은 gap inventory의 "Storage and Execution Contract Inventory"에 있다.

가장 큰 항목 하나를 여기 남긴다: `pipeline/validators.py:59-61`의
`nested_exception requires ≥2 sub_criteria (main+exception)` 규칙은 v1.3의
"sub_criteria는 exception span만 담는다"와 충돌하며, **historical 113 gold의 nested_exception 10건 중 9건
(sub_criteria 1개)을 거부한다.** 이 규칙은 gold와도, v1.3과도 어긋나 있다.
