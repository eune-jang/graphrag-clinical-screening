# 4-Layer Medical Ontology Architecture

## Overview
GraphRAG 기반 임상시험 적격성 스크리닝을 위한 4계층 의료 온톨로지

## Layer Structure
- **Layer 1 – Protocol KG:** 임상시험 적격성 기준 (Source: AACT)
- **Layer 2 – Terminology KG:** 표준 코드 식별자 (SNOMED CT, ICD-10, RxNorm, LOINC, OMOP)
- **Layer 3 – Domain KG:** 임상 개념 및 관계
- **Layer 4 – Lexical KG:** 표면 표현 (동의어, 한국어 번역, 약어)

## Design Rationale
- Layer 번호는 top-down 구축 의존성 반영
- 추론은 bottom-up (Layer 4 → 1) 방향
- OMOP CDM은 Layer 2 노드 속성으로 임베딩 (별도 레이어 아님)
