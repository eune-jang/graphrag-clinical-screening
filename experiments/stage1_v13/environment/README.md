# Stage 1 v1.3 Phase 5 — 실행 환경 기록

> **성격**: 재현성 **기록**. 개발 실험 환경을 고정하기 위한 것이고,
> 저장소의 공유 의존성을 바꾸지 않는다. (I-05 대응, PHASE 5B-prep)

## 1. Phase 5A가 실제로 성공한 환경

| 항목 | 값 |
|---|---|
| Python | **3.11.5** (CPython, miniconda base) |
| platform | Darwin arm64 |
| **openai SDK** | **1.6.1** |
| httpx / pydantic / anyio | 0.26.0 / 2.5.3 / 4.2.0 |
| model | `gpt-5.6-terra` |
| **requested** reasoning_effort | `medium` |
| max_completion_tokens | 8000 |
| 전달 방식 | `extra_body={"reasoning_effort": ..., "max_completion_tokens": ...}` |

목록은 [`requirements-phase5.txt`](requirements-phase5.txt).

## 2. 왜 `pyproject.toml`에 넣지 않았는가

저장소에는 이미 명확한 관례가 있다 — `pyproject.toml`이 개발 source of truth이고
`[project.optional-dependencies]`에 `dev` / `llm` / `iaa` 그룹이 있으며,
`requirements.txt`는 Streamlit Community Cloud 배포용 부분집합이다.

그런데도 이 파일을 별도로 둔 이유는 세 가지다.

1. **`openai`는 지금 어느 파일에도 선언되어 있지 않다.** 그런데 `pipeline/llm_client.py`
   (레거시 **프로덕션** 경로)가 이미 import한다. 즉 미선언 상태는 v1.3 개발 실험이 만든 문제가 아니라
   **기존 저장소의 결손**이다.
2. **`openai==1.6.1`을 공유 extra에 pin하면 프로덕션 경로까지 그 버전에 묶인다.**
   1.6.1은 PyPI 최신(3.8.0) 대비 매우 오래된 버전이고, v1.3 개발 실험 때문에 선택된 값이지
   프로덕션이 요구한 값이 아니다. §5-D가 금지하는 "SDK 현대화를 이유로 공유 프로덕션 LLM 동작을
   변경"의 거울상 — 실험을 이유로 프로덕션을 고정하는 것 — 에 해당한다.
3. 기존 `llm` extra는 `transformers` / `torch` / `sentence-transformers`, 즉 **로컬 open-weight**
   모델용이다. OpenAI SDK를 여기 넣으면 그룹의 의미가 섞인다.

따라서 이번 단계에서는 **대규모 의존성 리팩터를 하지 않고 기록만 남긴다.**
`openai`를 어느 그룹에 어떤 제약으로 선언할지는 **사람 판단 사항**이다(아래 §5).

## 3. `extra_body` 우회

설치본 `openai==1.6.1`의 `chat.completions.create` 서명에는
`reasoning_effort` / `max_completion_tokens` **명시 파라미터가 없다**(서명 확인).
`extra_body`는 있으므로 요청 본문에 그대로 실어 보냈다.

이 우회는 **실험 harness 안에만** 있다. `pipeline/llm_client.py`(공유 프로덕션 코드)도
`pipeline/stage1_v13/`(v1.3 런타임)도 수정하지 않았다 — 러너의 `llm=` 주입점을 썼다.

SDK를 3.x로 올리면 `extra_body` 없이 명시 파라미터를 쓰게 되므로 **harness 코드가 SDK 버전에
암묵적으로 결합되어 있다.** 이것이 재현성의 실질 위험이다.

## 4. reasoning-effort provenance — 요청과 확인을 구분한다

응답 metadata는 설정 적용을 **증명하지 않는다**. SDK 1.6.1의 `usage`가 노출하는 키는
`prompt_tokens` / `completion_tokens` / `total_tokens` 뿐이고 `reasoning_tokens` 류 필드가 없다.

따라서 run config와 attempt trace는 다음과 같이 기록한다.

```
requested_reasoning_effort = "medium"     ← 우리가 보낸 값. 검증 가능
confirmed_reasoning_effort                ← 기록하지 않는다. 제공자 metadata가 확인해 주지 않는 한
```

Phase 5B 실행 시 run config에 남겨야 할 최소 항목:

```
model                        gpt-5.6-terra
requested_reasoning_effort   medium
max_completion_tokens        8000
sdk_name / sdk_version       openai / 1.6.1
python_version               3.11.5
request_mechanism            chat.completions + extra_body
prompt_artifact / prompt_sha256
```

`pipeline/stage1_v13/tracing.py`의 `JsonlTracer(run_config=...)`가 이 dict를 **모든 attempt 레코드에
병합**하므로, 한 번 설정하면 시도 단위로 provenance가 남는다.

## 5. 사람 판단이 필요한 것

1. **`openai` 의존성 선언 위치와 제약** — 새 extra(`stage1_v13` 등) / 기존 그룹 / 계속 미선언 중 선택.
   프로덕션 경로도 이 패키지를 쓰므로 v1.3 실험만의 결정이 아니다.
2. **SDK 업그레이드 시점** — 올리면 `extra_body` 우회를 걷어낼 수 있으나 공유 의존성이 바뀐다.
   레거시 프로덕션 경로(`llm_client._call_openai`는 `temperature` + `max_tokens` 사용)의
   회귀 확인이 선행되어야 한다.
3. **reasoning effort 확인 방법** — 모델 계열 비교 단계에서 이 값은 조건 변수다.
   제공자가 확인 metadata를 주지 않는다면, 요청값 기록 외에 무엇을 근거로 삼을지 정해야 한다.

이 단계에서는 **아무것도 결정하지 않았고 아무 코드도 바꾸지 않았다.**
