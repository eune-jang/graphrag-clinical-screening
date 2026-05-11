"""
[ARCHIVED] Pipeline JSON → Label Studio Tasks JSON
====================================================
위치: pipeline/_archive_labelstudio_export.py
상태: ⚠️ ARCHIVED — 현재 파이프라인은 Label Studio 경로를 사용하지 않음.
      검수 워크플로우가 Neo4j + JSON 직접 검수로 이동함 (REVIEW.md 참조).
      이 파일은 향후 LS 재사용 가능성을 대비한 백업으로만 유지됨.
      활성 검수 도구: pipeline/07_neo4j_ingest.py + pipeline/08_review_queries.py

기존 입력 의존성: pipeline/06_validate_annotation.py 의 _validation 메타 활용

입력:
  - pipeline/output/*_annotation.json (validated, _validation 메타 포함)

출력:
  - pipeline/output/labelstudio/tasks.json   (모든 trial 통합, batch import 용)
  - pipeline/output/labelstudio/{NCT_ID}.json (trial 별 분리, 단일 import 용)

Label Studio 형식:
  - 각 task = trial 1개. data.text 에 모든 criterion 을 \n\n 으로 join.
  - predictions[0] 는 LLM pre-annotation. result 배열 안에:
      * NER (entities): type='labels', value={start, end, text, labels:[...]}
      * Relations: type='relation', from_id/to_id 로 entity ID 연결.
  - score: relation level 의 _validation.score 평균 (task 전체 신뢰도)
  - 개별 entity/relation 의 score 는 meta 로 부착 (Label Studio UI 가 hover 표시)

INCEpTION 의 _score / _score_explanation / _auto_accept 메타가
Label Studio 에서는 다음으로 매핑:
  - _score        → Label Studio prediction.score 또는 result item 의 meta.score
  - _explanation  → result item 의 meta.text (hover tooltip)
  - _auto_accept  → 별도 처리 없음 (annotator 가 단순 클릭으로 accept/reject)

⚠️ Label Studio 는 'auto_accept on first access' 기능이 없음.
   대신 score 로 정렬하면 high-confidence 항목 (score=1.0) 이 먼저 떠서
   annotator 가 빠르게 훑고 넘어갈 수 있음.

사용법:
  python -m pipeline._archive_labelstudio_export
  python -m pipeline._archive_labelstudio_export --trial NCT03425643

Label Studio import 방법:
  1. http://localhost:8080 접속, 로그인
  2. Create Project → Labeling Setup → Custom template → labelstudio_schema.xml 붙여넣기
  3. Save
  4. Project → Import → tasks.json 업로드 (또는 trial 별 *.json)
  5. Annotation 진입 → 회색 highlight 가 LLM pre-annotation 임
"""
from __future__ import annotations
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("_archive_labelstudio_export")


def _sanitize(text: str) -> str:
    """Strip XML/JSON-unsafe control chars (consistent with stage 4 inception)."""
    if not text:
        return ""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)


def _find_span(sofa_text: str, search_text: str, hint_begin: int = 0) -> tuple[int, int]:
    """Locate (begin, end) char offsets of search_text in sofa_text.

    Strategies (best to worst):
      1. Exact match starting near hint_begin
      2. Case-insensitive match anywhere
      3. Length-1 placeholder at hint_begin (Stage 3 already flagged 'span_not_in_text')
    """
    if not search_text:
        return hint_begin, hint_begin

    idx = sofa_text.find(search_text, max(0, hint_begin - 50))
    if idx >= 0:
        return idx, idx + len(search_text)

    idx = sofa_text.lower().find(search_text.lower())
    if idx >= 0:
        return idx, idx + len(search_text)

    return hint_begin, hint_begin + min(len(search_text), 1)


def _build_sofa(criteria: list[dict]) -> tuple[str, dict[str, tuple[int, int]]]:
    """Concat all criterion texts into one task-level text.

    Returns:
        (full_text, {criterion_id: (begin, end)})
    """
    parts: list[str] = []
    offsets: dict[str, tuple[int, int]] = {}
    cursor = 0

    for c in criteria:
        cid = c["criterion_id"]
        text = _sanitize(c.get("text", "") or "")
        offsets[cid] = (cursor, cursor + len(text))
        parts.append(text)
        cursor += len(text) + 4  # 4 = "\n\n\n\n" (criterion 사이 공백 충분히)

    return "\n\n\n\n".join(parts), offsets


def _convert_trial(annotation: dict) -> dict | None:
    """Convert a single trial annotation JSON to Label Studio task dict."""
    trial_id = annotation.get("trial_id")
    criteria = annotation.get("criteria") or []
    if not criteria:
        return None

    sofa_text, criterion_offsets = _build_sofa(criteria)

    # ---- Build prediction.result list ----
    result_items: list[dict] = []
    criterion_id_map: dict[str, str] = {}  # criterion_id -> Label Studio region id

    # 1) CriterionSpan entities
    for c in criteria:
        cid = c["criterion_id"]
        begin, end = criterion_offsets[cid]
        ls_id = f"crit_{cid}"
        criterion_id_map[cid] = ls_id

        # type/semantic_category 를 label 로 사용
        # Label Studio 는 한 region 에 여러 label 가능하지만 단순화 위해 type 만
        c_type = c.get("type", "inclusion")  # inclusion | exclusion
        label_value = "InclusionCriterion" if c_type == "inclusion" else "ExclusionCriterion"

        result_items.append({
            "id": ls_id,
            "from_name": "criterion_label",
            "to_name": "text",
            "type": "labels",
            "value": {
                "start": begin,
                "end": end,
                "text": sofa_text[begin:end],
                "labels": [label_value],
            },
            "meta": {
                "criterion_id": cid,
                "semantic_category": c.get("semantic_category", ""),
                "parent_role": c.get("parent_role", ""),
                "child_logic": c.get("child_logic", ""),
                "cohort_scope": ",".join(c.get("cohort_scope") or []),
            },
        })

    # 2) IS_PART_OF relations (child criterion -> parent criterion)
    for c in criteria:
        parent_id = c.get("parent_criterion_id")
        cid = c["criterion_id"]
        if parent_id and parent_id in criterion_id_map and cid in criterion_id_map:
            result_items.append({
                "from_id": criterion_id_map[cid],
                "to_id": criterion_id_map[parent_id],
                "type": "relation",
                "direction": "right",
                "labels": ["IS_PART_OF"],
            })

    # 3) ConceptMention entities + cross-layer relations
    auto_accept_count = 0
    flagged_count = 0
    score_sum = 0.0
    score_n = 0

    for c in criteria:
        cid = c["criterion_id"]
        criterion_text = c.get("text", "") or ""
        criterion_offset = criterion_offsets[cid]

        for ridx, rel_data in enumerate(c.get("relations") or []):
            rel_type = rel_data.get("relation_type")
            if not rel_type:
                continue

            target_text = _sanitize(rel_data.get("target_text_span", ""))
            cm_begin, cm_end = _find_span(sofa_text, target_text, criterion_offset[0])

            # Validation meta
            validation = rel_data.get("_validation") or {}
            score = validation.get("score")
            issues = validation.get("issues") or []
            review_status = validation.get("review_status")
            auto_accept = validation.get("auto_accept")

            if review_status == "auto_accept":
                auto_accept_count += 1
            elif review_status == "human_review":
                flagged_count += 1
            if score is not None:
                score_sum += float(score)
                score_n += 1

            # 3a) ConceptMention entity
            cm_id = f"concept_{cid}_{ridx}"
            result_items.append({
                "id": cm_id,
                "from_name": "concept_label",
                "to_name": "text",
                "type": "labels",
                "value": {
                    "start": cm_begin,
                    "end": cm_end,
                    "text": sofa_text[cm_begin:cm_end] if cm_end > cm_begin else target_text,
                    "labels": [rel_data.get("target_subtype") or "Concept"],
                },
                "score": float(score) if score is not None else None,
                "meta": {
                    "target_preferred_name": rel_data.get("target_preferred_name", ""),
                    "score": float(score) if score is not None else None,
                    "issues": issues,
                    "review_status": review_status,
                    "auto_accept": auto_accept,
                },
            })

            # 3b) Cross-layer relation (criterion -> concept)
            rel_meta: dict[str, Any] = {
                "score": float(score) if score is not None else None,
                "issues": issues,
                "review_status": review_status,
                "auto_accept": auto_accept,
            }
            # Spec properties
            props = rel_data.get("properties") or {}
            if isinstance(props, dict):
                # serialize complex values to string for tooltip readability
                for k, v in props.items():
                    if v is None:
                        continue
                    if isinstance(v, (dict, list)):
                        rel_meta[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        rel_meta[k] = str(v)

            biomarker = rel_data.get("biomarker_details") or {}
            if biomarker:
                rel_meta["biomarker_details"] = json.dumps(biomarker, ensure_ascii=False)

            result_items.append({
                "from_id": criterion_id_map.get(cid),
                "to_id": cm_id,
                "type": "relation",
                "direction": "right",
                "labels": [rel_type],
                "score": float(score) if score is not None else None,
                "meta": rel_meta,
            })

    # ---- Wrap into Label Studio task ----
    avg_score = score_sum / score_n if score_n else 1.0
    task = {
        "data": {
            "text": sofa_text,
            "trial_id": trial_id,
        },
        "predictions": [
            {
                "model_version": "llm-pre-annotation-v1",
                "score": round(avg_score, 4),
                "result": result_items,
            }
        ],
        "meta": {
            "trial_id": trial_id,
            "n_criteria": len(criteria),
            "n_relations": sum(len(c.get("relations") or []) for c in criteria),
            "auto_accept_count": auto_accept_count,
            "flagged_count": flagged_count,
            "avg_relation_score": round(avg_score, 4),
        },
    }
    return task


def convert_batch(input_dir: Path, output_dir: Path,
                  trial_filter: str | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(input_dir.glob("*_annotation.json"))
    if trial_filter:
        json_files = [f for f in json_files if trial_filter in f.name]
    if not json_files:
        logger.error(f"No annotation JSONs found in {input_dir}")
        return

    all_tasks: list[dict] = []
    success = errors = 0
    auto_total = flagged_total = 0

    for json_path in json_files:
        trial_id = json_path.stem.replace("_annotation", "")
        try:
            with open(json_path, encoding="utf-8") as f:
                annotation = json.load(f)
            task = _convert_trial(annotation)
            if not task:
                logger.warning(f"Skipping {trial_id}: no criteria")
                continue

            # 단일 trial 파일로도 저장 (개별 import 가능하도록)
            single_path = output_dir / f"{trial_id}.json"
            with open(single_path, "w", encoding="utf-8") as f:
                json.dump([task], f, ensure_ascii=False, indent=2)

            all_tasks.append(task)
            n_auto = task["meta"]["auto_accept_count"]
            n_flag = task["meta"]["flagged_count"]
            auto_total += n_auto
            flagged_total += n_flag
            n_rel = task["meta"]["n_relations"]
            n_crit = task["meta"]["n_criteria"]
            logger.info(
                f"  ✓ {trial_id}: {n_crit} criteria, {n_rel} relations, "
                f"auto:{n_auto} flagged:{n_flag} → {single_path.name}"
            )
            success += 1
        except Exception as e:
            logger.error(f"  ✗ {trial_id}: {e}")
            errors += 1

    # 통합 batch 파일
    batch_path = output_dir / "tasks.json"
    with open(batch_path, "w", encoding="utf-8") as f:
        json.dump(all_tasks, f, ensure_ascii=False, indent=2)

    logger.info(
        f"\n{'═' * 60}\n"
        f"Label Studio Export Complete\n"
        f"  Converted: {success}/{len(json_files)} trials\n"
        f"  Errors:    {errors}\n"
        f"  Output:    {output_dir}\n"
        f"  Batch file: {batch_path.name}\n"
        f"\n"
        f"Validation summary (전체):\n"
        f"  auto_accept (high-confidence): {auto_total}\n"
        f"  flagged (검수 필요):           {flagged_total}\n"
        f"\n"
        f"Label Studio import 방법:\n"
        f"  1. localhost:8080 접속\n"
        f"  2. Create Project → Labeling Setup → Custom template\n"
        f"  3. labelstudio_schema.xml 내용 붙여넣기 → Save\n"
        f"  4. Import → 단일 trial: {{NCT_ID}}.json,  전체 batch: tasks.json\n"
        f"{'═' * 60}"
    )


def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    _this_dir = Path(__file__).parent
    parser = argparse.ArgumentParser(
        description="Stage 4: Convert validated annotation JSON to Label Studio tasks JSON"
    )
    parser.add_argument("--input", "-i", type=Path,
                        default=_this_dir / "output")
    parser.add_argument("--output", "-o", type=Path,
                        default=_this_dir / "output" / "labelstudio")
    parser.add_argument("--trial", type=str, default=None)

    args = parser.parse_args()
    convert_batch(args.input, args.output, args.trial)


if __name__ == "__main__":
    main()