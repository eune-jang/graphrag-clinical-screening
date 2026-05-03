"""
AACT NSCLC Clinical Trial Sampling Frame Builder
=================================================
Protocol KG (Layer 1) 구축을 위한 NSCLC 임상시험 프로토콜 선정 스크립트

위치: notebooks/01_aact_nsclc_sampling_frame.py

TODO: 안정화 후 분리
  - 핵심 로직 → src/graphrag_screening/ontology/layer1_protocol.py
  - 실행 진입점 → scripts/build_sampling_frame.py

사전 준비:
1. https://aact.ctti-clinicaltrials.org/downloads 에서 최신 flat file (ZIP) 다운로드
2. ZIP 파일 압축 해제
3. 아래 DATA_DIR 경로를 압축 해제한 폴더로 변경

필요 라이브러리: pip install pandas openpyxl

변경 이력:
  - v2 (2026-05): NCCN v5.2026 기준 검토 후 업데이트
    - BIOMARKER_MAP: NRG1 추가 (NSCL-19 footnote qq 필수 검사 항목)
    - Modality: ADC_KEYWORDS, BISPECIFIC_KEYWORDS 카테고리 신설
    - TKI_KEYWORDS: ensartinib, repotrectinib 등 11개 약물 추가
    - ANTI_VEGF_KEYWORDS: bevacizumab, ramucirumab 분리 (기존 CHEMO에서 이동)
    - browse_conditions, keywords 테이블 필터링 로직에 반영
    - classify_stage() 함수 추가
    - amivantamab BISPECIFIC으로 재분류
  - v2.1 (2026-05): 코드 리뷰 후 버그 수정 및 분류 로직 보강
    - classify_histology(): adenosquamous 오분류 버그 수정 (Squamous → Both)
    - SURGERY_KEYWORDS: neoadjuvant/adjuvant 제거 (classify_stage()에서만 처리)
    - classify_stage(): "advanced" 단독 표현 처리 추가 (→ Advanced (III/IV))
    - classify_line(): maintenance/consolidation 패턴 추가
"""

import pandas as pd
import os
import re
from collections import Counter

# ============================================================
# 1. 설정 — 이 경로만 수정하세요
# ============================================================
DATA_DIR = "../data/external/aact"  # 프로젝트 구조 기준 상대 경로

# 필요한 파일 목록
REQUIRED_FILES = {
    "studies": os.path.join(DATA_DIR, "studies.txt"),
    "conditions": os.path.join(DATA_DIR, "conditions.txt"),
    "eligibilities": os.path.join(DATA_DIR, "eligibilities.txt"),
    "interventions": os.path.join(DATA_DIR, "interventions.txt"),
    "sponsors": os.path.join(DATA_DIR, "sponsors.txt"),
    "browse_conditions": os.path.join(DATA_DIR, "browse_conditions.txt"),
    "keywords": os.path.join(DATA_DIR, "keywords.txt"),
}

# ============================================================
# 2. 데이터 로드
# ============================================================
def load_table(name, filepath, usecols=None):
    """AACT pipe-delimited 파일 로드"""
    if not os.path.exists(filepath):
        print(f"  [경고] {name} 파일 없음: {filepath}")
        return pd.DataFrame()
    print(f"  로딩: {name} ← {filepath}")
    df = pd.read_csv(filepath, sep="|", low_memory=False, usecols=usecols)
    print(f"    → {len(df):,} rows")
    return df


def load_all():
    """필요한 테이블 전체 로드"""
    print("\n📂 AACT 데이터 로딩 중...\n")

    studies = load_table("studies", REQUIRED_FILES["studies"], usecols=[
        "nct_id", "study_type", "overall_status", "phase",
        "brief_title", "official_title", "enrollment", "start_date",
        "completion_date", "source",
    ])

    conditions = load_table("conditions", REQUIRED_FILES["conditions"], usecols=[
        "nct_id", "name",
    ])

    eligibilities = load_table("eligibilities", REQUIRED_FILES["eligibilities"], usecols=[
        "nct_id", "criteria",
    ])

    interventions = load_table("interventions", REQUIRED_FILES["interventions"], usecols=[
        "nct_id", "intervention_type", "name", "description",
    ])

    sponsors = load_table("sponsors", REQUIRED_FILES["sponsors"], usecols=[
        "nct_id", "lead_or_collaborator", "agency_class", "name",
    ])

    # v2: browse_conditions, keywords 로드 추가
    browse_conditions = load_table(
        "browse_conditions", REQUIRED_FILES["browse_conditions"],
        usecols=["nct_id", "mesh_term"],
    )

    keywords = load_table(
        "keywords", REQUIRED_FILES["keywords"],
        usecols=["nct_id", "name"],
    )

    return studies, conditions, eligibilities, interventions, sponsors, browse_conditions, keywords


# ============================================================
# 3. NSCLC 시험 필터링
# ============================================================
NSCLC_PATTERNS = [
    r"non.?small\s*cell\s*lung",
    r"nsclc",
    r"non.?small.?cell\s*lung\s*cancer",
    r"non.?small.?cell\s*lung\s*carcinoma",
    r"비소세포폐암",
]
NSCLC_REGEX = re.compile("|".join(NSCLC_PATTERNS), re.IGNORECASE)

# MeSH terms for NSCLC (browse_conditions 테이블용)
NSCLC_MESH_TERMS = [
    "Carcinoma, Non-Small-Cell Lung",
    "Lung Neoplasms",
]


def filter_nsclc(studies, conditions, browse_conditions, keywords):
    """NSCLC 관련 시험 필터링 (conditions + title + browse_conditions + keywords)"""

    # (a) conditions 테이블에서 NSCLC 매칭
    cond_match = conditions[
        conditions["name"].fillna("").str.contains(NSCLC_REGEX)
    ]["nct_id"].unique()

    # (b) brief_title / official_title에서 NSCLC 매칭
    title_match_brief = studies[
        studies["brief_title"].fillna("").str.contains(NSCLC_REGEX)
    ]["nct_id"].unique()

    title_match_official = studies[
        studies["official_title"].fillna("").str.contains(NSCLC_REGEX)
    ]["nct_id"].unique()

    # (c) v2: browse_conditions (NLM MeSH term) 매칭
    bc_match = set()
    if not browse_conditions.empty and "mesh_term" in browse_conditions.columns:
        bc_match = set(browse_conditions[
            browse_conditions["mesh_term"].isin(NSCLC_MESH_TERMS)
        ]["nct_id"].unique())

    # (d) v2: keywords 테이블 매칭
    kw_match = set()
    if not keywords.empty and "name" in keywords.columns:
        kw_match = set(keywords[
            keywords["name"].fillna("").str.contains(NSCLC_REGEX)
        ]["nct_id"].unique())

    all_nsclc_ids = (
        set(cond_match) | set(title_match_brief) | set(title_match_official)
        | bc_match | kw_match
    )

    # Interventional 시험만 필터
    nsclc = studies[
        (studies["nct_id"].isin(all_nsclc_ids)) &
        (studies["study_type"] == "Interventional")
    ].copy()

    # 유효한 status 필터
    valid_statuses = [
        "Completed", "Active, not recruiting", "Recruiting",
        "Enrolling by invitation", "Not yet recruiting",
        "Terminated", "Suspended", "Withdrawn",
    ]
    nsclc = nsclc[nsclc["overall_status"].isin(valid_statuses)]

    print(f"\n🔍 NSCLC Interventional 시험: {len(nsclc):,}건")
    print(f"   - conditions 매칭: {len(cond_match):,}")
    print(f"   - title 매칭 (추가): {len(set(title_match_brief) | set(title_match_official)):,}")
    print(f"   - browse_conditions (MeSH) 매칭: {len(bc_match):,}")
    print(f"   - keywords 매칭: {len(kw_match):,}")
    print(f"   - 합집합 (중복 제거 전): {len(all_nsclc_ids):,}")

    return nsclc


# ============================================================
# 4. 층화 기준 태깅 (자동 분류)
# ============================================================

# --- 4a. Treatment Modality 분류 ---
# v2: NCCN NSCL-J 기준 전면 재구성

TKI_KEYWORDS = [
    # EGFR TKI (1-3세대)
    "erlotinib", "gefitinib", "afatinib", "osimertinib", "dacomitinib",
    "lazertinib",
    # EGFR exon 20 insertion
    "sunvozertinib",
    # ALK TKI
    "crizotinib", "ceritinib", "alectinib", "brigatinib", "lorlatinib",
    "ensartinib",                                        # v2 추가
    # ROS1/NTRK TKI
    "repotrectinib", "taletrectinib",                    # v2 추가
    "entrectinib", "larotrectinib",
    # RET TKI
    "selpercatinib", "pralsetinib",
    "cabozantinib",                                      # v2 추가
    # MET TKI
    "capmatinib", "tepotinib",
    # KRAS G12C
    "sotorasib", "adagrasib",
    # BRAF (+MEK) inhibitors
    "dabrafenib", "trametinib",
    "encorafenib", "binimetinib", "vemurafenib",         # v2 추가
    # HER2 TKI
    "zongertinib", "sevabertinib",                       # v2 추가
    # EGFR exon 20 (legacy)
    "mobocertinib",
    # FGFR (emerging)
    "erdafitinib",                                       # v2 추가
]

IO_KEYWORDS = [
    "nivolumab", "pembrolizumab", "atezolizumab", "durvalumab",
    "ipilimumab", "tremelimumab", "cemiplimab",
    "anti-pd-1", "anti-pd-l1", "anti-ctla-4",
    "pd-1", "pd-l1", "checkpoint inhibitor", "immunotherapy",
    "immune checkpoint",
]

CHEMO_KEYWORDS = [
    # v2: bevacizumab, ramucirumab을 ANTI_VEGF로 분리
    "cisplatin", "carboplatin", "pemetrexed", "docetaxel", "paclitaxel",
    "gemcitabine", "vinorelbine", "etoposide", "nab-paclitaxel",
    "chemotherapy", "platinum-based", "platinum doublet",
]

# v2: 신규 카테고리 — ADC (Antibody-Drug Conjugate)
ADC_KEYWORDS = [
    "datopotamab deruxtecan", "datopotamab",
    "trastuzumab deruxtecan", "fam-trastuzumab", "t-dxd",
    "ado-trastuzumab emtansine", "t-dm1",
    "telisotuzumab vedotin", "telisotuzumab",
    "sacituzumab govitecan", "sacituzumab",
    "antibody-drug conjugate", "antibody drug conjugate",
]

# v2: 신규 카테고리 — Bispecific Antibody
BISPECIFIC_KEYWORDS = [
    "amivantamab",       # EGFR/MET bispecific (기존 TKI에서 이동)
    "zenocutuzumab",     # HER2/HER3 bispecific (NRG1 fusion)
    "bispecific",
]

# v2: Anti-VEGF (기존 CHEMO에서 분리)
ANTI_VEGF_KEYWORDS = [
    "bevacizumab", "ramucirumab",
    "anti-vegf", "antiangiogenic",
]

RADIATION_KEYWORDS = [
    "radiation", "radiotherapy", "chemoradiation", "sbrt",
    "stereotactic", "proton", "imrt", "igrt",
]

SURGERY_KEYWORDS = [
    "surgery", "surgical", "resection", "lobectomy", "pneumonectomy",
    # v2.1: neoadjuvant/adjuvant 제거 — Surgery 아닌 neoadjuvant chemo 시험의 오분류 방지
    # perioperative context는 classify_stage()의 periop_pats에서 처리
]


def classify_modality(intervention_text):
    """중재 텍스트에서 treatment modality 분류 (복수 가능)"""
    text = str(intervention_text).lower()
    modalities = set()

    if any(kw in text for kw in TKI_KEYWORDS):
        modalities.add("Targeted (TKI)")
    if any(kw in text for kw in IO_KEYWORDS):
        modalities.add("Immunotherapy")
    if any(kw in text for kw in CHEMO_KEYWORDS):
        modalities.add("Chemotherapy")
    if any(kw in text for kw in ADC_KEYWORDS):
        modalities.add("ADC")
    if any(kw in text for kw in BISPECIFIC_KEYWORDS):
        modalities.add("Bispecific Ab")
    if any(kw in text for kw in ANTI_VEGF_KEYWORDS):
        modalities.add("Anti-VEGF")
    if any(kw in text for kw in RADIATION_KEYWORDS):
        modalities.add("Radiation")
    if any(kw in text for kw in SURGERY_KEYWORDS):
        modalities.add("Surgery")

    if not modalities:
        modalities.add("Other/Unclassified")

    return " + ".join(sorted(modalities))


# --- 4b. Molecular Target / Biomarker 분류 ---
# v2: NRG1 추가, MET/HER2 패턴 보강

BIOMARKER_MAP = {
    "EGFR":     [r"egfr", r"epidermal growth factor"],
    "ALK":      [r"\balk\b", r"anaplastic lymphoma kinase"],
    "ROS1":     [r"ros1", r"ros-1"],
    "PD-L1":    [r"pd-?l1", r"programmed death.?ligand"],
    "KRAS":     [r"kras", r"k-ras"],
    "BRAF":     [r"braf", r"b-raf", r"v600e"],
    "MET":      [r"\bmet\b.*exon", r"met amplif", r"c-met",
                 r"met\s*ex14", r"met.*skipping"],               # v2: 패턴 보강
    "RET":      [r"\bret\b.*fusion", r"\bret\b.*rearrange",
                 r"ret-positive", r"ret\s+positive"],             # v2: 패턴 보강
    "NTRK":     [r"ntrk", r"neurotrophic"],
    "HER2":     [r"her2", r"her-2", r"erbb2",
                 r"her2.*ihc", r"her2.*overexpression"],          # v2: IHC 패턴 추가
    "NRG1":     [r"nrg1", r"neuregulin"],                        # v2: 신규 추가
    "STK11":    [r"stk11"],
    "TP53":     [r"tp53", r"p53"],
    "FGFR":     [r"fgfr", r"fibroblast growth factor receptor"], # v2: emerging 추가
}


def classify_biomarkers(text):
    """텍스트에서 biomarker 키워드 탐지"""
    text = str(text).lower()
    found = []
    for marker, patterns in BIOMARKER_MAP.items():
        if any(re.search(p, text) for p in patterns):
            found.append(marker)
    return ", ".join(found) if found else "Not specified"


# --- 4c. Line of Therapy 분류 ---
def classify_line(text):
    """eligibility criteria / title에서 line of therapy 추정"""
    text = str(text).lower()

    first_line_pats = [
        r"first.?line", r"1st.?line", r"1l\b", r"treatment.?na[iï]ve",
        r"previously\s+untreated", r"no\s+prior\s+(systemic\s+)?therapy",
        r"frontline",
    ]
    later_line_pats = [
        r"second.?line", r"2nd.?line", r"2l\b",
        r"third.?line", r"3rd.?line", r"3l\b",
        r"previously\s+treated", r"prior\s+(systemic\s+)?therapy",
        r"after\s+progression", r"relapsed", r"refractory",
        r"post.?(platinum|chemo|immunotherapy)",
    ]
    # v2.1: maintenance/consolidation 패턴 추가
    # NCCN에서 1L 후 유지요법 및 chemoRT 후 consolidation을 별도 치료 맥락으로 다룸
    maintenance_pats = [
        r"maintenance\s+therap", r"maintenance\s+treat",
        r"switch\s+maintenance", r"continuation\s+maintenance",
        r"consolidat\w*\s+(therap|immuno|treat)",
    ]

    is_1l = any(re.search(p, text) for p in first_line_pats)
    is_2l = any(re.search(p, text) for p in later_line_pats)
    is_maint = any(re.search(p, text) for p in maintenance_pats)

    if is_1l and is_2l:
        return "Mixed (1L + 2L+)"
    elif is_1l and is_maint:
        return "1L + Maintenance"
    elif is_1l:
        return "1L (Treatment-naïve)"
    elif is_2l:
        return "2L+ (Previously treated)"
    elif is_maint:
        return "Maintenance/Consolidation"
    else:
        return "Not specified"


# --- 4d. Histology 분류 ---
def classify_histology(text):
    """Squamous vs Non-squamous 분류"""
    text = str(text).lower()

    # v2.1: adenosquamous를 먼저 체크 — "squamous" 부분문자열 매칭에 의한 오분류 방지
    adenosq = bool(re.search(r"adenosquamous", text))
    if adenosq:
        return "Both"

    sq = bool(re.search(r"squamous", text))
    non_sq = bool(re.search(r"non.?squamous|adenocarcinoma|large\s*cell", text))

    if sq and non_sq:
        return "Both"
    elif non_sq:
        return "Non-squamous"
    elif sq:
        return "Squamous"
    else:
        return "Not specified"


# --- 4e. v2: Stage 분류 ---
def classify_stage(text):
    """title / eligibility criteria에서 disease stage 추정"""
    text = str(text).lower()

    early_pats = [
        r"stage\s*i[ab]?\b", r"stage\s*ii[ab]?\b",
        r"early.?stage", r"resectable",
        r"completely\s+resected",
    ]
    locally_adv_pats = [
        r"stage\s*iii[abc]?\b",
        r"locally\s+advanced", r"unresectable.*stage\s*iii",
        r"chemoradiation", r"concurrent.*chemo.*radi",
    ]
    metastatic_pats = [
        r"stage\s*iv[abc]?\b", r"metastatic",
        r"advanced\s+(or\s+)?metastatic",
        r"m1[abc]?\b",
    ]
    # v2.1: "advanced" 단독 사용 시 (IIIB/C + IV 통칭) — locally_adv/metastatic 어디에도
    # 안 잡힌 경우에만 적용하기 위해 별도 패턴으로 분리
    advanced_standalone_pat = r"\badvanced\b"

    periop_pats = [
        r"neoadjuvant", r"adjuvant", r"perioperative",
    ]

    is_early = any(re.search(p, text) for p in early_pats)
    is_la = any(re.search(p, text) for p in locally_adv_pats)
    is_met = any(re.search(p, text) for p in metastatic_pats)
    is_periop = any(re.search(p, text) for p in periop_pats)

    stages = []
    if is_early:
        stages.append("Early (I-II)")
    if is_la:
        stages.append("Locally Advanced (III)")
    if is_met:
        stages.append("Metastatic (IV)")
    # v2.1: "advanced" 단독인데 위 패턴에 안 잡힌 경우 → Advanced (III/IV)
    if not is_la and not is_met and re.search(advanced_standalone_pat, text):
        stages.append("Advanced (III/IV)")
    if is_periop:
        stages.append("Perioperative")

    return " / ".join(stages) if stages else "Not specified"


# ============================================================
# 5. Sampling Frame 구축
# ============================================================
def build_sampling_frame(nsclc, conditions, eligibilities, interventions, sponsors):
    """각 시험에 6개 층화 기준 태깅 (v2: stage 추가)"""
    print("\n🏷️  층화 기준 태깅 중...\n")

    nct_ids = nsclc["nct_id"].unique()

    # 시험별 intervention 텍스트 합치기
    intv = interventions[interventions["nct_id"].isin(nct_ids)].copy()
    intv["combined"] = (
        intv["name"].fillna("") + " " +
        intv["description"].fillna("") + " " +
        intv["intervention_type"].fillna("")
    )
    intv_text = intv.groupby("nct_id")["combined"].apply(lambda x: " ".join(x)).reset_index()
    intv_text.columns = ["nct_id", "intervention_text"]

    # 시험별 eligibility criteria 텍스트
    elig = eligibilities[eligibilities["nct_id"].isin(nct_ids)][["nct_id", "criteria"]].copy()
    elig.columns = ["nct_id", "eligibility_text"]

    # 시험별 lead sponsor
    lead_sp = sponsors[
        (sponsors["nct_id"].isin(nct_ids)) &
        (sponsors["lead_or_collaborator"] == "lead")
    ][["nct_id", "name", "agency_class"]].copy()
    lead_sp.columns = ["nct_id", "lead_sponsor", "sponsor_type"]

    # 합치기
    frame = nsclc[["nct_id", "brief_title", "official_title", "phase",
                    "overall_status", "enrollment", "start_date", "source"]].copy()
    frame = frame.merge(intv_text, on="nct_id", how="left")
    frame = frame.merge(elig, on="nct_id", how="left")
    frame = frame.merge(lead_sp, on="nct_id", how="left")

    # 분류용 통합 텍스트
    frame["_all_text"] = (
        frame["brief_title"].fillna("") + " " +
        frame["official_title"].fillna("") + " " +
        frame["intervention_text"].fillna("") + " " +
        frame["eligibility_text"].fillna("")
    )

    # 태깅
    frame["modality"] = frame["_all_text"].apply(classify_modality)
    frame["biomarker"] = frame["_all_text"].apply(classify_biomarkers)
    frame["line_of_therapy"] = frame["_all_text"].apply(classify_line)
    frame["histology"] = frame["_all_text"].apply(classify_histology)
    frame["stage"] = frame["_all_text"].apply(classify_stage)   # v2 추가

    # Phase 정리
    frame["phase_clean"] = frame["phase"].fillna("Not Applicable").str.strip()

    # 정리
    frame.drop(columns=["_all_text"], inplace=True)

    return frame


# ============================================================
# 6. 분포 리포트
# ============================================================
def print_distribution(frame):
    """층화 기준별 분포 출력"""
    print("\n" + "=" * 60)
    print("📊  NSCLC Sampling Frame 분포 리포트")
    print("=" * 60)
    print(f"\n총 시험 수: {len(frame):,}\n")

    dims = {
        "Phase": "phase_clean",
        "Treatment Modality": "modality",
        "Biomarker": "biomarker",
        "Line of Therapy": "line_of_therapy",
        "Histology": "histology",
        "Stage": "stage",              # v2 추가
        "Sponsor Type": "sponsor_type",
    }

    for label, col in dims.items():
        print(f"\n--- {label} ---")
        counts = frame[col].value_counts()
        for val, cnt in counts.items():
            pct = cnt / len(frame) * 100
            print(f"  {val:40s}  {cnt:5,}  ({pct:5.1f}%)")


# ============================================================
# 7. 최종 선정 가이드 + 내보내기
# ============================================================
def export_frame(frame, output_path="../results/nsclc_sampling_frame.xlsx"):
    """Excel로 내보내기"""

    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 출력 컬럼 정리 (v2: stage 추가)
    export_cols = [
        "nct_id", "brief_title", "phase_clean", "overall_status",
        "enrollment", "start_date",
        "modality", "biomarker", "line_of_therapy", "histology",
        "stage",                        # v2 추가
        "lead_sponsor", "sponsor_type",
    ]
    out = frame[export_cols].copy()
    out.columns = [
        "NCT_ID", "Brief_Title", "Phase", "Status",
        "Enrollment", "Start_Date",
        "Modality", "Biomarker", "Line_of_Therapy", "Histology",
        "Stage",                        # v2 추가
        "Lead_Sponsor", "Sponsor_Type",
    ]

    # enrollment 큰 순으로 정렬 (대규모 시험이 위로)
    out = out.sort_values("Enrollment", ascending=False)

    out.to_excel(output_path, index=False, engine="openpyxl")
    print(f"\n✅ Sampling Frame 저장 완료: {output_path}")
    print(f"   → {len(out):,}건")

    # 원본 eligibility criteria 별도 저장 (annotation 작업용)
    elig_path = output_path.replace(".xlsx", "_eligibility.xlsx")
    elig_cols = ["nct_id", "brief_title", "eligibility_text"]
    elig_out = frame[elig_cols].copy()
    elig_out.columns = ["NCT_ID", "Brief_Title", "Eligibility_Criteria"]
    elig_out.to_excel(elig_path, index=False, engine="openpyxl")
    print(f"   → Eligibility Criteria 별도 저장: {elig_path}")

    return out


# ============================================================
# 8. 메인 실행
# ============================================================
def main():
    print("=" * 60)
    print("  AACT NSCLC Sampling Frame Builder (v2 — NCCN v5.2026)")
    print("  Protocol KG (Layer 1) 구축용 프로토콜 선정")
    print("=" * 60)

    # 파일 존재 확인
    missing = [k for k, v in REQUIRED_FILES.items() if not os.path.exists(v)]
    if missing:
        print(f"\n❌ 다음 파일이 없습니다: {missing}")
        print(f"   DATA_DIR 경로를 확인하세요: {DATA_DIR}")
        print(f"   https://aact.ctti-clinicaltrials.org/downloads 에서 다운로드")
        return

    # 로드 (v2: browse_conditions, keywords 추가)
    studies, conditions, eligibilities, interventions, sponsors, browse_conditions, keywords = load_all()

    # NSCLC 필터링 (v2: browse_conditions, keywords 반영)
    nsclc = filter_nsclc(studies, conditions, browse_conditions, keywords)

    if len(nsclc) == 0:
        print("\n❌ NSCLC 시험이 검출되지 않았습니다. 필터 조건을 확인하세요.")
        return

    # Sampling Frame 구축
    frame = build_sampling_frame(nsclc, conditions, eligibilities, interventions, sponsors)

    # 분포 리포트
    print_distribution(frame)

    # 내보내기
    export_frame(frame, output_path="../results/nsclc_sampling_frame.xlsx")

    # 선정 가이드
    print("\n" + "=" * 60)
    print("📋  다음 단계: 프로토콜 선정 가이드")
    print("=" * 60)
    # v2.1: NCCN 치료 경로 분기 계층에 맞게 선정 가이드 재구성
    print("""
1. results/nsclc_sampling_frame.xlsx 파일을 열어 분포를 확인하세요.

2. Primary Axis — Stage × Line of Therapy (NCCN 최상위 분기)
   NCCN의 치료 경로 분기에 대응하는 매트릭스를 기준으로
   각 셀에서 1-2개씩 선정하세요:

                          1L          2L+         Maint/Consol
   Early (I-II)          periop      —           adjuvant
   Locally Adv (III)     chemoRT     salvage     consolidation
   Metastatic (IV)       systemic    subsequent  maintenance
   Advanced (III/IV)     systemic    subsequent  maintenance

3. Secondary Axis — Biomarker × Modality (NCCN 약물 선택 분기)
   Primary Axis 각 셀 내에서 다음 다양성을 확보하세요:
   - Biomarker: EGFR, ALK, PD-L1 외에 KRAS, ROS1, BRAF, MET, RET,
     NTRK, HER2, NRG1 시험이 포함되어 있는지
   - Modality: TKI, IO, Chemo, ADC, Bispecific Ab 시험이
     고르게 포함되어 있는지

4. Coverage Check — Histology, Phase (셀 내 다양성 보장)
   - Histology: Squamous 전용 시험이 포함되어 있는지
   - Phase: I, I/II, II, III가 모두 포함되어 있는지

5. 선정 우선순위:
   - Enrollment(등록 환자수)이 큰 시험 → 임상적 대표성 높음
   - Sponsor 다양성 확보 → 특정 회사 편중 방지
   - Status: Completed > Active > Recruiting 순 권장

6. 목표 샘플 수: 30-50개

7. 선정 후 results/nsclc_sampling_frame_eligibility.xlsx에서
   해당 시험의 Eligibility Criteria 텍스트를 확인하고
   두 annotator가 독립적으로 구조화 작업을 진행하세요.
""")


if __name__ == "__main__":
    main()
