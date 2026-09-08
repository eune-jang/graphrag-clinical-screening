# evidence/ — frozen research evidence

> **append-only 영역이다.** 여기 들어온 파일은 수정하지 않는다.
> JSON 재직렬화, 공백 정규화, 개행 변경도 **수정으로 간주**한다.

## 무엇이 여기에 들어오는가

연구 결과를 **재검증 가능한 상태로 고정**한 사본. 재계산이 아니라 복사이며,
원본과 바이트 단위로 동일해야 한다.

특히 아래 세 종류가 대상이다.

1. **동결 export** — 해시가 찍힌 gold/결과 파일
2. **재생성 불가한 중간 산출물** — 예: 무작위 표본이 섞인 작업목록
3. **버전관리 밖에 있던 1차 연구 데이터의 불변 사본** — 예: `iaa_workspace/`의 어노테이션 envelope

## 현재 번들

| 경로 | 내용 |
|---|---|
| [`stage1/adjudication_v1_2_2_2026-09-07/`](stage1/adjudication_v1_2_2_2026-09-07/) | Stage 1 판정 전건 완료 — 113 gold / 0 gap / 8 trials. gold export + exact queue + R1/R2/GOLD 불변 사본 (66 files) |

기준표준: ontology spec **v1.2.2** + **v1.2.3** 패치 + Stage 1 annotation guideline **v1.2.2**.
디렉터리 이름의 `v1_2_2`가 그 기준표준을 가리킨다.

## 명명 규칙

```
evidence/{stage}/{track}_{normative_basis}_{freeze_date}/
```

예: `stage1/adjudication_v1_2_2_2026-09-07/`

새 freeze는 **항상 새 디렉터리**다. 기존 디렉터리에 덮어쓰지 않는다.
같은 날 다시 동결해야 하면 내용이 실제로 달라졌는지부터 확인한다.

## 각 번들이 갖춰야 할 것

- `README.md` — provenance, 프로파일, 계보, **재검증 절차**
- `SHA256SUMS` — payload 전체의 해시
- 동결 payload

## 무결성 확인

```bash
cd evidence/stage1/adjudication_v1_2_2_2026-09-07
shasum -a 256 -c SHA256SUMS
```

번들별 상세 절차는 각 `README.md`에 있다.

## 하지 말 것

- 최신 번들이 생겼다고 이전 번들을 지우는 것 — 계보가 증거다
- 향후 규칙(v1.3 등)에 맞춰 historical record를 마이그레이션하는 것
- 동결 파일 안의 로컬 절대경로를 "정리"하는 것 — 해시가 깨진다.
  공개 배포가 필요하면 원본을 두고 **sanitized derived artifact를 따로** 만든다
  ([`../docs/repository/SOURCE_OF_TRUTH.md`](../docs/repository/SOURCE_OF_TRUTH.md) §6)

## 관련

- [`../docs/CURRENT_STATUS.md`](../docs/CURRENT_STATUS.md) — 최신 연구 상태
- [`../docs/repository/SOURCE_OF_TRUTH.md`](../docs/repository/SOURCE_OF_TRUTH.md) — 권위 우선순위
- [`../docs/papers/amia2027/README.md`](../docs/papers/amia2027/README.md) — AMIA 계보 스냅샷 (저장소 루트에 별도 보관)
