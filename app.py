import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy

# 1. 페이지 설정 (가장 먼저 실행되어야 함)
st.set_page_config(page_title="신항공장 통합 관리 System", layout="wide")

# ---------------------------------------------------------
# 2. 초기 설정 및 데이터 구조 정의
# ---------------------------------------------------------

# 탱크 스펙 (사용자 정의 값)
TANK_SPECS = {
    'TK-310':   {'max': 750,  'type': 'Buffer'},
    'TK-710':   {'max': 760,  'type': 'Prod'},
    'TK-720':   {'max': 760,  'type': 'Prod'},
    'TK-6101':  {'max': 5700, 'type': 'Shore'},
    'UTK-308':  {'max': 5400, 'type': 'Shore'},
    'UTK-1106': {'max': 6650, 'type': 'Shore'}
}

# 기본 데이터 (0으로 초기화)
DEFAULT_DATA = {
    'qty': 0.0, 'av': 0.0, 'water': 0, 'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
}

# 세션 상태 초기화 함수
def init_session_state():
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = {}
    if 'correction_log' not in st.session_state:
        st.session_state.correction_log = []

# 데이터 가져오기 함수 (안전장치 추가)
def get_daily_data(date_str):
    # DB가 없으면 생성
    if 'daily_db' not in st.session_state:
        init_session_state()

    # 해당 날짜 데이터가 있으면 반환
    if date_str in st.session_state.daily_db:
        return st.session_state.daily_db[date_str]
    
    # 없으면 전날 데이터 찾기
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if prev_date in st.session_state.daily_db:
        # 전날 데이터 복사 (이월)
        new_data = copy.deepcopy(st.session_state.daily_db[prev_date])
    else:
        # 전날 데이터도 없으면 0으로 초기화 (Zero Base)
        new_data = {k: DEFAULT_DATA.copy() for k in TANK_SPECS.keys()}
        
    st.session_state.daily_db[date_str] = new_data
    return new_data

# 블렌딩 계산 함수
def calc_blending(curr_qty, curr_val, in_qty, in_val):
    total = curr_qty + in_qty
    if total == 0: return 0.0
    return ((curr_qty * curr_val) + (in_qty * in_val)) / total

# ---------------------------------------------------------
# 3. 메인 앱 실행 로직
# ---------------------------------------------------------

# 초기화 실행
init_session_state()

# 사이드바 설정
st.sidebar.title("🏭 생산/출하/QC 시스템")

# [시스템 초기화 버튼] - 문제가 생겼을 때 누르는 비상 버튼
if st.sidebar.button("⚠️ 시스템 데이터 초기화 (Reset)"):
    st.session_state.daily_db = {}