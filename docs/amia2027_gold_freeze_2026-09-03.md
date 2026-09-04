# Stage 1 analytic gold freeze — 74건 확장본 (2026-09-03)

> **작성일**: 2026-09-03
> **대상**: `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/`
> **직전 freeze**: `AMIA_2027_STAGE1_GOLD_61items_2026-09-02/` (기록: `docs/amia2027_gold_freeze_2026-09-02.md`)
> **계기**: 판정 큐 S1 층의 마지막 셀인 **`s1_kind = "new"` 13건**(1라운드 일치 → 2라운드 불일치)을 판정 완료하여 gold envelope에 추가
> **결론**: S1 층 **49건 전건 판정 완료**(21 persist + 15 resolved + 13 new). `--strict` export 통과, 교차검증 12/12, 테스트 94/94

---

## 0. 한눈에

| 항목 | 09-02 freeze | 09-03 freeze |
|---|--:|--:|
| gold record | 61 | **74** (+13) |
| gap ticket | 0 | 0 |
| trials | 8 | 8 |
| queue stratum | S1 36 · S4 25 | **S1 49** · S4 25 |
| S1 판정률 | 36/49 (73%) | **49/49 (100%)** |

09-02 대비 실질 변경은 **13건 신규 추가뿐**. 기존 61건 중 내용이 바뀐 record는 없음(`NCT03728556_E6` 하나가 재저장으로 `adjudicated_at`만 `2026-09-02T00:14:57Z → 2026-09-03T01:54:14Z`로 갱신, 판정 내용 동일).

---

## 1. 추가된 13건 — `s1_kind = "new"`

큐(`results/adjudication/adjudication_queue.json`)의 `s1_kind="new"` 13건과 **집합이 정확히 일치**. 1라운드에서는 두 어노테이터가 같은 답을 냈다가 2라운드에서 갈린 항목들로, 큐 설계상 S1의 세 셀(persist / resolved / new) 중 마지막 셀.

| criterion_id | tier | rule_id | rule_status | gold `splitting_decision` |
|---|--:|---|---|---|
| `NCT02125461_E3` | 2 | §4-3 | existing | none |
| `NCT02125461_I3` | 2 | §3-1 | existing | none |
| `NCT02474355_I8` | 2 | §2-2 | existing | composite_split |
| `NCT02912949_I5` | 2 | §3-1 | existing | composite_split |
| `NCT02912949_I6` | **0** | §3-2 | existing | composite_split |
| `NCT02912949_I7` | **0** | §3-2 | existing | composite_split |
| `NCT02912949_I8` | **0** | §3-2 | existing | composite_split |
| `NCT02912949_I10` | 2 | §2-2 | existing | composite_split |
| `NCT03728556_E1` | 2 | §3-1 | existing | none |
| `NCT03728556_E7` | 2 | §3-1 | existing | none |
| `NCT03728556_I1` | 2 | §3-1 | existing | composite_split |
| `NCT03800134_I6` | 2 | §3-1 | existing | none |
| `NCT05756153_I8` | 2 | §2-3 | existing | nested_exception |

관찰 두 가지:

- **`rule_status` 13건 전부 `existing`.** 신규 규칙이 필요했던 항목이 하나도 없음 → "1라운드에 일치했다가 2라운드에 갈린" 불일치는 **규칙 부재가 아니라 규칙 미적용**이라는 `amia2027_work_summary.md` §122의 논지를 한 번 더 지지. `rule_status=new` 9건은 09-02 시점 그대로.
- **Tier 0이 3건 늘어 6건.** `NCT02912949_I6/I7/I8`이 모두 §3-2(spec 구조 제약)로 판정 — 임상 판단이 아니라 스키마 제약만으로 결론이 나는 항목이 이 셀에 몰려 있었음.

새 escalation·conflict 없음: `escalate_pi=true` 3건, `rule_status=conflict` 1건(`NCT05756153_E6`) 모두 09-02와 동일.

---

## 2. Freeze 산출물

`AMIA_2027_STAGE1_GOLD_74items_2026-09-03/`

| 파일 | sha256 |
|---|---|
| `AMIA_2027_STAGE1_ADJUDICATED_74items_2026-09-03.jsonl` (+`.txt`) | `cc018fbc4f45a91c2d21a489c8ea798648ead25c5ac4c2a08fd895ed1745750f` |
| `AMIA_2027_STAGE1_ADJUDICATED_74items_WITH_TEXT_2026-09-03.jsonl` (+`.txt`) | `97ec0277c8279ef76d273023641b2b2d6f672e1b8786d3e57bf212516b45c57d` |
| `MANIFEST.txt` | — |

검증: **74 gold / 0 gap · 8 trials · span violations 0 · 중복 ID 0 · 원문 미매칭 0** (`--strict` exit 0)

```bash
python scripts/export_adjudicated_dataset.py --strict --date 2026-09-03
```

### 데이터셋 구성

| 축 | 09-02 (61) | 09-03 (74) |
|---|---|---|
| record_type | gold 61 / gap_ticket 0 | gold 74 / gap_ticket 0 |
| queue stratum | S1 36 · S4 25 | **S1 49** · S4 25 |
| tier | 0→3 · 1→2 · 2→56 | **0→6** · 1→2 · **2→66** |
| criterion type | exclusion 39 · inclusion 22 | exclusion 42 · **inclusion 32** |
| gold `splitting_decision` | none 34 · composite 21 · nested 4 · macro 2 | none 39 · **composite 28** · nested 5 · macro 2 |
| `rule_status` | existing 51 · new 9 · conflict 1 | **existing 64** · new 9 · conflict 1 |
| `escalate_pi=true` | 3 | 3 (동일) |
| `adjudication.pass` | blind 61 | blind 74 |

`pass`가 여전히 전건 `blind`이므로 **D-3(`blind_label ≠ gold`) 표본은 계속 0건**. 09-02 freeze 문서 §6의 판단(그 축을 빼고 "single blind pass"로 명시)이 그대로 유효함.

---

## 3. 재계산된 초록 숫자

전문: `docs/amia_stage1_numbers.md` · κ 상세 패널: `results/iaa/round2_gold/iaa_stage1.{json,md}`

### 3-1. splitting_decision 일치도

| 축 | n | agreed | observed | κ | (09-02: n=61) |
|---|--:|--:|--:|--:|---|
| EHJ vs DYK — **round-2 전체** | 172 | 138 | 0.802 | 0.650 | 변화 없음 |
| EHJ vs DYK — 판정 대상 | 74 | 40 | 0.540 | 0.286 | 40/61 · 0.656 · 0.432 |
| EHJ vs GOLD | 74 | 54 | 0.730 | 0.524 | 48/61 · 0.787 · 0.615 |
| DYK vs GOLD | 74 | 51 | 0.689 | 0.494 | 46/61 · 0.754 · 0.591 |

> ⚠️ **판정 대상 표본과 172건은 서로 다른 표본이므로 비교 불가.** 판정 큐는 불일치를 의도적으로 과대표집하도록 층화됐으므로 74건은 전체 corpus를 **대표하지 않으며**, 74건 κ는 기술통계일 뿐 corpus 일치도의 두 번째 추정치가 아님(`adjudication_handover.md` §D-1/D-2 가드).
>
> κ는 raw agreement뿐 아니라 **주변분포에도 의존**하므로 불일치 과대표집이 corpus κ의 상한도 하한도 보장하지 않음. "구조적 하한"으로 서술하지 말 것.

> 📌 **Gold 축 κ를 "accuracy"로 부르지 말 것.** accuracy에 해당하는 값은 raw proportion(`agreed` 열). 초록 본문 권장 표현:
>
> *Against adjudicated gold, EHJ and DYK agreed on 54/74 (73.0%) and 51/74 (68.9%) of criteria, respectively (κ = 0.524 and 0.494).*

**숫자가 내려간 것은 성능 저하가 아니라 표본 구성 변화.** 추가된 13건은 정의상 2라운드 **불일치** 항목(`newly emerged`)만 모은 셀이므로, 판정 대상 표본의 불일치 농도가 36/61 → 49/74로 올라갔음. 세 축이 함께 내려간 것이 그 결과. 09-02 숫자와 09-03 숫자도 **서로 다른 표본**이므로 시계열로 읽지 말 것.

### 3-2. 판정이 실제로 바꾼 것

| outcome | 09-02 (61) | 09-03 (74) |
|---|--:|--:|
| 두 사람 일치 → gold 확정 | 37 | 37 |
| 갈림 → gold가 EHJ 편 | 11 | **17** |
| 갈림 → gold가 DYK 편 | 9 | **14** |
| **두 사람 만장일치 → gold가 둘 다 뒤집음** | **3** | **3** |
| 갈림 → gold가 제3의 답 | 1 | **3** |

만장일치를 뒤집은 3건은 변동 없음: `NCT01295827_I2`, `NCT03728556_E5`, `NCT03728556_E17`. **2:1 다수결로는 나올 수 없는 케이스**로, `adjudication_handover.md` §7.2("판정자 blind_label은 제3 의견이지 투표권이 아니다")를 실증하는 초록 핵심 숫자.

"갈림 → gold가 제3의 답" 3건은 두 사람 중 누구의 답도 채택되지 않은 경우로, 합의 기반 판정이었다면 잘못된 답이 확정됐을 항목. 1건 → 3건으로 늘어 이 논지의 표본이 보강됨.

---

## 4. Table 1 (round1 → round2 trajectories)

`docs/amia_stage1_trajectories.md` — **숫자는 변하지 않음**. 이 표는 어노테이터 envelope에서만 계산되므로 gold 추가와 무관.

| trajectory | round 1 | round 2 | n | % |
|---|---|---|--:|--:|
| stable agreement | agree | agree | 123 | 71.5% |
| resolved | differ | agree | 15 | 8.7% |
| persistent | differ | differ | 21 | 12.2% |
| newly emerged | agree | differ | 13 | 7.6% |
| **total** | | | **172** | 100.0% |

교차검증 **12/12 통과**. 다만 S1 검증 조건이 이번에 바뀌었음(§5-1).

---

## 5. 코드 변경

### 5-1. `scripts/amia_stage1_trajectories.py` — S1 교차검증 조건 수정

09-02 시점에는 S1 층에 `resolved`·`persistent`만 판정되어 있었으므로 검증식이 그에 맞춰져 있었음:

```
S1 stratum (36)  ==  resolved ∪ persistent
```

`s1_kind="new"` 13건이 들어오면서 이 식은 **정상 상태를 실패로 보고**하게 됨. 큐 정의상 S1은 처음부터 세 셀(persist / resolved / new) 전부였고, 09-02 export가 그중 두 셀만 담고 있었던 것. 실제 정의에 맞게 교정:

```
S1 stratum (49)  ==  resolved ∪ persistent ∪ newly emerged
```

집합 동등성 검증 결과 **S1-only 0건 / trajectory-only 0건**으로 정확히 일치.

### 5-2. `--export` 기본값을 날짜순 최신 export로

두 스크립트 모두 export 디렉터리를 **이름 전체가 아니라 뒤쪽 날짜 문자열로 정렬**하도록 변경. 이름에 item 수가 날짜보다 앞에 오므로(`AMIA_..._{N}items_{date}`) 사전식 정렬은 `"113items" < "61items"`가 되어, 항목이 늘면 **조용히 옛 freeze를 집는** 버그가 있었음.

- `amia_stage1_trajectories.py`: `--export` 하드코딩(`..._61items_2026-09-02/...`) → `newest_export()` 기본값
- `amia_stage1_numbers.py`: 기존 `newest_export()`의 정렬 키 교정

### 5-3. `tests/test_iaa_metrics.py` — S1 검증 회귀 테스트 갱신

`test_trajectory_cross_validation_flags_stratum_mismatch`가 옛 조건(`S1 == resolved ∪ persistent`)을 그대로 단언하고 있어 실패. 새 조건으로 갱신하면서 **S1이 `newly emerged`를 빠뜨린 경우도 실패로 잡는** 케이스를 추가(빠뜨림은 조용히 통과하면 안 되는 방향의 drift).

---

## 부록 A. 재현 명령

```bash
# freeze 재생성 (검증 실패 시 non-zero exit)
python scripts/export_adjudicated_dataset.py --strict --date 2026-09-03

# κ 패널 (GOLD 축 포함)
python scripts/compute_iaa.py --stage 1 --round 2 --include-llm --out results/iaa/round2_gold

# 초록 숫자 (frozen export 기준, 기본값 = 최신 export)
python scripts/amia_stage1_numbers.py --out docs/amia_stage1_numbers.md

# Table 1 trajectories (read-only, 교차검증 12/12)
python scripts/amia_stage1_trajectories.py --strict --out docs/amia_stage1_trajectories.md

# 테스트
python tests/test_iaa_metrics.py     # 44/44
python tests/test_adjudication.py    # 50/50
```

## 부록 B. 변경 파일

| 파일 | 성격 |
|---|---|
| `AMIA_2027_STAGE1_GOLD_74items_2026-09-03/` | 신규 — jsonl ×2 + txt ×2 + MANIFEST |
| `scripts/amia_stage1_trajectories.py` | 수정 — S1 검증 조건 + `--export` 기본값 |
| `scripts/amia_stage1_numbers.py` | 수정 — `newest_export()` 정렬 키 |
| `tests/test_iaa_metrics.py` | 수정 — S1 검증 회귀 테스트 갱신 |
| `docs/amia_stage1_numbers.md` | 재생성 — 74건 기준 |
| `docs/amia_stage1_trajectories.md` | 재생성 — export 참조 경로만 변경, 숫자 동일 |
| `results/iaa/round2_gold/` | 재생성 — GOLD 축 κ 패널 |
| `docs/amia2027_gold_freeze_2026-09-03.md` | 신규 — 이 문서 |

> 09-02 freeze(`AMIA_2027_STAGE1_GOLD_61items_2026-09-02/`)와 그 기록 문서는 **그대로 보존**. 초록에 인용할 숫자는 이 문서와 `docs/amia_stage1_numbers.md`의 74건 기준을 사용할 것.
