#!/bin/bash
# GraphRAG Clinical Screening - Project Scaffold
# 프로젝트 루트에서 실행하세요: bash scaffold.sh

echo "📁 프로젝트 구조 생성 중..."

# ── 디렉토리 생성 ──
mkdir -p configs/experiment
mkdir -p data/{raw,processed,external}
mkdir -p src/graphrag_screening/{ontology,graph/queries,retrieval,agent,evaluation,utils}
mkdir -p notebooks
mkdir -p scripts
mkdir -p tests
mkdir -p results
mkdir -p docs/figures

# ── __init__.py 생성 ──
touch src/graphrag_screening/__init__.py
touch src/graphrag_screening/ontology/__init__.py
touch src/graphrag_screening/graph/__init__.py
touch src/graphrag_screening/retrieval/__init__.py
touch src/graphrag_screening/agent/__init__.py
touch src/graphrag_screening/evaluation/__init__.py
touch src/graphrag_screening/utils/__init__.py

# ── .gitignore ──
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg

# 환경
.env
.venv/
venv/
env/

# 데이터 (용량 크고 라이선스 이슈)
data/raw/*
data/processed/*
data/external/*
!data/raw/README.md
!data/processed/README.md
!data/external/README.md

# 실험 결과
results/*
!results/README.md

# Jupyter
.ipynb_checkpoints/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Neo4j
neo4j_data/
EOF

# ── .env.example ──
cat > .env.example << 'EOF'
# Neo4j 접속 정보
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# 데이터 경로 (머신별로 다름)
DATA_DIR=./data/raw
AACT_DIR=./data/external/aact

# LLM 설정 (필요 시)
# HF_MODEL_NAME=meta-llama/Llama-3-8B
# HF_TOKEN=your_token_here
EOF

# ── configs ──
cat > configs/neo4j.yaml << 'EOF'
# Neo4j 연결 설정
connection:
  uri: ${NEO4J_URI}
  user: ${NEO4J_USER}
  password: ${NEO4J_PASSWORD}

database: graphrag
EOF

cat > configs/model.yaml << 'EOF'
# LLM 모델 설정
default:
  model_name: "meta-llama/Llama-3-8B"
  max_tokens: 2048
  temperature: 0.0

screening:
  model_name: "meta-llama/Llama-3-8B"
  max_tokens: 1024
  temperature: 0.0
EOF

cat > configs/experiment/nsclc_sequoia.yaml << 'EOF'
# NCT02923921 (SEQUOIA Trial) 실험 설정
trial:
  nct_id: NCT02923921
  name: SEQUOIA
  cancer_type: NSCLC

ontology:
  layers: [protocol, terminology, domain, lexical]
  
evaluation:
  metrics: [precision, recall, f1, specificity]
EOF

# ── data README ──
cat > data/raw/README.md << 'EOF'
# Raw Data

이 디렉토리에는 원본 데이터가 위치합니다. Git에는 포함되지 않습니다.

## 데이터 출처 및 다운로드 방법

### AACT (Clinical Trials)
- URL: https://aact.ctti-clinicaltrials.org/downloads
- 최신 flat file (ZIP) 다운로드 후 `data/external/aact/`에 압축 해제

### n2c2 2018 Track 1
- URL: https://n2c2.dbmi.hms.harvard.edu/
- DUA 체결 후 다운로드
EOF

cat > data/processed/README.md << 'EOF'
# Processed Data

전처리 완료된 데이터가 저장됩니다. Git에는 포함되지 않습니다.
`scripts/` 또는 `notebooks/`의 코드를 실행하여 재생성할 수 있습니다.
EOF

cat > data/external/README.md << 'EOF'
# External Resources

외부 리소스 (AACT dump, SNOMED CT RF2, UMLS 등)가 위치합니다.
Git에는 포함되지 않습니다.

## 필요 리소스
- AACT flat files: https://aact.ctti-clinicaltrials.org/downloads
- SNOMED CT RF2: https://www.nlm.nih.gov/healthit/snomedct/
- UMLS MRCONSO: https://www.nlm.nih.gov/research/umls/
- RxNorm: https://www.nlm.nih.gov/research/umls/rxnorm/
EOF

# ── results README ──
cat > results/README.md << 'EOF'
# Results

실험 결과가 저장됩니다. Git에는 포함되지 않습니다.
`scripts/run_evaluation.py`를 실행하여 결과를 재생성할 수 있습니다.
EOF

# ── pyproject.toml ──
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "graphrag-clinical-screening"
version = "0.1.0"
description = "GraphRAG-based AI agent for clinical trial eligibility screening"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Eun Hye Jang"},
]

dependencies = [
    "pandas>=2.0",
    "neo4j>=5.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
    "openpyxl>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "jupyter>=1.0",
    "ipykernel>=6.0",
]
llm = [
    "transformers>=4.40",
    "torch>=2.0",
    "sentence-transformers>=2.0",
]

[tool.setuptools.packages.find]
where = ["src"]
EOF

# ── docs ──
cat > docs/architecture.md << 'EOF'
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
EOF

# ── README.md 업데이트 ──
cat > README.md << 'EOF'
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
EOF

echo ""
echo "✅ 프로젝트 구조 생성 완료!"
echo ""
echo "📂 생성된 구조:"
find . -not -path './.git/*' -not -path './.git' | head -60 | sed 's/^/  /'
echo ""
echo "다음 단계:"
echo "  git add ."
echo "  git commit -m 'add project scaffold'"
echo "  git push"
