import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import gspread
import pandas as pd
import datetime
import io
import json
import re
from PIL import Image
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

# ==========================================
# 1. 시스템 및 API 설정
# ==========================================
st.set_page_config(page_title="원자재 표시사항 DB 시스템", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    SHEET_ID = st.secrets["GOOGLE_SHEET_ID"]
    FOLDER_ID = st.secrets["DRIVE_FOLDER_ID"]
except KeyError as e:
    st.error(f"⚠️ 시스템 설정 오류: Streamlit Secrets에 {e} 값이 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-3.8-flash"

ADMIN_PASSWORD = "2082"

FOOD_TYPES = [
    "선택하세요 (검색 가능)",

    # 1. 과자류, 빵류 또는 떡류
    "과자", "캔디류", "추잉껌", "빵류", "떡류",

    # 2. 빙과류
    "아이스크림", "저지방아이스크림", "아이스밀크", "샤베트", "비유지방아이스크림",
    "아이스크림믹스", "저지방아이스크림믹스", "아이스밀크믹스", "샤베트믹스", "비유지방아이스크림믹스",
    "빙과", "식용얼음", "어업용얼음",

    # 3. 코코아가공품류 또는 초콜릿류
    "코코아매스", "코코아버터", "코코아분말", "기타 코코아가공품",
    "초콜릿", "밀크초콜릿", "화이트초콜릿", "준초콜릿", "초콜릿가공품",

    # 4. 당류
    "설탕", "기타설탕", "당시럽류", "올리고당", "올리고당가공품",
    "포도당", "과당", "기타과당", "물엿", "기타엿", "덱스트린", "당류가공품",

    # 5. 잼류
    "잼", "기타잼",

    # 6. 두부류 또는 묵류
    "두부", "유바", "가공두부", "묵류",

    # 7. 식용유지류
    "콩기름(대두유)", "옥수수기름(옥배유)", "채종유(유채유 또는 카놀라유)",
    "미강유(현미유)", "참기름", "추출참깨유", "들기름", "추출들깨유",
    "홍화유(사플라워유 또는 잇꽃유)", "해바라기유", "목화씨기름(면실유)",
    "땅콩기름(낙화생유)", "올리브유", "팜유류", "야자유", "고추씨기름",
    "기타식물성유지", "어유", "기타동물성유지", "혼합식용유", "향미유",
    "가공유지", "쇼트닝", "마가린", "모조치즈", "식물성크림",
    "기타 식용유지가공품",

    # 8. 면류
    "생면", "숙면", "건면", "유탕면",

    # 9. 음료류
    "침출차", "액상차", "고형차", "커피", "농축과·채즙(또는 과·채분)",
    "과·채주스", "과·채음료", "탄산음료", "탄산수", "원액두유",
    "가공두유", "유산균음료", "효모음료", "기타발효음료",
    "인삼·홍삼음료", "혼합음료", "음료베이스",

    # 10. 특수영양식품
    "영아용 조제유", "성장기용 조제유",
    "영아전기용 조제식", "영아후기용 조제식", "유아기용 조제식",
    "영·유아용 이유식", "체중조절용 조제식품", "임산·수유부용식품",
    "고령자용 영양조제식품",

    # 11. 특수의료용도식품
    "일반 환자용 균형영양조제식품", "당뇨환자용 영양조제식품",
    "신장질환자용 영양조제식품", "장질환자용 단백가수분해 영양조제식품",
    "암환자용 영양조제식품", "고혈압환자용 영양조제식품",
    "폐질환자용 영양조제식품", "간경변환자용 영양조제식품",
    "열량 및 영양공급용 식품", "연하곤란자용 점도조절 식품",
    "수분 및 전해질 보충용 조제식품", "선천성대사질환자용조제식품",
    "영·유아용 특수조제식품", "기타환자용 영양조제식품",
    "당뇨환자용 식단형 식품", "신장질환자용 식단형 식품",
    "암환자용 식단형 식품", "고혈압환자용 식단형 식품",

    # 12. 장류
    "한식메주", "개량메주", "한식간장", "양조간장", "산분해간장",
    "효소분해간장", "혼합간장", "한식된장", "된장", "고추장",
    "춘장", "청국장", "혼합장", "기타장류",

    # 13. 조미식품
    "발효식초", "희석초산", "소스", "마요네즈", "토마토케첩",
    "복합조미식품", "카레(커리)분", "카레(커리)", "고춧가루",
    "실고추", "천연향신료", "향신료조제품", "천일염",
    "재제소금(재제조소금)", "태움·용융소금", "정제소금",
    "기타소금", "가공소금",

    # 14. 절임류 또는 조림류
    "김치", "김칫속", "절임식품", "당절임", "조림류",

    # 15. 주류
    "탁주", "약주", "청주", "맥주", "과실주", "소주", "위스키",
    "브랜디", "일반증류주", "리큐르", "기타 주류", "주정",

    # 16. 농산가공식품류
    "전분", "전분가공품", "밀가루", "영양강화 밀가루", "땅콩버터",
    "땅콩 또는 견과류가공품", "시리얼류", "찐쌀", "효소식품",
    "과·채가공품", "곡류가공품", "두류가공품", "서류가공품",
    "기타 농산가공품",

    # 17. 식육가공품 및 포장육
    "햄", "생햄", "프레스햄", "혼합프레스햄",
    "소시지", "발효소시지", "혼합소시지", "베이컨",
    "건조저장육", "양념육", "분쇄가공육제품", "갈비가공품", "식육케이싱",
    "식육추출가공품", "식용우지", "식용돈지", "식육간편조리세트",
    "식육함유가공품", "포장육",

    # 18. 알가공품류
    "전란액", "난황액", "난백액", "전란분", "난황분", "난백분",
    "알가열제품", "피단", "알함유가공품",

    # 19. 유가공품류
    "우유", "저지방우유", "무지방우유",
    "환원유", "환원저지방우유", "환원무지방우유",
    "강화우유", "유산균첨가우유", "유산균첨가저지방우유", "유산균첨가무지방우유",
    "유당분해우유", "유당분해저지방우유", "유당분해무지방우유",
    "가공유", "저지방가공유", "무지방가공유", "산양유",
    "발효유", "농후발효유", "크림발효유", "농후크림발효유", "발효버터유", "발효유분말",
    "버터유", "농축우유", "탈지농축우유", "가당연유", "가당탈지연유", "가공연유",
    "유크림", "가공유크림", "버터", "가공버터", "버터오일",
    "자연치즈", "가공치즈",
    "전지분유", "탈지분유", "가당분유", "혼합분유",
    "유청", "농축유청", "유청단백분말", "유당", "유단백가수분해식품", "유함유가공품",

    # 20. 수산가공식품류
    "어육살", "연육", "어육반제품", "어묵", "어육소시지",
    "기타 어육가공품", "젓갈", "양념젓갈", "액젓", "조미액젓",
    "조미건어포", "건어포", "기타 건포류",
    "가공김(조미김 또는 구운김)", "한천", "기타 수산물가공품",

    # 21. 동물성가공식품류
    "기타식육 또는 기타알", "기타동물성가공식품", "곤충가공식품",
    "자라분말", "자라분말제품", "자라유제품", "추출가공식품",

    # 22. 벌꿀 및 화분가공품류
    "벌집꿀", "벌꿀", "사양벌집꿀", "사양벌꿀", "로열젤리",
    "로열젤리제품", "가공화분", "화분함유제품",

    # 23. 즉석식품류
    "생식제품", "생식함유제품", "즉석섭취식품", "신선편의식품",
    "즉석조리식품", "간편조리세트", "만두", "만두피",

    # 24. 기타식품류
    "캡슐류", "효모식품", "기타가공품",

    # 25. 식품첨가물 및 혼합제제류 (식품첨가물공전 및 표시기준)
    "식품첨가물", "화학적합성품 식품첨가물", "천연첨가물", "혼합제제 식품첨가물",
    "영양강화제", "L-글루탐산나트륨제제", "면류첨가알칼리제", "발색제제",
    "보존료제제", "사카린나트륨제제", "타르색소제제",
    "팽창제제", "향료", "향료제제", "혼합제제",

    # 26. 건강기능식품 및 원료 (건강기능식품의 기준 및 규격 / 표시기준)
    "건강기능식품", "건강기능식품원료"
]

OLD_ALLERGENS = [
    "🟩 해당없음 (안전)", "난류(가금류)", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게", "새우",
    "돼지고기", "복숭아", "토마토", "아황산류", "호두", "닭고기", "쇠고기", "오징어", "조개류(굴, 전복, 홍합 포함)", "잣"
]

NEW_ALLERGENS = [
    "🟩 해당없음 (안전)", "참깨", "들깨", "아몬드", "캐슈넛"
]

def get_google_creds():
    try:
        creds = Credentials(
            token=None,
            refresh_token=st.secrets["google_oauth"]["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.secrets["google_oauth"]["client_id"],
            client_secret=st.secrets["google_oauth"]["client_secret"]
        )
        return creds
    except Exception as e:
        st.error(f"구글 인증 로드 실패: {e}")
        return None

# ==========================================
# 2. 구글 드라이브 & 시트 통신 함수
# ==========================================
def upload_file_to_drive(file_bytes, file_name, mime_type):
    try:
        creds = get_google_creds()
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        return uploaded_file.get('webViewLink'), uploaded_file.get('id')
    except Exception as e:
        st.error(f"드라이브 업로드 에러: {e}")
        return None, None

def download_file_from_drive(file_id):
    try:
        creds = get_google_creds()
        service = build('drive', 'v3', credentials=creds)
        request = service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        file_metadata = service.files().get(fileId=file_id, fields='mimeType').execute()
        return file_stream.getvalue(), file_metadata.get('mimeType')
    except Exception as e:
        return None, None

def append_data_to_sheet(row_data):
    try:
        creds = get_google_creds()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.sheet1
        worksheet.append_row(row_data)
        return True
    except Exception as e:
        return str(e)

def update_row_data(row_index_str, update_dict):
    try:
        creds = get_google_creds()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.sheet1

        # A~N열 구글 시트 순서 매핑
        col_map = {
            '코드': 'A', '제품명': 'B', '식품유형': 'C', '원재료명(한글표시사항)': 'D',
            '원산지': 'E', '제조원': 'F', '공급사(판매원)': 'G', '기존알레르기': 'H',
            '신규알레르기': 'I', '검증상태': 'M', '검증결과': 'N'
        }

        for key, val in update_dict.items():
            if key in col_map:
                worksheet.update_acell(f'{col_map[key]}{row_index_str}', str(val))
        return True
    except Exception as e:
        return str(e)

def load_sheet_data():
    try:
        creds = get_google_creds()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.sheet1
        df_s = pd.DataFrame(worksheet.get_all_records())
        if not df_s.empty:
            df_s.columns = [str(c).strip() for c in df_s.columns]
        return df_s
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_bom_data():
    try:
        creds = get_google_creds()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("배합비 DB")
        return pd.DataFrame(worksheet.get_all_records())
    except Exception:
        return pd.DataFrame()

def standardize_master_columns(df_m):
    """전체 원재료 명단의 컬럼명을 품목코드/품목명/거래처명으로 표준화합니다."""
    if df_m is None or df_m.empty:
        return pd.DataFrame()
    df_m = df_m.copy()
    df_m.columns = [str(c).strip() for c in df_m.columns]
    if '원자재코드' in df_m.columns and '품목코드' not in df_m.columns:
        df_m['품목코드'] = df_m['원자재코드']
    if '원자재명' in df_m.columns and '품목명' not in df_m.columns:
        df_m['품목명'] = df_m['원자재명']
    if '거래처명' not in df_m.columns:
        df_m['거래처명'] = ""
    return df_m

@st.cache_data(ttl=600)
def load_master_data():
    try:
        creds = get_google_creds()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.worksheet("전체 원재료 명단")
        df_m = pd.DataFrame(worksheet.get_all_records())
        return standardize_master_columns(df_m)
    except Exception:
        return pd.DataFrame()

# ==========================================
# 3. 공용 헬퍼 함수 (정밀 상호·품목 정규화 & 마스터 매칭)
# ==========================================
GENERIC_CORP_SUFFIXES = (
    "인터내셔널", "인터내셔날", "글로벌", "코리아", "산업", "상사", "통상", "무역",
    "유통", "물산", "화학", "케미칼", "케미컬", "바이오", "바이오켐", "푸드", "푸드텍",
    "식품", "향료", "제약", "상회", "농산", "축산", "수산", "에프앤비", "fnb", "food",
    "foods", "korea", "global", "international"
)

OEM_NOISE_TOKENS = {
    "프루티홈", "남양유업", "삼육케어", "한국메디칼푸드", "돌코리아", "비알", "빙그레",
    "빙그레880", "빙그레캐옴", "넛유", "롯데칠성", "푸르밀", "뉴트리", "태국산", "중국산",
    "호주산혼합", "소분", "20kg소분", "20kg", "foodgrade", "hy", "tof", "bk"
}

def normalize_company_name(name, strip_parens=True):
    """법인 기호, 수식어, 공백, 괄호 부가정보를 제거하여 핵심 상호명을 추출합니다."""
    if pd.isna(name):
        return ""
    s = str(name).strip()
    s = re.sub(r'^(공급사|판매원|제조원|납품업체|거래처|상호명?)\s*[:：]\s*', '', s)
    s = s.replace("㈜", " ").replace("(주)", " ").replace("（주）", " ")
    s = s.replace("(유)", " ").replace("（유）", " ").replace("(합)", " ")
    s = re.sub(r'(주식회사|유한회사|유한책임회사|합자회사|합명회사)', ' ', s)
    s = re.sub(r'\b(co\.?,?\s*ltd\.?|corp\.?|inc\.?|llc|limited|company)\b', ' ', s, flags=re.IGNORECASE)
    if strip_parens:
        s = re.sub(r'\([^)]*\)', ' ', s)
        s = re.sub(r'\[[^\]]*\]', ' ', s)
    s = re.sub(r'[^가-힣a-zA-Z0-9]', '', s).lower()
    return s

def extract_company_variants(raw_name):
    """업체명에서 본명칭, 괄호 내 약칭, 영문 발음 표기 변형을 추출합니다."""
    if pd.isna(raw_name) or not str(raw_name).strip():
        return set()
    s = str(raw_name).strip()
    variants = set()
    c_core = normalize_company_name(s, strip_parens=True)
    c_full = normalize_company_name(s, strip_parens=False)
    if c_core:
        variants.add(c_core)
    if c_full:
        variants.add(c_full)

    ignore_tags = {"주", "유", "합", "본사", "공장", "유지", "가공", "탈지", "냉장", "상온", "수입", "직거래", "인천세관장"}
    for p in re.findall(r'\(([^)]+)\)', s):
        p_clean = normalize_company_name(p, strip_parens=True)
        if p_clean and p_clean not in ignore_tags and len(p_clean) >= 2:
            variants.add(p_clean)

    expanded = set(variants)
    for v in variants:
        v_kor = (
            v.replace("hy", "에이치와이")
             .replace("fi", "에프아이")
             .replace("f&f", "에프앤에프")
             .replace("fnf", "에프앤에프")
             .replace("tof", "티오에프")
             .replace("jj", "제이제이")
             .replace("nnp", "앤앤피")
             .replace("bk", "비케이")
             .replace("tr", "티알")
             .replace("hn", "에이치엔")
             .replace("csf", "씨에스에프")
        )
        expanded.add(v_kor)
    return expanded

def is_same_company(vendor_input, master_vendor):
    """공급사(판매원)와 마스터 거래처명을 엄격 대조합니다 (무작위 짧은 단어 포함 오매칭 차단)."""
    sv_set = extract_company_variants(vendor_input)
    mv_set = extract_company_variants(master_vendor)
    if not sv_set or not mv_set:
        return False

    if sv_set & mv_set:
        return True

    for sv in sv_set:
        for mv in mv_set:
            shorter, longer = (sv, mv) if len(sv) <= len(mv) else (mv, sv)
            if len(shorter) >= 3 and longer.startswith(shorter):
                rem = longer[len(shorter):]
                if rem in GENERIC_CORP_SUFFIXES:
                    return True
    return False

def normalize_food_item(text):
    """식품첨가물 이명·영문 약어·발음 표기 차이를 표준화합니다."""
    s = re.sub(r'\s+', '', str(text).strip().lower())
    replacements = [
        ("구연산삼나트륨", "구연산나트륨"),
        ("구연산소다", "구연산나트륨"),
        ("카복시메틸셀룰로스나트륨", "cmc"),
        ("카르복시메틸셀룰로스나트륨", "cmc"),
        ("카르복시메틸셀룰로오스나트륨", "cmc"),
        ("sodiumcarboxymethylcellulose", "cmc"),
        ("carboxymethylcellulose", "cmc"),
        ("아비셀플러스", "avicel+"),
        ("아비셀", "avicel"),
        ("지피", "gp"),
        ("초코렛", "초코"),
        ("초콜렛", "초코"),
        ("초콜릿", "초코"),
        ("흑임자", "검은깨"),
        ("검은참깨", "검은깨"),
        ("정제소금", "정제염"),
        ("본소금", "정제염"),
        ("비타민-", "비타민"),
    ]
    for k, v in replacements:
        s = s.replace(k, v)
    return s

def calc_name_similarity(a, b):
    """일반 수식어('농축액', '혼합제제' 등) 착시를 배제한 품목명 유사도를 계산합니다."""
    s1 = re.sub(r'[^가-힣a-z0-9+#]', '', normalize_food_item(a))
    s2 = re.sub(r'[^가-힣a-z0-9+#]', '', normalize_food_item(b))
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    generic_words = ["혼합제제", "분말", "농축과즙", "농축액", "추출분말", "추출액", "페이스트", "시럽", "향", "과즙"]
    c1, c2 = s1, s2
    for gw in generic_words:
        if len(c1) > len(gw) + 1:
            c1 = c1.replace(gw, "")
        if len(c2) > len(gw) + 1:
            c2 = c2.replace(gw, "")

    if c1 and c2 and c1 == c2:
        return 0.95
    if c1 and c2 and len(c1) >= 3 and len(c2) >= 3 and (c1 in c2 or c2 in c1):
        return 0.85

    g1 = {s1[i:i+2] for i in range(max(1, len(s1) - 1))}
    g2 = {s2[i:i+2] for i in range(max(1, len(s2) - 1))}
    base_sim = len(g1 & g2) / max(1, len(g1 | g2))

    if c1 and c2:
        cg1 = {c1[i:i+2] for i in range(max(1, len(c1) - 1))}
        cg2 = {c2[i:i+2] for i in range(max(1, len(c2) - 1))}
        core_sim = len(cg1 & cg2) / max(1, len(cg1 | cg2))
        return (base_sim * 0.4) + (core_sim * 0.6)
    return base_sim

def extract_item_segments(name, vendor_name=""):
    """마스터 품목명의 괄호 밖 본명칭과 괄호 안 세부 모델명(고객사 노이즈 제외)을 분리 추출합니다."""
    raw = str(name).strip()
    segs = {normalize_food_item(raw)}
    outside = re.sub(r'\([^)]*\)', ' ', raw).strip()
    if outside:
        segs.add(normalize_food_item(outside))

    v_clean = re.sub(r'[^가-힣a-z0-9]', '', normalize_food_item(vendor_name))
    for grp in re.findall(r'\(([^)]+)\)', raw):
        for part in re.split(r'[,/]', grp):
            p_norm = normalize_food_item(part)
            p_alnum = re.sub(r'[^가-힣a-z0-9+#]', '', p_norm)
            if not p_alnum or len(p_alnum) < 2:
                continue
            if p_alnum in OEM_NOISE_TOKENS or (v_clean and p_alnum == v_clean):
                continue
            segs.add(p_norm)
    return {re.sub(r'[^가-힣a-z0-9+#]', '', x) for x in segs if re.sub(r'[^가-힣a-z0-9+#]', '', x)}

def smart_item_match_score(sub_name, master_name, vendor_name=""):
    """동일 거래처 내에서 업체 제출 제품명과 마스터 품목명의 정밀 일치 점수를 반환합니다."""
    sub_segs = extract_item_segments(sub_name, vendor_name)
    mst_segs = extract_item_segments(master_name, vendor_name)
    if not sub_segs or not mst_segs:
        return 0.0

    if sub_segs & mst_segs:
        return 1.0

    sub_full = normalize_food_item(sub_name)
    mst_full = normalize_food_item(master_name)
    model_mst = set(re.findall(r'(?:#\d+|[a-z]+\+?\d+[a-z0-9]*|\d{4,})', mst_full))
    model_sub = set(re.findall(r'(?:#\d+|[a-z]+\+?\d+[a-z0-9]*|\d{4,})', sub_full))
    common_models = {m for m in (model_mst & model_sub) if m not in {"100", "2000"}}
    if common_models:
        return 0.95

    generic_only = {"혼합제제", "농축액", "과즙농축액", "페이스트", "추출분말", "추출액", "분말", "시럽"}
    best = 0.0
    for ss in sub_segs:
        for ms in mst_segs:
            if len(ss) >= 3 and len(ms) >= 3 and (ss in ms or ms in ss):
                if ss not in generic_only and ms not in generic_only:
                    best = max(best, 0.88)
            sim = calc_name_similarity(ss, ms)
            if sim > best:
                best = sim
    return best

def filter_master_candidates(master_df, vendor_name, product_name):
    """전체 원재료 명단에서 1순위(동일 공급사 납품 품목) 및 2순위(품목명 유사 품목) 후보군을 압축 추출합니다."""
    if master_df.empty or '품목코드' not in master_df.columns:
        return {"공급사_일치_품목": [], "품목명_유사_참고후보": []}, pd.DataFrame()

    work_df = master_df[['품목코드', '품목명', '거래처명']].copy()
    work_df['품목코드'] = work_df['품목코드'].astype(str).str.strip()
    work_df = work_df[work_df['품목코드'] != '']

    # 1차: 공급사(판매원) ↔ 거래처명 엄격 매칭
    vendor_mask = work_df['거래처명'].apply(lambda mv: is_same_company(vendor_name, mv))
    vendor_matched_df = work_df[vendor_mask].drop_duplicates()

    # 2차: 품목명 정밀 유사도 상위 후보 추출 (공급사 오기재 대비용)
    work_df['_sim'] = work_df.apply(
        lambda r: smart_item_match_score(product_name, r['품목명'], r['거래처명']), axis=1
    )
    sim_limit = 15 if not vendor_matched_df.empty else 40
    similar_df = work_df[~vendor_mask].sort_values(by='_sim', ascending=False).head(sim_limit)
    similar_df = similar_df[similar_df['_sim'] > 0][['품목코드', '품목명', '거래처명']].drop_duplicates()

    payload = {
        "공급사_일치_품목": vendor_matched_df.to_dict(orient='records'),
        "품목명_유사_참고후보": similar_df.to_dict(orient='records')
    }
    return payload, vendor_matched_df

def extract_recommended_code(ai_text):
    """AI 응답 텍스트에서 추천매칭코드 값만 정제하여 반환합니다."""
    for line in str(ai_text).split('\n'):
        if "추천매칭코드" in line and ":" in line:
            raw = line.split(":", 1)[1].strip()
            raw = re.sub(r'[\[\]\(\)\'\"`]', '', raw).strip()
            if not raw or "없음" in raw:
                return "없음"
            code_token = raw.split()[0].strip()
            return code_token
    return "없음"

def verify_with_ai(file_bytes, mime_type, vendor_data, candidates_payload):
    candidates_json = json.dumps(candidates_payload, ensure_ascii=False)
    prompt = f"""
    당신은 식품안전팀의 엄격한 품질관리(QC) AI 검수자입니다.
    두 가지 작업을 수행하십시오.

    [작업 1: 교차 검증]
    업체가 입력한 데이터와 첨부된 라벨 문서(이미지/PDF)를 정밀하게 비교하세요.
    - 업체 데이터: 제품명({vendor_data['제품명']}), 공급사(판매원)({vendor_data.get('공급사(판매원)', '')}), 제조원({vendor_data['제조원']}), 원재료명({vendor_data['원재료명(한글표시사항)']}), 기존알레르기({vendor_data['기존알레르기']}), 신규알레르기({vendor_data['신규알레르기']})
    - 라벨 원본에 숨어있는 알레르기 성분(특히 신규 알레르기: 참깨, 들깨, 아몬드, 캐슈넛 — 흑임자는 참깨, 임자/수임은 들깨로 분류) 누락 여부를 집중 점검하세요.

    [작업 2: 사내 원자재 마스터 품목코드 자동 매칭]
    아래 제공된 '사내 원자재 후보 명단(JSON)'에서 업체가 제출한 [공급사(판매원): {vendor_data.get('공급사(판매원)', '')}] 및 [제품명: {vendor_data['제품명']}]과 일치하는 품목을 찾아 `품목코드`를 매칭하세요.
    - 1순위 원칙: `공급사_일치_품목` 리스트(해당 거래처가 당사에 납품하는 품목 목록) 안에서 제품명·모델번호·이명(예: 구연산삼나트륨=구연산나트륨, CMC=카복시메틸셀룰로스나트륨, Avicel=아비셀 등)이 일치하는 품목코드를 최우선 선택하세요.
    - 2순위 원칙: `공급사_일치_품목`에 해당 품목이 없을 때만 `품목명_유사_참고후보`를 확인하되, 거래처명이 전혀 다른 타사 OEM 전용 품목(예: 공급사가 롯데칠성이 아닌데 거래처가 롯데칠성인 코드 등)은 절대 추천하지 말고 불확실하면 '없음'으로 기재하세요.
    - 사내 원자재 후보 명단(JSON): {candidates_json}

    [출력 형식] (반드시 아래 양식을 지켜 순수 텍스트로만 출력하세요)
    판정: [합격] 또는 [불합격] (사유: ~)
    상세코멘트: (라벨 대조 및 알레르기 검증 결과 상세 작성)
    매칭근거: (선택한 사내 품목명·거래처명 및 매칭 판단 근거 요약)
    추천매칭코드: (찾아낸 품목코드만 정확히 기재. 명단에 없거나 거래처가 달라 불확실하면 '없음'으로 기재)
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        file_part = {"mime_type": mime_type, "data": file_bytes}
        response = model.generate_content([prompt, file_part])
        return response.text
    except Exception as e:
        return f"AI 분석 에러: {e}"

def render_inline_viewer(img_url):
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', str(img_url))
    if match:
        file_id = match.group(1)
        iframe_src = f"https://drive.google.com/file/d/{file_id}/preview"
        components.iframe(iframe_src, height=800, scrolling=True)
    else:
        st.markdown(f"[링크 직접 열기]({img_url})")

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def format_audit_result(text):
    text_str = str(text)
    if "[합격]" in text_str:
        return "🟢 합격"
    elif "[불합격]" in text_str:
        return "🔴 불합격"
    return text_str

def clean_allergen_text(text):
    text = str(text).replace("🟩 해당없음 (안전)", "-").strip()
    text = re.sub(r'[⚠️🚨]', '', text).strip()
    if not text:
        return "-"
    return text

def highlight_new_allergens(text):
    text = str(text)
    targets = ["참깨", "들깨", "아몬드", "캐슈넛"]
    has_target = any(t in text for t in targets)

    if has_target:
        return f'<span style="background-color: #ffcccc; color: #cc0000; padding: 2px 6px; border-radius: 4px; font-weight: bold;">{text}</span>'
    return text

# ==========================================
# 4. 화면 라우팅 (관리자 vs 협력업체)
# ==========================================
with st.sidebar:
    st.markdown("### 🔐 식품안전팀 관리자 로그인")
    user_pw = st.text_input("접속 암호를 입력하세요:", type="password")

is_admin = (user_pw == ADMIN_PASSWORD)

if not is_admin:
    # ----------------------------------------------------
    # [프론트엔드] 협력업체 다중 등록 폼
    # ----------------------------------------------------
    st.title("🤝 원자재 라벨 및 표시사항 다중 등록 시스템")

    st.markdown("""
    <div style="background-color: #f0f7ff; padding: 15px; border-radius: 8px; border-left: 5px solid #0056b3; margin-bottom: 20px;">
    <strong>📢 [안내] 원자재 알레르기 유발물질 선제적 전수조사 및 DB화</strong><br>
    식약처 법규 개정에 따라 향후 <strong>알레르기 유발물질 의무 표시 대상 확대(참깨, 들깨, 아몬드, 캐슈넛 추가)가 시행될 예정</strong>입니다. <br>
    연세유업은 제도 시행 전 <strong>선제적인 파악 및 대응</strong>을 통해 완벽한 법규 준수와 소비자 안전을 확보하고자, 협력업체에서 납품하시는 모든 원료의 <strong>'원본 라벨(한글표시사항)' 및 '성분 정보'</strong>를 전수조사 중입니다. 정확한 품질관리를 위해 사업자등록증 상의 정보와 라벨 원본 내용을 똑같이 기재해 주시기를 당부드립니다.
    </div>
    """, unsafe_allow_html=True)

    if "item_count" not in st.session_state:
        st.session_state.item_count = 1

    st.markdown("### 📝 제출 품목 개수 설정")
    col_num1, col_num2, col_num3 = st.columns([3, 2, 5])
    with col_num1:
        new_count = st.number_input("연세유업 납품 품목 개수를 적으세요 (제한 없음)", min_value=1, value=st.session_state.item_count, step=1)
    with col_num2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("입력칸 개수 적용 / 추가하기", type="secondary"):
            st.session_state.item_count = new_count
            st.rerun()

    st.markdown("<hr style='border:2px solid #ddd'>", unsafe_allow_html=True)

    if "vendor_maker" not in st.session_state:
        st.session_state.vendor_maker = ""
    if "vendor_items" not in st.session_state:
        st.session_state.vendor_items = [{} for _ in range(100)]

    def save_maker():
        st.session_state.vendor_maker = st.session_state.maker_input
    def save_item(idx, key, val):
        st.session_state.vendor_items[idx][key] = val

    def reset_form():
        st.session_state.vendor_maker = ""
        st.session_state.vendor_items = [{} for _ in range(100)]
        st.session_state.item_count = 1

    st.markdown("### 🏢 공급사(판매원) 정보")
    st.caption("💡 연세유업에 원료를 직접 공급하시는 공급사(판매원)명을 사업자등록증 기준으로 기재해 주세요.")
    v_vendor_global = st.text_input(
        "공급사(판매원)명을 적어주세요 (사업자등록증 기준 필수 기재)",
        value=st.session_state.vendor_maker,
        key="maker_input",
        on_change=save_maker
    )
    st.markdown("---")

    items_data = []

    for i in range(int(st.session_state.item_count)):
        st.markdown(f"#### 📌 제출 품목 {i+1}")

        current_data = st.session_state.vendor_items[i]

        # 1열: 제품명 및 식품유형 (원산지 입력칸 제거 유지)
        col1, col2 = st.columns(2)
        with col1:
            v_name = st.text_input(
                "🏷️ 제품명 (라벨 표기 기준, 필수)",
                value=current_data.get('name', ''),
                key=f"name_{i}"
            )
            save_item(i, 'name', v_name)

        with col2:
            default_type_idx = 0
            if current_data.get('type') in FOOD_TYPES:
                default_type_idx = FOOD_TYPES.index(current_data['type'])

            v_type = st.selectbox(
                "분류 식품유형 (타이핑하여 검색 가능, 필수)",
                options=FOOD_TYPES,
                index=default_type_idx,
                key=f"type_{i}"
            )
            save_item(i, 'type', v_type)

        # 2열: 품목별 제조원 및 '공급사(판매원)와 동일' 체크박스 + 우측 설명란
        col_m1, col_m2 = st.columns([2, 2])
        with col_m1:
            same_as_vendor = st.checkbox(
                "✅ 제조원과 공급사(판매원)가 동일한 경우 체크해주세요",
                value=current_data.get('same_maker', False),
                key=f"same_maker_{i}"
            )
            save_item(i, 'same_maker', same_as_vendor)

            if same_as_vendor:
                v_item_maker = v_vendor_global
                st.text_input(
                    "🏭 제조원 (공급사(판매원)와 동일 자동적용)",
                    value=v_vendor_global,
                    disabled=True,
                    key=f"maker_disabled_{i}"
                )
            else:
                v_item_maker = st.text_input(
                    "🏭 제조원 (라벨 표기 기준 실제 제조원, 필수)",
                    value=current_data.get('item_maker', ''),
                    placeholder="한글표시사항(라벨)에 표기된 실제 제조원(생산공장/해외제조사 등)을 기재하세요",
                    key=f"item_maker_{i}"
                )
            save_item(i, 'item_maker', v_item_maker)

        with col_m2:
            st.markdown(
                """
                <div style="background-color: #f8f9fa; padding: 12px 15px; border-radius: 6px; border-left: 4px solid #0056b3; margin-top: 10px; font-size: 13.5px; color: #333; line-height: 1.5;">
                <strong>💡 제조원 작성 안내</strong><br>
                • <strong>제조원과 공급사(판매원)가 동일한 경우:</strong> 좌측 체크박스를 체크하시면 상단의 공급사(판매원)명이 자동 입력됩니다.<br>
                • <strong>수입 원료 또는 타사 제조품을 납품하시는 경우:</strong> 체크하지 마시고 라벨에 표기된 <strong>실제 제조원명</strong>을 직접 기재해 주세요.
                </div>
                """,
                unsafe_allow_html=True
            )

        # 백엔드 전송 및 DB 호환을 위해 원산지 값은 빈칸으로 유지
        v_origin = ""

        # 3열: 기존/신규 알레르기 및 원재료명
        col4, col5 = st.columns([2, 2])
        with col4:
            v_old_allergy = st.multiselect(
                "⚠️ 기존 알레르기 물질 (필수 체크)",
                options=OLD_ALLERGENS,
                default=current_data.get('old_allergy', []),
                key=f"oa_{i}"
            )
            save_item(i, 'old_allergy', v_old_allergy)

            v_new_allergy = st.multiselect(
                "🚨 신규 알레르기 물질 (필수 체크)",
                options=NEW_ALLERGENS,
                default=current_data.get('new_allergy', []),
                key=f"na_{i}"
            )
            save_item(i, 'new_allergy', v_new_allergy)

        with col5:
            v_ingredients = st.text_area(
                "📝 원재료명 및 함량 (쉼표로 구분하여 전부 기재)",
                value=current_data.get('ingredients', ''),
                height=120,
                key=f"ing_{i}"
            )
            save_item(i, 'ingredients', v_ingredients)

        uploaded_file = st.file_uploader("📸 원본 라벨 첨부 (PDF/JPG 필수)", type=['jpg', 'jpeg', 'png', 'pdf'], key=f"file_{i}")

        items_data.append({
            "name": v_name, "type": v_type, "vendor": v_vendor_global, "maker": v_item_maker, "origin": v_origin,
            "old_allergy": v_old_allergy, "new_allergy": v_new_allergy,
            "ingredients": v_ingredients, "file": uploaded_file
        })

        st.markdown("<hr style='border:1px dashed #ccc'>", unsafe_allow_html=True)

    st.info("💡 모든 입력칸은 작성 즉시 자동 임시저장됩니다. 중간에 화면을 이동해도 내용이 유지됩니다.")

    col_submit, col_reset = st.columns([8, 2])
    with col_submit:
        submit_btn = st.button("📤 작성한 품목 모두 제출하기", type="primary", use_container_width=True)
    with col_reset:
        if st.button("🗑️ 전체 비우기", use_container_width=True):
            reset_form()
            st.rerun()

    if submit_btn:
        error_found = False

        if not v_vendor_global:
            st.error("❌ 상단에 [공급사(판매원)]을 반드시 입력해 주세요.")
            error_found = True

        for idx, item in enumerate(items_data):
            if not item['name'] or item['type'] == "선택하세요 (검색 가능)" or not item['maker'] or not item['ingredients'] or not item['file']:
                st.error(f"❌ [품목 {idx+1}] 필수 항목(제품명, 식품유형, 제조원, 원재료명, 파일 첨부)이 누락되었습니다.")
                error_found = True

            if not item['old_allergy']:
                st.error(f"❌ [품목 {idx+1}] 기존 알레르기 포함 여부를 체크해 주세요. (없으면 '해당없음')")
                error_found = True
            elif "🟩 해당없음 (안전)" in item['old_allergy'] and len(item['old_allergy']) > 1:
                st.error(f"❌ [품목 {idx+1}] 기존 알레르기에서 '해당없음'과 다른 물질을 중복 선택할 수 없습니다.")
                error_found = True

            if not item['new_allergy']:
                st.error(f"❌ [품목 {idx+1}] 신규 알레르기 포함 여부를 체크해 주세요. (없으면 '해당없음')")
                error_found = True
            elif "🟩 해당없음 (안전)" in item['new_allergy'] and len(item['new_allergy']) > 1:
                st.error(f"❌ [품목 {idx+1}] 신규 알레르기에서 '해당없음'과 다른 물질을 중복 선택할 수 없습니다.")
                error_found = True

        if not error_found:
            progress_bar = st.progress(0)
            status_text = st.empty()

            success_count = 0
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            total = len(items_data)

            for idx, item in enumerate(items_data):
                progress_pct = int(((idx) / total) * 100)
                progress_bar.progress(progress_pct / 100.0)
                status_text.info(f"총 {total}건 중 {idx+1}번째 품목({item['name']}) 라벨을 안전하게 전송 중입니다... ({progress_pct}%)")

                file_bytes = item['file'].getvalue()
                file_mime_type = item['file'].type
                ext = ".pdf" if "pdf" in file_mime_type.lower() else ".jpg"
                file_name = f"업체제출_{item['name']}_{current_time}_{idx+1}{ext}"

                drive_link, file_id = upload_file_to_drive(file_bytes, file_name, file_mime_type)

                if drive_link and file_id:
                    # 구글 시트 열 순서(A~N열):
                    # A:코드, B:제품명, C:식품유형, D:원재료명(한글표시사항), E:원산지, F:제조원, G:공급사(판매원),
                    # H:기존알레르기, I:신규알레르기, J:제출일시, K:이미지링크, L:파일ID, M:검증상태, N:검증결과
                    row_data = [
                        "", item['name'], item['type'], item['ingredients'], item['origin'], item['maker'],
                        item['vendor'], ", ".join(item['old_allergy']), ", ".join(item['new_allergy']), current_time,
                        drive_link, file_id, "대기중", "검증전"
                    ]
                    res = append_data_to_sheet(row_data)
                    if res == True:
                        success_count += 1
                    else:
                        st.error(f"[품목 {idx+1}] 저장 중 에러가 발생했습니다: {res}")
                else:
                    st.error(f"[품목 {idx+1}] 파일 업로드에 실패했습니다.")

            progress_bar.progress(1.0)
            status_text.success("전송 완료!")

            if success_count == total:
                st.success(f"🎉 총 {success_count}건의 품목 전체가 성공적으로 제출되었습니다! 협조해 주셔서 감사합니다.")
                reset_form()
                st.balloons()
            elif success_count > 0:
                st.warning(f"일부 품목만 제출되었습니다. ({success_count}/{total}건 성공)")

else:
    # ----------------------------------------------------
    # [백엔드] 식품안전팀 관리자 대시보드
    # ----------------------------------------------------
    st.title("🛡️ 식품안전팀 품질관리 통합 대시보드")

    admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5 = st.tabs([
        "📊 제출 현황판", "🤖 AI 교차 검증 및 코드 승인", "🔍 등록 DB 검색", "🚨 배합비 역추적", "📋 완제품 알레르기 마스터"
    ])

    df = load_sheet_data()
    master_df = standardize_master_columns(load_master_data())

    # ------------------ [탭 1: 수취 현황판 (미제출 독촉 & 승인 관리 분리)] ------------------
    with admin_tab1:
        col_t1_title, col_t1_btn = st.columns([8, 2])
        with col_t1_title:
            st.markdown("### 📈 협력업체 라벨 제출 현황 및 승인 관제")
            st.caption("① 아예 안 낸 업체 명단, ② 낸 업체 중 누락 품목(승인·미승인 무관), ③ 내부 승인/미승인 현황을 각각 분리하여 관리합니다.")
        with col_t1_btn:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 최신 데이터 불러오기", key="t1_btn_refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        if not master_df.empty and '품목코드' in master_df.columns:
            master_view = master_df.copy()
            master_view['품목코드'] = master_view['품목코드'].astype(str).str.strip()
            master_view = master_view[master_view['품목코드'] != ''].reset_index(drop=True)
            master_view['거래처명_원본'] = master_view['거래처명'].fillna('').astype(str).str.strip()
            master_view['거래처_표시명'] = master_view['거래처명_원본'].apply(lambda x: x if x else "(거래처 미기재)")
            has_biz_col = '사업자번호' in master_view.columns

            total_items = len(master_view)

            # 시트1 전체 제출 데이터 정리
            valid_sub_df = pd.DataFrame()
            if not df.empty:
                valid_sub_df = df.copy()
                for req_col in ['코드', '제품명', '공급사(판매원)', '제조원', '검증상태', '제출일시']:
                    if req_col not in valid_sub_df.columns:
                        valid_sub_df[req_col] = ""
                non_empty_mask = (
                    (valid_sub_df['제품명'].astype(str).str.strip() != '') |
                    (valid_sub_df['공급사(판매원)'].astype(str).str.strip() != '') |
                    (valid_sub_df['제조원'].astype(str).str.strip() != '')
                )
                valid_sub_df = valid_sub_df[non_empty_mask].copy()
                valid_sub_df['코드'] = valid_sub_df['코드'].astype(str).str.strip()
                valid_sub_df['검증상태'] = valid_sub_df['검증상태'].astype(str).str.strip()

            # 마스터 거래처별 인덱스 구성
            vendor_meta = {}
            for v_disp, grp in master_view.groupby('거래처_표시명', sort=False):
                raw_v = grp['거래처명_원본'].iloc[0]
                vendor_meta[v_disp] = {
                    'raw': raw_v,
                    'norm_full': normalize_company_name(raw_v, strip_parens=False),
                    'norm_core': normalize_company_name(raw_v, strip_parens=True),
                    'items': grp['품목명'].astype(str).tolist()
                }

            code_to_vendors = {}
            for _, r in master_view.iterrows():
                c_val = r['품목코드']
                code_to_vendors.setdefault(c_val, []).append(r['거래처_표시명'])
            code_to_vendors = {k: list(dict.fromkeys(v)) for k, v in code_to_vendors.items()}

            # 시트1 제출 행 -> 마스터 거래처 1곳 매핑
            def match_company_to_master_vendor(comp_str, prod_name, candidate_vendors=None):
                v_full = normalize_company_name(comp_str, strip_parens=False)
                v_core = normalize_company_name(comp_str, strip_parens=True)
                if not v_full and not v_core:
                    return None
                target_list = candidate_vendors if candidate_vendors is not None else [
                    k for k in vendor_meta.keys() if k != "(거래처 미기재)"
                ]

                def pick_best(matches):
                    if len(matches) == 1:
                        return matches[0]
                    best_v, best_sim = matches[0], -1.0
                    for mv in matches:
                        sims = [calc_name_similarity(prod_name, it) for it in vendor_meta[mv]['items']]
                        max_s = max(sims) if sims else 0.0
                        if max_s > best_sim:
                            best_sim = max_s
                            best_v = mv
                    return best_v

                m1 = [mv for mv in target_list if v_full and vendor_meta[mv]['norm_full'] == v_full]
                if m1:
                    return pick_best(m1)
                m2 = [mv for mv in target_list if v_core and vendor_meta[mv]['norm_core'] == v_core]
                if m2:
                    return pick_best(m2)
                m3 = []
                for mv in target_list:
                    mc = vendor_meta[mv]['norm_core']
                    mf = vendor_meta[mv]['norm_full']
                    for a, b in [(v_core, mc), (v_full, mf), (v_core, mf), (v_full, mc)]:
                        if len(a) >= 2 and len(b) >= 2 and (a in b or b in a):
                            m3.append(mv)
                            break
                if m3:
                    return pick_best(m3)
                return None

            def assign_row_vendor(s_row):
                s_code = str(s_row.get('코드', '')).strip()
                s_prod = str(s_row.get('제품명', '')).strip()
                s_vendor = str(s_row.get('공급사(판매원)', '')).strip()
                s_maker = str(s_row.get('제조원', '')).strip()

                if s_code and s_code in code_to_vendors:
                    c_vendors = code_to_vendors[s_code]
                    if len(c_vendors) == 1:
                        return c_vendors[0]
                    m_c = (
                        match_company_to_master_vendor(s_vendor, s_prod, c_vendors)
                        or match_company_to_master_vendor(s_maker, s_prod, c_vendors)
                    )
                    if m_c:
                        return m_c

                m_v = match_company_to_master_vendor(s_vendor, s_prod)
                if m_v:
                    return m_v
                m_m = match_company_to_master_vendor(s_maker, s_prod)
                if m_m:
                    return m_m
                return None

            if not valid_sub_df.empty:
                valid_sub_df['_매칭거래처'] = valid_sub_df.apply(assign_row_vendor, axis=1)
                unmatched_sub_df = valid_sub_df[valid_sub_df['_매칭거래처'].isna()].copy()
            else:
                unmatched_sub_df = pd.DataFrame()

            # 승인 전 대기중 품목의 제품명 <-> 마스터 품목명 대조 점수 함수
            def normalize_item_text(t):
                s = str(t).strip().lower()
                s = s.replace("구연산삼나트륨", "구연산나트륨").replace("흑임자", "검은깨")
                s = re.sub(r'[^가-힣a-z0-9]', '', s)
                return s

            def item_pair_score(sub_name, master_name, vendor_name=""):
                sn = normalize_item_text(sub_name)
                if not sn:
                    return 0.0
                candidates = [master_name]
                outside = re.sub(r'\([^)]*\)', '', str(master_name)).strip()
                if outside:
                    candidates.append(outside)
                v_norm = normalize_item_text(vendor_name)
                for m in re.findall(r'\(([^)]+)\)', str(master_name)):
                    mn = normalize_item_text(m)
                    if mn and mn != v_norm and len(mn) >= 2:
                        candidates.append(m)

                best = 0.0
                for cand in candidates:
                    cn = normalize_item_text(cand)
                    if not cn:
                        continue
                    if sn == cn:
                        return 1.0
                    sim = calc_name_similarity(sn, cn)
                    if len(sn) >= 2 and len(cn) >= 2 and (sn in cn or cn in sn):
                        sim = max(sim, 0.75)
                    if sim > best:
                        best = sim
                return best

            # 마스터 품목별 상태 판별: 승인여부(코드 확정) vs 제출여부_통합(승인+대기중 모두 포함)
            master_view['승인여부'] = False
            master_view['제출여부_통합'] = False
            master_view['매칭된_제출제품명'] = ""
            master_view['업체_미분류_대기건'] = ""

            zero_vendor_list = []
            submitted_vendor_names = set()

            code_vendor_counts = master_view['품목코드'].value_counts().to_dict()
            all_approved_codes = set()
            if not valid_sub_df.empty:
                all_approved_codes = set(valid_sub_df[valid_sub_df['코드'] != '']['코드'].tolist())

            for v_disp, grp in master_view.groupby('거래처_표시명', sort=False):
                m_indices = grp.index.tolist()
                if not valid_sub_df.empty:
                    v_subs = valid_sub_df[valid_sub_df['_매칭거래처'] == v_disp].copy()
                else:
                    v_subs = pd.DataFrame()

                # 단일 거래처 코드인데 코드 승인만 되어 있는 건 보완
                approved_by_single_code_idx = set()
                for idx in m_indices:
                    mc = master_view.loc[idx, '품목코드']
                    if code_vendor_counts.get(mc, 1) == 1 and mc in all_approved_codes:
                        approved_by_single_code_idx.add(idx)

                if v_subs.empty and not approved_by_single_code_idx:
                    # 아예 1건도 안 낸 전면 미제출 업체
                    biz_str = ""
                    if has_biz_col:
                        biz_vals = [str(x).strip() for x in grp['사업자번호'].unique() if str(x).strip()]
                        biz_str = ", ".join(biz_vals)
                    item_list_str = ", ".join([f"[{r['품목코드']}] {r['품목명']}" for _, r in grp.iterrows()])
                    zero_vendor_list.append({
                        '거래처명': v_disp,
                        '사업자번호': biz_str,
                        '미제출 품목수': len(grp),
                        '마스터 등록 품목 목록': item_list_str
                    })
                    continue

                submitted_vendor_names.add(v_disp)

                # 1단계: 코드 승인된 건 매칭
                used_sub_indices = set()
                matched_m_indices = set()

                for idx in approved_by_single_code_idx:
                    master_view.loc[idx, '승인여부'] = True
                    master_view.loc[idx, '제출여부_통합'] = True
                    matched_m_indices.add(idx)

                if not v_subs.empty:
                    coded_subs = v_subs[v_subs['코드'] != '']
                    for s_idx, s_row in coded_subs.iterrows():
                        sc = s_row['코드']
                        for idx in m_indices:
                            if master_view.loc[idx, '품목코드'] == sc:
                                master_view.loc[idx, '승인여부'] = True
                                master_view.loc[idx, '제출여부_통합'] = True
                                master_view.loc[idx, '매칭된_제출제품명'] = str(s_row.get('제품명', ''))
                                matched_m_indices.add(idx)
                                used_sub_indices.add(s_idx)

                # 2단계: 승인 전(코드 빈칸) 대기중 제출건 매칭 (승인·미승인 구분 없이 제출 인정)
                rem_m_indices = [idx for idx in m_indices if idx not in matched_m_indices]
                rem_subs = v_subs[~v_subs.index.isin(used_sub_indices)] if not v_subs.empty else pd.DataFrame()

                if len(m_indices) == 1 and len(rem_m_indices) == 1 and not rem_subs.empty:
                    only_idx = rem_m_indices[0]
                    first_s_idx = rem_subs.index[0]
                    master_view.loc[only_idx, '제출여부_통합'] = True
                    master_view.loc[only_idx, '매칭된_제출제품명'] = str(rem_subs.loc[first_s_idx, '제품명'])
                    matched_m_indices.add(only_idx)
                    used_sub_indices.add(first_s_idx)
                elif rem_m_indices and not rem_subs.empty:
                    pair_candidates = []
                    for idx in rem_m_indices:
                        m_name = master_view.loc[idx, '품목명']
                        for s_idx, s_row in rem_subs.iterrows():
                            s_name = str(s_row.get('제품명', ''))
                            sc_val = item_pair_score(s_name, m_name, v_disp)
                            if sc_val >= 0.55:
                                pair_candidates.append((sc_val, idx, s_idx, s_name))
                    pair_candidates.sort(key=lambda x: x[0], reverse=True)
                    for sc_val, idx, s_idx, s_name in pair_candidates:
                        if idx not in matched_m_indices and s_idx not in used_sub_indices:
                            master_view.loc[idx, '제출여부_통합'] = True
                            master_view.loc[idx, '매칭된_제출제품명'] = s_name
                            matched_m_indices.add(idx)
                            used_sub_indices.add(s_idx)

                # 해당 업체에 제품명이 마스터와 전혀 달라 자동 연결 안 된 대기건이 남았다면 비고 표시
                leftover_subs = v_subs[~v_subs.index.isin(used_sub_indices)] if not v_subs.empty else pd.DataFrame()
                if not leftover_subs.empty:
                    leftover_names = ", ".join(leftover_subs['제품명'].astype(str).tolist())
                    for idx in m_indices:
                        if not master_view.loc[idx, '제출여부_통합']:
                            master_view.loc[idx, '업체_미분류_대기건'] = f"대기중 타명칭 제출있음: {leftover_names}"

            # 결과 데이터프레임 분리
            zero_vendors_df = pd.DataFrame(zero_vendor_list)

            # [그룹 2] 1건 이상 제출한 업체 중, 승인·미승인 구분 없이 아직 안 들어온 누락 품목 리스트
            partial_missing_items_df = master_view[
                (master_view['거래처_표시명'].isin(submitted_vendor_names)) &
                (master_view['제출여부_통합'] == False)
            ].copy()
            partial_missing_items_df['거래처명'] = partial_missing_items_df['거래처_표시명']

            # [그룹 3] 내부 검수 관리용 (승인 vs 미승인)
            approved_master_df = master_view[master_view['승인여부'] == True].copy()
            unapproved_master_df = master_view[master_view['승인여부'] == False].copy()
            pending_sheet_df = valid_sub_df[valid_sub_df['검증상태'] == '대기중'].copy() if not valid_sub_df.empty else pd.DataFrame()

            total_submitted_master_cnt = int(master_view['제출여부_통합'].sum())
            total_approved_master_cnt = len(approved_master_df)
            submit_rate_pct = round((total_submitted_master_cnt / total_items) * 100, 1) if total_items > 0 else 0.0
            approve_rate_pct = round((total_approved_master_cnt / total_items) * 100, 1) if total_items > 0 else 0.0

            # 상단 요약 지표 (독촉 관점 + 승인 관점 분리 표시)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("🔴 아예 안 낸 업체 (0건 제출)", f"{len(zero_vendors_df)}개사")
            k2.metric("🟡 낸 업체의 누락 품목 (승인·미승인 무관)", f"{len(partial_missing_items_df)}건", f"{partial_missing_items_df['거래처명'].nunique() if not partial_missing_items_df.empty else 0}개사")
            k3.metric("🔵 시트1 미승인(검수 대기중)", f"{len(pending_sheet_df)}건")
            k4.metric("🟢 마스터 코드 승인 완료", f"{total_approved_master_cnt} / {total_items}건", f"승인률 {approve_rate_pct}%")

            st.progress(min(1.0, submit_rate_pct / 100.0))
            st.markdown(
                f"**[제출 기준(승인·미승인 합산)] 전체 {total_items}건 중 {total_submitted_master_cnt}건 접수 ({submit_rate_pct}%)** "
                f"&nbsp;|&nbsp; **[승인 기준] {total_approved_master_cnt}건 코드 확정 ({approve_rate_pct}%)**"
            )

            st.markdown("---")

            # 목적별로 완전히 분리된 4개 서브탭
            sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
                f"🔴 1. 아예 안 낸 업체 명단 ({len(zero_vendors_df)}개사)",
                f"🟡 2. 낸 업체 중 누락 품목 ({len(partial_missing_items_df)}건)",
                f"⚖️ 3. 승인 / 미승인 검수 현황 (대기 {len(pending_sheet_df)}건 · 승인 {total_approved_master_cnt}건)",
                f"⚠️ 4. 상호 미매칭 제출건 확인 ({len(unmatched_sub_df)}건)"
            ])

            # [서브탭 1] 아예 1건도 제출하지 않은 업체 명단
            with sub_tab1:
                st.caption("승인·미승인 구분 없이 '시트1'에 단 1건도 제출하지 않은 업체 명단입니다.")
                if zero_vendors_df.empty:
                    st.success("🎉 전면 미제출 업체가 없습니다!")
                else:
                    q_zero = st.text_input("🔍 업체명 또는 품목명 검색:", key="t1_zero_search")
                    view_zero = zero_vendors_df.copy()
                    if q_zero.strip():
                        kw = q_zero.strip()
                        view_zero = view_zero[
                            view_zero['거래처명'].astype(str).str.contains(kw, case=False, na=False) |
                            view_zero['마스터 등록 품목 목록'].astype(str).str.contains(kw, case=False, na=False)
                        ]

                    zero_cols = (
                        ['거래처명', '사업자번호', '미제출 품목수', '마스터 등록 품목 목록']
                        if has_biz_col else
                        ['거래처명', '미제출 품목수', '마스터 등록 품목 목록']
                    )
                    st.dataframe(
                        view_zero[zero_cols].sort_values(by='미제출 품목수', ascending=False),
                        use_container_width=True,
                        hide_index=True
                    )

                    c_dl1, c_dl2 = st.columns(2)
                    with c_dl1:
                        st.download_button(
                            label=f"📥 아예 안 낸 업체 명단 다운로드 ({len(view_zero)}개사 / CSV)",
                            data=convert_df_to_csv(view_zero[zero_cols]),
                            file_name="전면_미제출_업체명단.csv",
                            mime="text/csv",
                            key="t1_dl_zero_vendors"
                        )
                    with c_dl2:
                        zero_v_set = set(view_zero['거래처명'].tolist())
                        z_item_cols = ['품목코드', '품목명', '거래처명', '사업자번호'] if has_biz_col else ['품목코드', '품목명', '거래처명']
                        z_items_df = master_view[master_view['거래처_표시명'].isin(zero_v_set)].copy()
                        z_items_df['거래처명'] = z_items_df['거래처_표시명']
                        st.download_button(
                            label=f"📥 아예 안 낸 업체의 품목별 상세 다운로드 ({len(z_items_df)}건 / CSV)",
                            data=convert_df_to_csv(z_items_df[z_item_cols]),
                            file_name="전면_미제출_품목상세.csv",
                            mime="text/csv",
                            key="t1_dl_zero_items"
                        )

            # [서브탭 2] 낸 업체 중 누락된 품목과 거래처명 (승인·미승인 무관)
            with sub_tab2:
                st.caption("1건 이상 제출한 업체들 중에서, 이미 제출된 품목(승인완료 + 미승인 대기중 모두 포함)을 제외하고 아직 빠진 '누락 품목'과 '거래처명' 리스트입니다.")
                if partial_missing_items_df.empty:
                    st.success("🎉 제출 업체 중 누락된 품목이 없습니다!")
                else:
                    q_part = st.text_input("🔍 누락 품목명, 품목코드 또는 거래처명 검색:", key="t1_part_search")
                    view_part_items = partial_missing_items_df.copy()
                    if q_part.strip():
                        kw_p = q_part.strip()
                        view_part_items = view_part_items[
                            view_part_items['품목명'].astype(str).str.contains(kw_p, case=False, na=False) |
                            view_part_items['품목코드'].astype(str).str.contains(kw_p, case=False, na=False) |
                            view_part_items['거래처명'].astype(str).str.contains(kw_p, case=False, na=False)
                        ]

                    part_item_cols = ['품목코드', '품목명', '거래처명']
                    if has_biz_col:
                        part_item_cols.append('사업자번호')
                    if (view_part_items['업체_미분류_대기건'] != "").any():
                        part_item_cols.append('업체_미분류_대기건')

                    st.dataframe(
                        view_part_items[part_item_cols].sort_values(by=['거래처명', '품목코드']),
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        label=f"📥 제출 업체 중 누락 품목 리스트 다운로드 ({len(view_part_items)}건 / CSV)",
                        data=convert_df_to_csv(view_part_items[part_item_cols]),
                        file_name="제출업체_누락품목_리스트.csv",
                        mime="text/csv",
                        key="t1_dl_part_items"
                    )

                    st.markdown("#### 🔎 특정 거래처 선택 시 [누락 품목 vs 실제 제출 내역(승인+대기)] 비교")
                    part_vendor_opts = sorted(view_part_items['거래처명'].unique().tolist())
                    sel_v = st.selectbox(
                        "확인할 거래처를 선택하세요:",
                        options=["선택하세요"] + part_vendor_opts,
                        key="t1_sel_part_vendor"
                    )
                    if sel_v != "선택하세요":
                        cd1, cd2 = st.columns(2)
                        with cd1:
                            v_miss = view_part_items[view_part_items['거래처명'] == sel_v][['품목코드', '품목명']]
                            st.error(f"🔴 [{sel_v}] 누락 품목 ({len(v_miss)}건)")
                            st.dataframe(v_miss, use_container_width=True, hide_index=True)
                        with cd2:
                            v_sub_list = valid_sub_df[valid_sub_df['_매칭거래처'] == sel_v] if not valid_sub_df.empty else pd.DataFrame()
                            st.info(f"📥 [{sel_v}] 시트1 실제 제출 내역 ({len(v_sub_list)}건 — 승인·대기 포함)")
                            if not v_sub_list.empty:
                                s_cols = [c for c in ['검증상태', '코드', '제품명', '공급사(판매원)', '제조원', '제출일시'] if c in v_sub_list.columns]
                                st.dataframe(v_sub_list[s_cols], use_container_width=True, hide_index=True)

            # [서브탭 3] 내부 검수 관리: 승인 vs 미승인 별도 관리
            with sub_tab3:
                st.caption("독촉 명단과 별개로, 우리 팀 내부 검수 기준인 '미승인(검수 대기)' 건과 '승인 완료(마스터 코드 확정)' 건을 따로 관리합니다.")
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    st.warning(f"🔵 시트1 미승인(검수 대기중) 제출 목록 ({len(pending_sheet_df)}건)")
                    if pending_sheet_df.empty:
                        st.success("현재 미승인 대기 건이 없습니다.")
                    else:
                        p_cols = [c for c in ['제품명', '공급사(판매원)', '제조원', '식품유형', '제출일시'] if c in pending_sheet_df.columns]
                        st.dataframe(pending_sheet_df[p_cols], use_container_width=True, hide_index=True)
                with col_a2:
                    st.success(f"🟢 마스터 코드 승인 완료 리스트 ({len(approved_master_df)}건)")
                    app_cols = ['품목코드', '품목명', '거래처명']
                    st.dataframe(approved_master_df[app_cols], use_container_width=True, hide_index=True)

                with st.expander(f"📋 마스터 전체 기준 미승인 품목 전체 보기 ({len(unapproved_master_df)}건 — 미제출 + 대기중 포함)"):
                    st.dataframe(unapproved_master_df[['품목코드', '품목명', '거래처명']], use_container_width=True, hide_index=True)

            # [서브탭 4] 상호 표기 불일치 제출건 확인 (독촉 오발송 방지)
            with sub_tab4:
                st.caption("업체가 시트1에 제출했으나 공급사(판매원)·제조원 명칭을 마스터 거래처명과 다르게 적어 자동 연결되지 않은 건입니다. 독촉 메일 발송 전 한번 확인해 주세요.")
                if unmatched_sub_df.empty:
                    st.success("🎉 시트1의 모든 제출건이 마스터 거래처명과 정상 매칭되었습니다.")
                else:
                    st.warning(f"⚠️ 마스터 거래처명과 상호가 매칭되지 않은 제출건이 {len(unmatched_sub_df)}건 있습니다.")
                    u_cols = [c for c in ['검증상태', '코드', '제품명', '공급사(판매원)', '제조원', '제출일시'] if c in unmatched_sub_df.columns]
                    st.dataframe(unmatched_sub_df[u_cols], use_container_width=True, hide_index=True)
        else:
            st.info("구글 시트에 '전체 원재료 명단' 데이터가 없거나 헤더(품목코드, 품목명, 거래처명)를 확인해주세요.")

    # ------------------ [탭 2: AI 검증 및 승인] ------------------
    with admin_tab2:
        col_t2_title, col_t2_btn = st.columns([8, 2])
        with col_t2_title:
            st.markdown("### 🤖 대기열 검증 및 마스터 코드 확정 (인라인 수정 모드)")
            st.caption("좌측의 폼에서 오타를 직접 수정한 후 승인할 수 있으며, 우측의 라벨 이미지와 실시간으로 대조 가능합니다.")
        with col_t2_btn:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 대기 목록 새로고침", key="btn_refresh_tab2", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        master_select_options = ["직접 입력 / AI 추천값 유지"]
        master_code_lookup = {}
        if not master_df.empty and '품목코드' in master_df.columns:
            for _, m_row in master_df.iterrows():
                mc = str(m_row.get('품목코드', '')).strip()
                mn = str(m_row.get('품목명', '')).strip()
                mv = str(m_row.get('거래처명', '')).strip()
                if mc:
                    label_str = f"[{mc}] {mn} | {mv}"
                    if label_str not in master_code_lookup:
                        master_select_options.append(label_str)
                        master_code_lookup[label_str] = mc
                    if mc not in master_code_lookup:
                        master_code_lookup[mc] = f"[{mc}] {mn} ({mv})"

        if not df.empty and '검증상태' in df.columns:
            pending_df = df[df['검증상태'] == '대기중'].reset_index()

            if pending_df.empty:
                st.success("🎉 현재 대기 중인 검증 건이 없습니다. 모두 승인되었습니다.")
            else:
                st.warning(f"⚠️ 현재 {len(pending_df)}건의 라벨이 검증 및 승인 대기 중입니다.")

                for _, row in pending_df.iterrows():
                    excel_row_idx = row['index'] + 2
                    name = row.get('제품명', '')
                    vendor_title = row.get('공급사(판매원)', '')
                    file_id = row.get('파일ID', '')
                    submit_time = row.get('제출일시', '')
                    img_url = row.get('이미지링크', '')

                    with st.expander(f"📦 [대기중] {name} | 공급사: {vendor_title} ({submit_time})", expanded=False):
                        col_left, col_right = st.columns([4, 6])

                        with col_left:
                            st.markdown("#### 📝 제출 데이터 (수정 가능)")

                            edit_maker = st.text_input("제조원", value=row.get('제조원', ''), key=f"e_maker_{excel_row_idx}")
                            edit_vendor = st.text_input("공급사(판매원)", value=row.get('공급사(판매원)', ''), key=f"e_vendor_{excel_row_idx}")
                            edit_name = st.text_input("제품명", value=row.get('제품명', ''), key=f"e_name_{excel_row_idx}")
                            edit_type = st.text_input("식품유형", value=row.get('식품유형', ''), key=f"e_type_{excel_row_idx}")
                            edit_origin = st.text_input("원산지", value=row.get('원산지', ''), key=f"e_origin_{excel_row_idx}")
                            edit_old = st.text_input("기존 알레르기", value=row.get('기존알레르기', ''), key=f"e_old_{excel_row_idx}")
                            edit_new = st.text_input("신규 알레르기", value=row.get('신규알레르기', ''), key=f"e_new_{excel_row_idx}")
                            edit_ing = st.text_area("원재료명(한글표시사항)", value=row.get('원재료명(한글표시사항)', ''), height=150, key=f"e_ing_{excel_row_idx}")

                            candidates_payload, vendor_matched_df = filter_master_candidates(master_df, edit_vendor, edit_name)
                            if not vendor_matched_df.empty:
                                st.caption(f"✅ 사내 마스터 내 '{edit_vendor}' 일치 거래처 품목 {len(vendor_matched_df)}건 확인됨")
                            else:
                                st.caption("ℹ️ 공급사명 완전 일치 거래처 없음 (AI 분석 시 전체 명단 유사 품목으로 확장 탐색)")

                            if st.button(f"🔍 AI 교차검증 및 매칭 분석", key=f"btn_ai_{excel_row_idx}"):
                                if file_id:
                                    with st.spinner("드라이브 라벨 분석 및 공급사·제품명 기반 마스터 코드 매칭 중..."):
                                        f_bytes, mime = download_file_from_drive(file_id)
                                        if f_bytes:
                                            updated_vendor_data = {
                                                '제품명': edit_name,
                                                '공급사(판매원)': edit_vendor,
                                                '원재료명(한글표시사항)': edit_ing,
                                                '제조원': edit_maker,
                                                '기존알레르기': edit_old,
                                                '신규알레르기': edit_new
                                            }
                                            result = verify_with_ai(f_bytes, mime, updated_vendor_data, candidates_payload)
                                            match_code = extract_recommended_code(result)

                                            st.session_state[f"ai_result_{excel_row_idx}"] = result
                                            st.session_state[f"rec_code_{excel_row_idx}"] = match_code
                                            st.session_state[f"final_code_{excel_row_idx}"] = match_code
                                        else:
                                            st.error("라벨 파일 다운로드 실패")
                                else:
                                    st.error("파일 ID가 존재하지 않습니다.")

                            if f"ai_result_{excel_row_idx}" in st.session_state:
                                st.markdown("### 📋 AI 판독 및 매칭 결과")
                                ai_result_text = st.session_state[f"ai_result_{excel_row_idx}"]

                                if "[불합격]" in ai_result_text:
                                    st.markdown(f'<div style="background-color: #ffcccc; padding: 10px; border-radius: 5px; color: #cc0000; font-weight: bold;">{ai_result_text}</div>', unsafe_allow_html=True)
                                else:
                                    st.info(ai_result_text)

                                st.markdown("---")

                                def apply_manual_select(row_idx=excel_row_idx):
                                    sel_val = st.session_state.get(f"sel_master_{row_idx}", "")
                                    if sel_val in master_code_lookup and sel_val != "직접 입력 / AI 추천값 유지":
                                        st.session_state[f"final_code_{row_idx}"] = master_code_lookup[sel_val]

                                st.selectbox(
                                    "🔎 사내 마스터 명단에서 직접 검색·변경 (선택 시 아래 코드칸에 자동 입력):",
                                    options=master_select_options,
                                    key=f"sel_master_{excel_row_idx}",
                                    on_change=apply_manual_select
                                )

                                final_code = st.text_input(
                                    "최종 매핑할 '원자재 코드' 입력:",
                                    value=st.session_state.get(f"rec_code_{excel_row_idx}", ""),
                                    key=f"final_code_{excel_row_idx}"
                                )

                                clean_final_code = str(final_code).strip()
                                if clean_final_code in master_code_lookup:
                                    st.caption(f"📌 매핑 대상 확인: {master_code_lookup[clean_final_code]}")

                                if st.button(f"✅ 코드 '{clean_final_code}' 승인 및 수정사항 전체 DB 저장", type="primary", key=f"btn_approve_{excel_row_idx}"):
                                    if clean_final_code and clean_final_code != "없음":
                                        ai_full_text = st.session_state[f"ai_result_{excel_row_idx}"]
                                        update_dict = {
                                            '코드': clean_final_code,
                                            '제품명': edit_name,
                                            '식품유형': edit_type,
                                            '원재료명(한글표시사항)': edit_ing,
                                            '원산지': edit_origin,
                                            '제조원': edit_maker,
                                            '공급사(판매원)': edit_vendor,
                                            '기존알레르기': edit_old,
                                            '신규알레르기': edit_new,
                                            '검증상태': '승인완료',
                                            '검증결과': ai_full_text
                                        }
                                        res = update_row_data(excel_row_idx, update_dict)

                                        if res == True:
                                            st.cache_data.clear()
                                            st.rerun()
                                        else:
                                            st.error(f"저장 에러: {res}")
                                    else:
                                        st.error("유효한 원자재 코드를 입력해야 승인할 수 있습니다.")

                        with col_right:
                            st.markdown("#### 🖼️ 첨부 라벨 원본 뷰어")
                            if img_url and str(img_url).startswith('http'):
                                render_inline_viewer(img_url)
                            else:
                                st.warning("라벨 이미지가 없습니다.")
        else:
            st.info("등록된 데이터가 없습니다.")

    # ------------------ [탭 3: 기존 DB 검색 및 다운로드] ------------------
    with admin_tab3:
        st.markdown("### 🔍 승인된 원자재 DB 다중 검색 및 다운로드")
        if not df.empty and '검증상태' in df.columns:
            approved_df = df[df['검증상태'] == '승인완료'].copy()
            if '공급사(판매원)' not in approved_df.columns:
                approved_df['공급사(판매원)'] = ""

            search_query = st.text_input("🔍 제품명 또는 코드 검색 (쉼표로 구분하여 여러 개 동시 검색 가능, 예: 20014, 참깨):")

            if search_query:
                queries = [q.strip() for q in search_query.split(',') if q.strip()]
                pattern = '|'.join(queries)

                approved_df = approved_df[
                    approved_df['제품명'].astype(str).str.contains(pattern, regex=True, na=False) |
                    approved_df['코드'].astype(str).str.contains(pattern, regex=True, na=False)
                ]

            approved_df['기존알레르기'] = approved_df['기존알레르기'].apply(clean_allergen_text)
            approved_df['신규알레르기'] = approved_df['신규알레르기'].apply(clean_allergen_text).apply(highlight_new_allergens)

            def make_link(name, file_id):
                if file_id:
                    return f'<a href="https://drive.google.com/uc?export=download&id={file_id}" target="_blank" style="text-decoration: underline; color: #0056b3; font-weight: bold;">{name}</a>'
                return name

            approved_df['제품명(클릭 시 라벨오픈)'] = approved_df.apply(lambda row: make_link(row['제품명'], row['파일ID']), axis=1)

            display_cols = ['코드', '제품명(클릭 시 라벨오픈)', '식품유형', '원산지', '원재료명(한글표시사항)', '제조원', '공급사(판매원)', '기존알레르기', '신규알레르기']

            st.markdown(
                """
                <style>
                .table-container {
                    max-height: 600px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }
                .custom-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 14px;
                }
                .custom-table th, .custom-table td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                    vertical-align: top;
                }
                .custom-table th {
                    background-color: #f2f2f2;
                    font-weight: bold;
                    position: sticky;
                    top: 0;
                    z-index: 1;
                    box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.4);
                }
                </style>
                """, unsafe_allow_html=True
            )
            html_table = approved_df[display_cols].to_html(classes="custom-table", index=False, escape=False)
            st.markdown(f'<div class="table-container">{html_table}</div>', unsafe_allow_html=True)

            if not approved_df.empty:
                raw_df = df[df['검증상태'] == '승인완료'].copy()
                if '공급사(판매원)' not in raw_df.columns:
                    raw_df['공급사(판매원)'] = ""
                if search_query:
                    raw_df = raw_df[raw_df['제품명'].astype(str).str.contains(pattern, regex=True, na=False) | raw_df['코드'].astype(str).str.contains(pattern, regex=True, na=False)]

                dl_cols = ['코드', '제품명', '식품유형', '원산지', '원재료명(한글표시사항)', '제조원', '공급사(판매원)', '기존알레르기', '신규알레르기']
                csv = convert_df_to_csv(raw_df[dl_cols])
                st.download_button(
                    label="📥 검색 결과 엑셀(CSV) 다운로드",
                    data=csv,
                    file_name="원자재_DB_검색결과.csv",
                    mime="text/csv",
                )
        else:
            st.info("데이터가 없습니다.")

    # ------------------ [탭 4: 배합비 역추적기] ------------------
    with admin_tab4:
        st.markdown("### 🚨 잠복 알레르기 및 완제품(BOM) 역추적")
        bom_df = load_bom_data()

        if not df.empty and '코드' in df.columns:
            valid_df = df[df['코드'] != '']
            target_allergen = st.text_input("🔍 추적할 숨은 성분 키워드 (예: 참깨, 아몬드):")

            if target_allergen:
                mask_name = valid_df['제품명'].astype(str).str.contains(target_allergen, regex=False, na=False)
                mask_detail = valid_df['원재료명(한글표시사항)'].astype(str).str.contains(target_allergen, regex=False, na=False)

                tracked_df = valid_df[mask_name | mask_detail].copy()

                if tracked_df.empty:
                    st.success("🎉 해당 물질이 포함된 원료가 없습니다!")
                else:
                    st.error(f"🚨 타겟 물질('{target_allergen}')이 포함된 원자재 {len(tracked_df)}건 적발.")
                    st.dataframe(tracked_df[['코드', '제품명', '원재료명(한글표시사항)', '신규알레르기']], use_container_width=True, hide_index=True)

                    csv_mat = convert_df_to_csv(tracked_df[['코드', '제품명', '원재료명(한글표시사항)', '신규알레르기']])
                    st.download_button("📥 적발된 원자재 리스트 다운로드", data=csv_mat, file_name=f"{target_allergen}_포함_원자재.csv", mime="text/csv")

                    st.markdown("---")

                    if not bom_df.empty:
                        st.markdown(f"#### 🏭 '{target_allergen}' 유입 완제품 리스트 (다계층 무한 추적)")
                        flagged_codes = tracked_df['코드'].astype(str).tolist()
                        affected_products_list = []

                        code_cols = [c for c in bom_df.columns if str(c).startswith('Code') and c != 'Code1']
                        if not code_cols and '원자재코드' in bom_df.columns:
                            code_cols = ['원자재코드']

                        for code_col in code_cols:
                            matches = bom_df[bom_df[code_col].astype(str).isin(flagged_codes)]
                            name_col = code_col.replace('Code', 'Name')
                            if name_col not in bom_df.columns:
                                name_col = '원자재명' if '원자재명' in bom_df.columns else code_col

                            for _, row in matches.iterrows():
                                affected_products_list.append({
                                    '완제품코드': str(row.get('Code1', row.get('완제품코드', ''))),
                                    '완제품명': str(row.get('Name1', row.get('완제품명', ''))),
                                    '적발된 원료코드': str(row.get(code_col, '')),
                                    '적발된 원료명': str(row.get(name_col, '')),
                                })

                        if not affected_products_list:
                            st.success("✅ 적발 원료가 투입된 완제품이 없습니다.")
                        else:
                            affected_df = pd.DataFrame(affected_products_list).drop_duplicates()
                            st.warning(f"⚠️ 총 {len(affected_df['완제품코드'].unique())}종의 완제품에 투입되고 있습니다.")
                            st.dataframe(affected_df, use_container_width=True, hide_index=True)

                            csv_prod = convert_df_to_csv(affected_df)
                            st.download_button("📥 유입 위험 완제품 리스트 다운로드", data=csv_prod, file_name=f"{target_allergen}_유입_완제품.csv", mime="text/csv")
                    else:
                        st.info("BOM 데이터가 없습니다.")

    # ------------------ [탭 5: 완제품 알레르기 마스터] ------------------
    with admin_tab5:
        st.markdown("### 📋 완제품 알레르기 통합 마스터 테이블")

        WARNING_MSG = "알레르기 유발물질 혼입 가능성 있음"
        st.markdown(f"""
        <div style="background-color: #ffe6e6; padding: 15px; border-radius: 8px; border-left: 5px solid #ff4d4d; margin-bottom: 20px;">
        <strong>⚠️ [주의] 알레르기 교차 혼입 방지</strong><br>
        당사는 알레르기 교차 혼입 방지 문구로 『<strong>{WARNING_MSG}</strong>』을(를) 사용하고 있으므로, 표시사항 스티커 및 패키지 후면 인쇄 시 반드시 해당 문구를 포함하여야 합니다.
        </div>
        """, unsafe_allow_html=True)

        bom_df = load_bom_data()

        if df.empty or bom_df.empty or '코드' not in df.columns:
            st.info("원자재 DB(승인 완료건) 또는 배합비 DB가 필요합니다.")
        else:
            with st.spinner("BOM 데이터와 원자재 DB를 스캔하여 완제품별 알레르기 테이블을 구성 중입니다..."):
                valid_df = df[df['코드'] != '']

                prod_col = 'Name1' if 'Name1' in bom_df.columns else '완제품명'
                prod_code_col = 'Code1' if 'Code1' in bom_df.columns else '완제품코드'

                unique_products = bom_df[[prod_code_col, prod_col]].drop_duplicates().dropna(subset=[prod_code_col])

                master_table_data = []

                code_cols = [c for c in bom_df.columns if str(c).startswith('Code') and c != 'Code1']
                if not code_cols and '원자재코드' in bom_df.columns:
                    code_cols = ['원자재코드']

                for _, p_row in unique_products.iterrows():
                    p_code = p_row[prod_code_col]
                    p_name = p_row[prod_col]

                    if not str(p_code).strip(): continue

                    p_bom_rows = bom_df[bom_df[prod_code_col] == p_code]

                    used_rm_codes = set()
                    for code_col in code_cols:
                        used_rm_codes.update(p_bom_rows[code_col].dropna().astype(str).tolist())

                    used_rm_df = valid_df[valid_df['코드'].astype(str).isin(used_rm_codes)]

                    if used_rm_df.empty: continue

                    all_old_allergies = set()
                    all_new_allergies = set()

                    for _, rm_row in used_rm_df.iterrows():
                        old_str = str(rm_row.get('기존알레르기', ''))
                        new_str = str(rm_row.get('신규알레르기', ''))

                        for item in old_str.split(','):
                            clean_item = item.strip()
                            if clean_item and "해당없음" not in clean_item:
                                all_old_allergies.add(clean_item)

                        for item in new_str.split(','):
                            clean_item = item.strip()
                            if clean_item and "해당없음" not in clean_item:
                                all_new_allergies.add(clean_item)

                    final_old = ", ".join(sorted(list(all_old_allergies))) if all_old_allergies else "해당없음"
                    final_new = ", ".join(sorted(list(all_new_allergies))) if all_new_allergies else "해당없음"

                    master_table_data.append({
                        "완제품코드": p_code,
                        "완제품명": p_name,
                        "기존 알레르기 요약": final_old,
                        "신규 알레르기 요약": final_new
                    })

                if master_table_data:
                    master_res_df = pd.DataFrame(master_table_data)
                    st.dataframe(master_res_df, use_container_width=True, hide_index=True)

                    csv_master = convert_df_to_csv(master_res_df)
                    st.download_button("📥 완제품 알레르기 마스터 테이블 다운로드", data=csv_master, file_name="완제품_알레르기_마스터.csv", mime="text/csv")
                else:
                    st.warning("매칭되는 완제품 데이터가 없습니다. 원자재 코드와 BOM 코드가 일치하는지 확인해주세요.")
