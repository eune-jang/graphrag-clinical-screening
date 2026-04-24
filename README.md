# Beyond Keyword Matching: A GraphRAG-Based AI Agent for Clinical Trial Eligibility Screening

A GraphRAG-based AI agent that leverages multi-layered medical ontologies for automated clinical trial patient screening using EMR data.

## Project Structure

```
├── configs/          # 실험 설정 파일
├── data/             # 데이터 (raw, processed, external)
├── src/              # 메인 패키지
├── notebooks/        # 탐색·분석 노트북
├── scripts/          # 실행 스크립트
├── tests/            # 테스트
├── results/          # 실험 결과
└── docs/             # 문서 및 figure
```

## Setup

```bash
# 패키지 설치
pip install -e .

# 개발 환경
pip install -e ".[dev]"

# LLM 관련 (GPU 서버)
pip install -e ".[llm]"
```

## Architecture

4-Layer Medical Ontology (Neo4j):
1. **Protocol KG** – Clinical trial eligibility criteria
2. **Terminology KG** – Standardized code identifiers (SNOMED CT, ICD-10, RxNorm, LOINC, OMOP)
3. **Domain KG** – Clinical concepts and relationships
4. **Lexical KG** – Surface expressions (synonyms, Korean translations, abbreviations)

## Citation

*(논문 출판 후 추가 예정)*

## License

MIT License
