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

    return studies, conditions, eligibilities, interventions, sponsors


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


def filter_nsclc(studies, conditions):
    """NSCLC 관련 시험 필터링 (conditions + title 기반)"""

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

    all_nsclc_ids = set(cond_match) | set(title_match_brief) | set(title_match_official)

    # Interventional 시험만 필터
    nsclc = studies[
        (studies["nct_id"].isin(all_nsclc_ids)) &
        (studies["study_type"] == "Interventional")
    ].copy()

    # 유효한 status 필터 (너무 오래된 것 제외하되 넓게 잡음)
    valid_statuses = [
        "Completed", "Active, not recruiting", "Recruiting",
        "Enrolling by invitation", "Not yet recruiting",
        "Terminated", "Suspended", "Withdrawn",
    ]
    nsclc = nsclc[nsclc["overall_status"].isin(valid_statuses)]

    print(f"\n🔍 NSCLC Interventional 시험: {len(nsclc):,}건")
    print(f"   - conditions 매칭: {len(cond_match):,}")
    print(f"   - title 매칭 (추가): {len(set(title_match_brief) | set(title_match_official)) - len(cond_match):,}")

    return nsclc


# ============================================================
# 4. 층화 기준 태깅 (자동 분류)
# ============================================================

# --- 4a. Treatment Modality 분류 ---
TKI_KEYWORDS = [
    "erlotinib", "gefitinib", "afatinib", "osimertinib", "dacomitinib",
    "crizotinib", "ceritinib", "alectinib", "brigatinib", "lorlatinib",
    "selpercatinib", "pralsetinib", "capmatinib", "tepotinib",
    "sotorasib", "adagrasib", "dabrafenib", "trametinib",
    "entrectinib", "larotrectinib", "mobocertinib",
    "lazertinib", "amivantamab",
]

IO_KEYWORDS = [
    "nivolumab", "pembrolizumab", "atezolizumab", "durvalumab",
    "ipilimumab", "tremelimumab", "cemiplimab",
    "anti-pd-1", "anti-pd-l1", "anti-ctla-4",
    "pd-1", "pd-l1", "checkpoint inhibitor", "immunotherapy",
    "immune checkpoint",
]

CHEMO_KEYWORDS = [
    "cisplatin", "carboplatin", "pemetrexed", "docetaxel", "paclitaxel",
    "gemcitabine", "vinorelbine", "etoposide", "nab-paclitaxel",
    "bevacizumab", "ramucirumab",
    "chemotherapy", "platinum-based", "platinum doublet",
]

RADIATION_KEYWORDS = [
    "radiation", "radiotherapy", "chemoradiation", "sbrt",
    "stereotactic", "proton", "imrt", "igrt",
]

SURGERY_KEYWORDS = [
    "surgery", "surgical", "resection", "lobectomy", "pneumonectomy",
    "neoadjuvant", "adjuvant",
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
    if any(kw in text for kw in RADIATION_KEYWORDS):
        modalities.add("Radiation")
    if any(kw in text for kw in SURGERY_KEYWORDS):
        modalities.add("Surgery")

    if not modalities:
        modalities.add("Other/Unclassified")

    return " + ".join(sorted(modalities))


# --- 4b. Molecular Target / Biomarker 분류 ---
BIOMARKER_MAP = {
    "EGFR":     [r"egfr", r"epidermal growth factor"],
    "ALK":      [r"\balk\b", r"anaplastic lymphoma kinase"],
    "ROS1":     [r"ros1", r"ros-1"],
    "PD-L1":    [r"pd-?l1", r"programmed death.?ligand"],
    "KRAS":     [r"kras", r"k-ras"],
    "BRAF":     [r"braf", r"b-raf", r"v600e"],
    "MET":      [r"\bmet\b.*exon", r"met amplif", r"c-met"],
    "RET":      [r"\bret\b.*fusion", r"\bret\b.*rearrange", r"ret-positive"],
    "NTRK":     [r"ntrk", r"neurotrophic"],
    "HER2":     [r"her2", r"her-2", r"erbb2"],
    "STK11":    [r"stk11"],
    "TP53":     [r"tp53", r"p53"],
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

    is_1l = any(re.search(p, text) for p in first_line_pats)
    is_2l = any(re.search(p, text) for p in later_line_pats)

    if is_1l and is_2l:
        return "Mixed (1L + 2L+)"
    elif is_1l:
        return "1L (Treatment-naïve)"
    elif is_2l:
        return "2L+ (Previously treated)"
    else:
        return "Not specified"


# --- 4d. Histology 분류 ---
def classify_histology(text):
    """Squamous vs Non-squamous 분류"""
    text = str(text).lower()

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


# ============================================================
# 5. Sampling Frame 구축
# ============================================================
def build_sampling_frame(nsclc, conditions, eligibilities, interventions, sponsors):
    """각 시험에 5개 층화 기준 태깅"""
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

    # 출력 컬럼 정리
    export_cols = [
        "nct_id", "brief_title", "phase_clean", "overall_status",
        "enrollment", "start_date",
        "modality", "biomarker", "line_of_therapy", "histology",
        "lead_sponsor", "sponsor_type",
    ]
    out = frame[export_cols].copy()
    out.columns = [
        "NCT_ID", "Brief_Title", "Phase", "Status",
        "Enrollment", "Start_Date",
        "Modality", "Biomarker", "Line_of_Therapy", "Histology",
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
    print("  AACT NSCLC Sampling Frame Builder")
    print("  Protocol KG (Layer 1) 구축용 프로토콜 선정")
    print("=" * 60)

    # 파일 존재 확인
    missing = [k for k, v in REQUIRED_FILES.items() if not os.path.exists(v)]
    if missing:
        print(f"\n❌ 다음 파일이 없습니다: {missing}")
        print(f"   DATA_DIR 경로를 확인하세요: {DATA_DIR}")
        print(f"   https://aact.ctti-clinicaltrials.org/downloads 에서 다운로드")
        return

    # 로드
    studies, conditions, eligibilities, interventions, sponsors = load_all()

    # NSCLC 필터링
    nsclc = filter_nsclc(studies, conditions)

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
    print("""
1. results/nsclc_sampling_frame.xlsx 파일을 열어 분포를 확인하세요.

2. 층화 기준 5개 (Phase, Modality, Biomarker, Line, Histology)의
   주요 조합(cell)에서 최소 1-2개씩 선정하세요.

3. 선정 우선순위:
   - Enrollment(등록 환자수)이 큰 시험 → 임상적 대표성 높음
   - Sponsor 다양성 확보 → 특정 회사 편중 방지
   - Status: Completed > Active > Recruiting 순 권장

4. 목표 샘플 수: 30-50개

5. 선정 후 results/nsclc_sampling_frame_eligibility.xlsx에서
   해당 시험의 Eligibility Criteria 텍스트를 확인하고
   두 annotator가 독립적으로 구조화 작업을 진행하세요.
""")


if __name__ == "__main__":
    main()
