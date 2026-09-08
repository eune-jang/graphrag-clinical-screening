# Stage 1 adjudication — frozen evidence bundle (2026-09-07)

> **동결일**: 2026-09-07 · **번들 생성일**: 2026-09-08
> **판정 기준표준**: ontology spec **v1.2.2** + **v1.2.3 패치** + annotation guideline **v1.2.2**
> **범위**: Stage 1 splitting 판정 **전건 완료** — 큐 113건 = gold 113건, 미해결 gap 0건
> **상태**: **APPEND-ONLY.** 이 디렉터리의 어떤 파일도 수정·재포맷·정규화하지 않는다.

이 번들은 Stage 1 판정이 끝난 시점의 증거를 **한 디렉터리 안에서 자기완결적으로** 재검증할 수 있도록
동결한 사본이다. 재계산이 아니라 **복사**이며, 원본과 바이트 단위로 동일하다.

---

## 1. 왜 이 번들이 존재하는가

판정의 실제 원본 세 가지가 서로 다른 이유로 Git 밖에 있었다.

| 원본 | 위치 | Git 상태 | 문제 |
|---|---|---|---|
| R1/R2 어노테이터 envelope | `iaa_workspace/` | `.gitignore` 대상 | 버전관리 이력이 **전혀 없음**. 이 노트북이 유일 사본이었다 |
| GOLD committed envelope | `iaa_workspace/` | 동일 | 동일 |
| 판정 큐 | `results/adjudication/` | `results/*` 무시 대상 | `build_adjudication_queue.py`가 **S4 감사표본을 매번 재추첨**한다. 시드는 고정이지만 표본틀은 고정이 아니므로, 이 큐 파일을 잃으면 **재생성이 불가능**하다. 그런데 이 표본은 논문 Methods에 보고된다 |

세 원본 모두 live working file로 제자리에 그대로 두고(작업 흐름 불변),
**불변 사본만** 이 번들에 넣어 버전관리한다.

---

## 2. 구성

```
evidence/stage1/adjudication_v1_2_2_2026-09-07/
├── README.md            이 파일
├── SHA256SUMS           아래 64개 파일 전부의 sha256 (README·SHA256SUMS 자신은 제외)
├── gold/                113-item 동결 export (5 files)
├── queue/               판정 큐 원본 (3 files)
└── envelopes/           R1/R2/GOLD envelope 불변 사본 (56 files, 8 trials)
```

### 2.1 `gold/` — 113-item 동결 export

| 파일 | 용도 |
|---|---|
| `STAGE1_ADJUDICATED_113items_2026-09-07.jsonl` (+`.txt`) | provenance 사본. 저장된 record 그대로, 가공 없음 |
| `STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl` (+`.txt`) | 리뷰/출판용. 원문 `criterion_text`·`criterion_type`·`protocol_ref`·`source_order` 조인 |
| `MANIFEST.txt` | export 스크립트가 생성한 통계 + sha256 |

`.txt`는 대응 `.jsonl`과 **바이트 동일**한 사본이다(해시가 같다). 별도 포맷이 아니다.

`scripts/export_adjudicated_dataset.py`가 만든 리포지터리 루트의
`STAGE1_GOLD_113items_2026-09-07/`와 **내용이 동일**하다. 루트 쪽은 스크립트가 바라보는
생성 경로(`amia_stage1_numbers.py` 등이 저장소 루트를 glob한다)이고, 이쪽은 동결 증거 사본이다.
둘이 갈라지면 `SHA256SUMS`로 즉시 검출된다.

### 2.2 `queue/` — 판정 큐

| 파일 | 비고 |
|---|---|
| `adjudication_queue.json` (113 items) | **재생성 불가.** S1 49 / S2 35 / S3 4 / S4 25 |
| `adjudication_queue.csv` | 위 JSON의 CSV 표현 |
| `tier0_violations.csv` | tier-0 위생 점검 출력. **원본 mtime 2026-07-30** — 큐(08-25)보다 앞선 시점의 산출물이며, 큐 생성 이전 단계의 기록으로 함께 보관한다 |

`queue/adjudication_queue.json`의 `criterion_id` 집합은 `gold/`의 113건과 **정확히 일치**한다(차집합 0).

### 2.3 `envelopes/` — R1/R2/GOLD 불변 사본

8개 IAA trial × `stage1/{input.json, llm_output.json, round1/, round2/}`.

| 구분 | 파일 수 | 내용 |
|---|--:|---|
| `input.json` | 8 | 판정 대상 criterion 원문 |
| `llm_output.json` | 7 | Stage 1 LLM 사전 어노테이션 (NCT03800134 없음) |
| `round1/{DYK,EHJ}_*` | 16 | 1라운드 어노테이터 라벨 |
| `round2/{DYK,EHJ}_*` | 16 | 2라운드 어노테이터 라벨 |
| `round2/GOLD_*` | 8 | 판정 결과 (113 record) |
| `round2/gap_tickets.json` | 1 | NCT03728556 — **빈 배열** |

R1/R2 합계 **172 record × 2 annotator × 2 round**. 이것이 전체 코퍼스 κ(=0.650, n=172)의 분모다.

`.DS_Store`는 복사하지 않았다. 이 8개 trial이 IAA 실험 대상이며,
`iaa_pipeline_spec/iaa_8trials.txt`의 9개 id 중 파일럿 trial **NCT03425643(KEYNOTE-671)은 제외**된다
— 프롬프트 few-shot 예제의 출처라 누출 방지를 위해 IAA에서 뺐다.

---

## 3. 검증된 프로파일

`gold/STAGE1_ADJUDICATED_113items_WITH_TEXT_2026-09-07.jsonl`에서 재계산한 값.

| 항목 | 값 |
|---|---|
| total lines / gold / gap ticket | 113 / **113** / **0** |
| trials | 8 |
| unique criterion ID / 중복 | 113 / 0 |
| criterion type | exclusion 62, inclusion 51 |
| text_span 축자 위반 | **0** |
| queue stratum | S1 49 · S2 35 · S3 4 · S4 25 |
| tier | 0 → 10, 1 → 2, 2 → 101 |
| splitting_decision | none 59 · composite_split 42 · nested_exception 10 · macro_aggregate 2 |
| rule_status | existing 99 · new 12 · conflict 2 |
| `escalate_pi=true` | 7건 |

`rule_status=conflict` 2건: `NCT03800134_E6`, `NCT05756153_E6`
`escalate_pi=true` 7건: `NCT02075840_E12`, `NCT02125461_I2`, `NCT02912949_E7`, `NCT03728556_I3`, `NCT03800134_E5`, `NCT03800134_E6`, `NCT05756153_E6`

### 판정 provenance — 단일 blind pass

**이 서술을 사후에 다르게 고쳐 쓰지 말 것.**

- `adjudication.pass == "revealed"`인 record가 **하나도 없다**.
- 동료 라벨을 공개한 뒤 gold를 수정한 사례가 없다.
- 113건 전부 `blind_label == gold`이며, 둘이 다른 record는 **0건**이다.
- 따라서 이 데이터셋에는 D-3("blind → revealed 라벨 변경") 표본이 **존재하지 않는다**.

판정은 다수결도, 어노테이터 합의도 아니다. 단일 판정자(`GOLD`)가 동결 기준표준에 대해
`rule_id`를 인용하고 증거 `tier`를 부여하는 정오 판단이다. 두 어노테이터가 일치해도 둘 다 틀릴 수 있으므로
일치 항목도 감사 대상에 포함했다.

---

## 4. 계보 — 61 → 74 → 113

criterion_id 집합이 **완전히 중첩**한다(실측 확인).

```
AMIA_2027_STAGE1_GOLD_61items_2026-09-01/   60 gold + 1 gap ticket   (선행본, WITH_TEXT .txt 누락)
        ⊆
AMIA_2027_STAGE1_GOLD_61items_2026-09-02/   61 gold, 0 gap · S1 36 + S4 25
        ⊆
AMIA_2027_STAGE1_GOLD_74items_2026-09-03/   74 gold, 0 gap · S1 49 + S4 25   ← AMIA 제출 시점
        ⊆
   이 번들 (113)                            113 gold, 0 gap · S1+S2+S3+S4     ← 판정 전건 완료
```

61·74는 **AMIA 계보 스냅샷**이며 최종 판정 범위가 아니다. 삭제하지 말 것.
113 − 74 = 39건은 S2 35 + S3 4이다.

---

## 5. 무결성 재검증 방법

```bash
cd evidence/stage1/adjudication_v1_2_2_2026-09-07
shasum -a 256 -c SHA256SUMS          # 64개 전부 OK 이어야 한다

# 루트 export와 갈라지지 않았는지
for f in gold/STAGE1_*; do cmp "$f" "../../../STAGE1_GOLD_113items_2026-09-07/$(basename $f)"; done

# live workspace와 갈라지지 않았는지 (이 번들에 담긴 8 trial만 비교)
(cd envelopes && find . -type f) | while read -r f; do
  cmp "envelopes/$f" "../../../iaa_workspace/$f" || echo "DIVERGED: $f"
done
```

---

## 6. 하지 말 것

- 이 디렉터리의 파일을 수정·재포맷·정규화하는 것 (JSON 재직렬화 포함 — 해시가 깨진다)
- 향후 guideline v1.3에 맞춰 historical record를 "올려 맞추는" 것
- 61/74 스냅샷을 "113이 최신이니까" 삭제하는 것
- 이 데이터셋을 2-pass revealed 판정으로 서술하는 것 (§3 참조)
- 판정 강화 gold 정확도를 전체 코퍼스 어노테이터 κ와 **같은 척도인 것처럼** 나란히 비교하는 것

## 7. 관련 문서

- `docs/amia2027_gold_freeze_2026-09-02.md` / `-03.md` — 선행 freeze 기록
- `iaa_pipeline_spec/adjudication_guide_v2_over_v1.md` §2-0 — 기준표준 정의
- `iaa_pipeline_spec/adjudication_handover.md` — 판정 설계 근거
- `pipeline/schema/annotation_guideline_v1_2_2_notion.md` — 동결 가이드라인 (규칙 ID 출처)
- `pipeline/schema/ontology_spec_v1_2_3_patch.md` — 미병합 정합성 패치
