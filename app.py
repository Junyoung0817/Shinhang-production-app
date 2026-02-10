import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy

st.set_page_config(page_title="신항공장 통합 관리 System", layout="wide")

# ---------------------------------------------------------
# 1. 초기 설정 및 데이터 정의
# ---------------------------------------------------------

# 탱크 스펙
TANK_SPECS = {
    'TK-310':   {'max': 750,  'type': 'Buffer'},
    'TK-710':   {'max': 760,  'type': 'Prod'},
    'TK-720':   {'max': 760,  'type': 'Prod'},
    'TK-6101':  {'max': 5700, 'type': 'Shore'},
    'UTK-308':  {'max': 5400, 'type': 'Shore'},
    'UTK-1106': {'max': 6650, 'type': 'Shore'}
}

# 기본 데이터 구조 (모두 0)
DEFAULT_DATA = {
    'qty': 0.0, 'av': 0.0, 'water': 0, 'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
}

# 오차 기록 저장소 초기화
if 'correction_log' not in st.session_state:
    st.session_state.correction_log = []

# 날짜별 DB 로드 (수정됨: 더미 데이터 삭제)
def get_daily_data(date_str):
    # 1. 세션 DB가 없으면 빈 딕셔너리로 초기화 (더미 데이터 X)
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = {}

    # 2. 해당 날짜 데이터가 있으면 반환
    if date_str in st.session_state.daily_db:
        return st.session_state.daily_db[date_str]
    
    # 3. 해당 날짜 데이터가 없으면? (이월 or 0 초기화)
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")