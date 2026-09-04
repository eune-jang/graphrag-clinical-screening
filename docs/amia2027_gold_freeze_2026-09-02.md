# Stage 1 analytic gold freeze — 검증·수정 기록

> **작성일**: 2026-09-02
> **대상**: `AMIA_2027_STAGE1_GOLD_61items_2026-09-02/`
> **계기**: 외부 모델의 9/2 export 리뷰 코멘트 6항목에 대해 "이미 반영된 것 / 반영 필요한 것 / 잘못된 지적"을 구분
> **결론**: 6항목 중 **1건은 오진, 4건은 이미 반영 완료, 1건(manifest)만 실제 작업 필요**. 작업 도중 별건 버그 1건 발견·수정. Stage 1 analytic gold는 **freeze 가능 상태**
>
> ⚠️ **2026-09-03에 대체됨** — S1 층의 `s1_kind="new"` 13건이 추가로 판정되어 gold는 **74건**이 되었습니다. 초록에 인용할 숫자는 `docs/amia2027_gold_freeze_2026-09-03.md` / `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/`를 사용하세요. 이 문서는 09-02 시점의 검증·수정 기록으로 보존합니다(§1 `blind_label` 오진 반박, §3-3 `metrics.py` 버그 분석은 계속 유효).

---

## 0. 한눈에

| # | 리뷰 코멘트 | 판정 | 조치 |
|---|---|---|---|
| 1 | `blind_label`이 최종 gold와 같이 덮어써짐 → 9/1에서 원복 필요 | ❌ **오진** | 원복 안 함. MANIFEST에 provenance 설명 절 추가 |
| 2 | `NCT02075840_I6` `rule_id` = `§T3-2` → `§3-2` | ✅ 이미 반영 | — |
| 3 | `NCT01295827_E6` `escalate_pi` = true → false | ✅ 이미 반영 | — |
| 4 | `NCT02474355_E2` `§3-1, §T3-2` → `§3-1` | ✅ 이미 반영 | — |
| 5 | `NCT05756153_E5` `§T3-2` → `§3-1` | ✅ 이미 반영 | — |
| 6 | manifest를 61 gold / 0 gap으로 재생성 | ⚠️ **작업 필요** | export 스크립트 신규 작성 후 재생성 |
| — | (별건) `compute_iaa.py`가 GOLD 축에서 크래시 | 🐛 **버그** | `metrics.py` 수정 + 회귀 테스트 추가 |

리뷰어가 2–5를 "아직 남아 있다"고 본 이유: 리뷰 시점의 export 파일이 **09:25 생성본**이었고, 사용자가 그 이후 **09:31~09:38**에 workspace GOLD envelope을 수정했기 때문. 즉 수정은 이미 끝나 있었고 export만 stale이었음.

---

## 1. `blind_label` 지적이 오진인 이유

리뷰어 주장: *"1차 blind pass의 `blind_label`은 최종 정답을 바꿔도 영구 보존돼야 하는데, 9/2 export에서 몇몇 항목의 `blind_label`이 최종 gold와 같이 바뀌어 있다. 9/1 원본에서 복원하라."*

### 1-1. 근거 ① — 61건 전부 `pass = "blind"`

```
workspace 61 records → adjudication.pass: Counter({'blind': 61})
```

`revealed`(2차 공개) pass를 거친 record가 **0건**. 즉 "정답을 바꾼 2차 판정"이라는 사건 자체가 이 데이터셋에 존재하지 않음.

### 1-2. 근거 ② — 코드상 보존 시점은 revealed pass 저장 때뿐

`iaa_pipeline/streamlit_app.py:1303-1309`

```python
if blind:
    snapshot = _blind_snapshot(gold_draft)   # 1차: 지금 입력값이 곧 blind_label
else:
    snapshot = blind_label                    # 2차: 기존 blind_label 그대로 보존
```

blind 모드에서 다시 저장하면 `blind_label`이 갱신되는 것이 **설계 그대로의 동작**. `blind_label`이 immutable snapshot이 되는 것은 항목이 revealed pass로 넘어간 이후.

가이드 문구(`adjudication_guide_v2_over_v1.md:245` "1차에서 매긴 `blind_label`은 정답을 바꿔도 그대로 남음")는 **1차 → 2차 전이**를 전제한 서술이고, 1차 내부의 재작업을 금지하는 규정이 아님.

### 1-3. 근거 ③ — 9/1 시점에도 `blind_label == final`이었음

| 항목 | 9/1 blind | 9/1 final | 9/2 blind | 9/2 final |
|---|---|---|---|---|
| `NCT01295827_E6` | macro_aggregate | macro_aggregate | none | none |
| `NCT02075840_I6` | composite/OR | composite/OR | composite/AND | composite/AND |
| `NCT03728556_E5` | nested_exception | nested_exception | composite/OR | composite/OR |

리뷰어가 말한 "원래 blind"는 **별도 보존된 1차 의견이 아니라 그 시점의 gold 값 그 자체**. 9/1 export에서 `blind != final`인 record는 `NCT03728556_E17` 하나뿐이었고, 그것도 당시 gap_ticket이라 최상위 `splitting_decision`이 없어서 생긴 형식 차이였음.

### 1-4. 원복하면 안 되는 이유

- 없던 blind→final 델타를 **인위적으로 생성**하게 되어 D-3 분석이 오염됨
- `pass="blind"`인 record인데 `blind_label ≠ 최상위 gold`가 되어 **스키마 내부 모순** 발생
- `build_adjudication_seed`는 blind-pass record를 `existing_gold`로 seed하므로(`streamlit_app.py:211-213`) 복원된 `blind_label`은 **어디에서도 읽히지 않음**

### 1-5. 재발 방지

MANIFEST에 `blind → gold provenance` 절을 신설하여, 데이터셋 자체가 이 설계를 설명하도록 함. 향후 같은 오독이 반복되지 않게.

---

## 2. 이미 반영되어 있던 항목 (검증 완료)

09:25 export ↔ 현재 workspace 대조 결과, 리뷰어가 지적한 metadata 4건 + gap 전환 1건 모두 반영 완료 상태였음.

| 항목 | 09:25 export | 현재 workspace |
|---|---|---|
| `NCT02075840_I6` `rule_id` | `§T3-2` | `§3-2` |
| `NCT01295827_E6` `escalate_pi` | `true` | `false` |
| `NCT02474355_E2` `rule_id` | `§3-1, §T3-2` | `§3-1` |
| `NCT05756153_E5` `rule_id` | `§T3-2` | `§3-1` |
| `NCT03728556_E17` | gap_ticket | gold (`none / §3-1 / existing`), `gap_tickets.json = []` |
| `rule_status=conflict` | `NCT05756153_E6` 1건 | 동일 (설계 의도대로 유지) |

---

## 3. 실제 수행한 수정

### 3-1. export 재생성 스크립트 신설 — `scripts/export_adjudicated_dataset.py`

기존 export는 ad-hoc으로 만들어져 재현 불가능했음. 스크립트화하여 freeze를 재현 가능하게 만듦.

- 입력: `iaa_workspace/*/stage1/round2/GOLD_*_committed.json` + `gap_tickets.json` + `stage1/input.json`
- 출력 2종:
  - **plain** — 저장된 record를 verbatim 그대로. workspace와 clean diff가 되는 provenance 사본
  - **WITH_TEXT** — 원문(`criterion_text` / `criterion_type` / `protocol_ref` / `source_order`) join + 생략된 `needs_recursion`을 명시적 `false`로 기록한 리뷰용 사본
- `record_type`으로 gold와 tier-3 gap ticket을 라인 단위로 구분 → 미해결 gap을 확정 gold로 오인할 수 없음
- 내장 검증: 중복 criterion_id · 원문 매칭 누락 · **text_span 세그먼트가 `criterion_text`의 verbatim 연속 부분문자열인지**(v1.2.3 변경 6 배열형 대응)
- `--strict`: 검증 문제 발생 시 non-zero exit

```bash
python scripts/export_adjudicated_dataset.py --strict
```

### 3-2. MANIFEST 재생성 (61 gold / 0 gap)

sha256을 포함하고, 위 §1-5의 provenance 절을 담음.

### 3-3. 🐛 `metrics.py` — GOLD 축 κ 계산 크래시 수정

```
AttributeError: 'list' object has no attribute 'lower'   # metrics.py  _span_tokens
```

- **원인**: `_span_tokens`가 `text_span`을 문자열로 가정. 그러나 spec **v1.2.3 변경 6**으로 GOLD envelope의 `text_span`은 **연속 세그먼트 배열**로 저장됨
- **영향 범위**: annotator 쌍(EHJ×DYK, 양쪽 다 문자열)은 정상 동작했으나, **GOLD가 포함된 모든 쌍이 예외로 중단** → E-G / D-G κ를 애초에 산출할 수 없는 상태였음. 리뷰 대응 중 처음 발견
- **수정**: 기존 공용 헬퍼 `iaa_pipeline.adjudication.normalize_text_span`을 경유하도록 변경. 배열의 세그먼트들은 **하나의 span의 조각**이므로 token set을 union으로 합침
- **회귀 테스트**: `tests/test_iaa_metrics.py::test_split_degree_handles_array_text_span` 추가 — 문자열형 ↔ 배열형이 섞인 쌍에서 `span_alignment_f1 == 1.0`인지 확인
- 테스트: `test_iaa_metrics.py` **39/39**, `test_adjudication.py` **50/50** 통과

### 3-4. 초록 숫자 재계산 스크립트 신설 — `scripts/amia_stage1_numbers.py`

**live workspace가 아니라 frozen export에서** 숫자를 뽑음. 초록 숫자와 데이터셋이 항상 같이 움직이도록 강제.

```bash
python scripts/amia_stage1_numbers.py --out docs/amia_stage1_numbers.md
```

---

## 4. Freeze 산출물

`AMIA_2027_STAGE1_GOLD_61items_2026-09-02/`

| 파일 | sha256 |
|---|---|
| `AMIA_2027_STAGE1_ADJUDICATED_61items_2026-09-02.jsonl` (+`.txt`) | `fcbbdae547d0265f…` *(§4-1 재생성분, 최신값은 MANIFEST.txt 참조)* |
| `AMIA_2027_STAGE1_ADJUDICATED_61items_WITH_TEXT_2026-09-02.jsonl` (+`.txt`) | `aaf9ffbacbec8c58…` *(§4-1 재생성분, 최신값은 MANIFEST.txt 참조)* |
| `MANIFEST.txt` | — |

검증: **61 gold / 0 gap · 8 trials · span violations 0 · 중복 ID 0 · 원문 미매칭 0**

09:25 stale export 대비 변경분은 예상과 정확히 일치 — rule_id 3건, `escalate_pi` 1건, `adjudicated_at` 6건, `blind_label` full-snapshot 4건. 그 외 57건은 동일.

### 4-1. 재생성 이력

| 시각 | 계기 | plain sha256 | WITH_TEXT sha256 |
|---|---|---|---|
| 09:50 | 최초 freeze (리뷰 코멘트 §2 반영분) | `7e8fc28bc1f7571d…` | `5760f3540cba65ca…` |
| **10:12** | **`NCT03728556_E5` child a에 예외절 span 추가** | **`fcbbdae547d0265f…`** | **`aaf9ffbacbec8c58…`** |

10:12 변경 내용 — child a `text_span`이 1개 → 2개 세그먼트:

```
+ "Participation in the overall survival follow-up of a study is allowed"
```

`needs_recursion=true` / `recursion_note`로 재귀 판정 대상임을 이미 표시해 둔 branch에, 예외절 원문 위치를 span으로 명시한 것. `splitting_decision`(composite_split) / `child_logic`(OR)은 불변이므로 **§5의 κ·outcome 숫자는 변하지 않음**. span verbatim 검증 통과 (2개 세그먼트 모두 `criterion_text`의 연속 부분문자열).

### 데이터셋 구성

| 축 | 분포 |
|---|---|
| record_type | gold 61 / gap_ticket 0 |
| queue stratum | S1 36 · S4 25 |
| tier | 0→3 · 1→2 · 2→56 |
| criterion type | exclusion 39 · inclusion 22 |
| gold `splitting_decision` | none 34 · composite_split 21 · nested_exception 4 · macro_aggregate 2 |
| `rule_status` | existing 51 · new 9 · conflict 1 |
| `escalate_pi=true` | 3 (`NCT02125461_I2`, `NCT03728556_I3`, `NCT05756153_E6`) |
| `adjudication.pass` | blind 61 |

---

## 5. 재계산된 초록 숫자

전문: `docs/amia_stage1_numbers.md` · κ 상세 패널: `results/iaa/round2_gold/iaa_stage1.{json,md}`

### 5-1. splitting_decision 일치도

| 축 | n | agreed | observed | κ |
|---|--:|--:|--:|--:|
| EHJ vs DYK — **round-2 전체** | 172 | 138 | 0.802 | 0.650 |
| EHJ vs DYK — 판정 대상 61건 | 61 | 40 | 0.656 | 0.432 |
| EHJ vs GOLD | 61 | 48 | 0.787 | 0.615 |
| DYK vs GOLD | 61 | 46 | 0.754 | 0.591 |

> ⚠️ **61건과 172건은 서로 다른 표본이므로 비교 불가.** 판정 큐는 불일치를 의도적으로 과대표집하도록 층화됐으므로 61건은 전체 corpus를 **대표하지 않으며**, 61건 κ는 기술통계일 뿐 corpus 일치도의 두 번째 추정치가 아님(`adjudication_handover.md` §D-1/D-2 가드).
>
> κ는 raw agreement뿐 아니라 **주변분포(marginal distribution)에도 의존**하므로, 불일치 과대표집이 corpus κ의 상한도 하한도 수학적으로 보장하지 않음. "구조적 하한"으로 서술하지 말 것.

> 📌 **Gold 축 κ를 "accuracy"로 부르지 말 것.** κ는 chance-corrected agreement이지 정답률이 아님. accuracy에 해당하는 값은 raw proportion(`agreed` 열)임. 초록 본문 권장 표현:
>
> *Against adjudicated gold, EHJ and DYK agreed on 48/61 (78.7%) and 46/61 (75.4%) of criteria, respectively (κ = 0.615 and 0.591).*
>
> 이 두 가드 문구는 `docs/amia_stage1_numbers.md` §2·§3에 생성 시점에 함께 기록됨(`scripts/amia_stage1_numbers.py`). MANIFEST는 데이터셋 자체만 기술하므로 분석 해석 가드는 담지 않음.

### 5-2. 판정이 실제로 바꾼 것

| outcome | n |
|---|--:|
| 두 사람 일치 → gold 확정 | 37 |
| 갈림 → gold가 EHJ 편 | 11 |
| 갈림 → gold가 DYK 편 | 9 |
| **두 사람 만장일치 → gold가 둘 다 뒤집음** | **3** |
| 갈림 → gold가 제3의 답 | 1 |

만장일치를 뒤집은 3건: `NCT01295827_I2`, `NCT03728556_E5`, `NCT03728556_E17`.

**2:1 다수결로는 절대 나올 수 없는 케이스**로, `adjudication_handover.md` §7.2의 "판정자 blind_label은 제3 의견이지 투표권이 아니다"를 실증함. 초록의 핵심 주장으로 쓸 수 있는 숫자.

---

## 6. 남은 판단 1건 — D-3 분석 축

`adjudication.pass`가 61건 전부 `blind`이므로 **D-3(`blind_label ≠ gold`) 표본이 구조적으로 0건**. 초록에서 blind→final 변화를 다룰 계획이었다면 현 데이터로는 불가능.

| 선택지 | 비용 | 평가 |
|---|---|---|
| **① 그 축을 빼고 "single blind pass"로 명시** | 없음 | **권장.** §5-2의 "만장일치 3건 뒤집음"이 같은 논지를 더 강하게 보여줌 |
| ② revealed pass를 실제로 한 바퀴 실행 | 61건 재판정 | 마감(9/3) 대비 비현실적 |

---

## 부록 A. 재현 명령

```bash
# freeze 재생성 (검증 실패 시 non-zero exit)
python scripts/export_adjudicated_dataset.py --strict

# κ 패널 (GOLD 축 포함)
python scripts/compute_iaa.py --stage 1 --round 2 --include-llm --out results/iaa/round2_gold

# 초록 숫자 (frozen export 기준)
python scripts/amia_stage1_numbers.py --out docs/amia_stage1_numbers.md

# 테스트
python tests/test_iaa_metrics.py     # 39/39
python tests/test_adjudication.py    # 50/50
```

## 부록 B. 변경 파일

| 파일 | 성격 |
|---|---|
| `scripts/export_adjudicated_dataset.py` | 신규 — freeze export + MANIFEST 생성 |
| `scripts/amia_stage1_numbers.py` | 신규 — frozen export에서 초록 숫자 재계산 |
| `iaa_pipeline/metrics.py` | 수정 — `_span_tokens` 배열형 `text_span` 대응 (버그) |
| `tests/test_iaa_metrics.py` | 수정 — 배열형 span 회귀 테스트 추가 |
| `CLAUDE.md` | 수정 — 두 신규 스크립트를 명령 목록에 추가 |
| `AMIA_2027_STAGE1_GOLD_61items_2026-09-02/` | 재생성 — jsonl ×2 + txt ×2 + MANIFEST |
| `docs/amia_stage1_numbers.md` | 신규 — 초록 숫자 리포트 |
| `results/iaa/round2_gold/` | 신규 — GOLD 축 포함 κ 패널 (기존 `round2/`의 annotator-only 스냅샷은 보존) |

> 09:25 stale export 원본은 세션 scratchpad에 백업되어 있으며 저장소에는 남기지 않음.
