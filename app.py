import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy
import time

# 1. 페이지 설정 (반드시 맨 처음에 와야 함)
st.set_page_config(page_title="신항공장 생산관리", layout="wide")

# ---------------------------------------------------------
# 2. 안전한 함수 정의 (에러 방지)
# ---------------------------------------------------------

# Rerun 호환성 처리 (버전 문제 해결)
def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        try:
            st.experimental_rerun()
        except:
            st.warning("화면을 새로고침(F5) 해주세요.")

# 탱크 스펙
TANK_SPECS = {
    'TK-310':   {'max': 750,  'type': 'Buffer'},
    'TK-710':   {'max': 760,  'type': 'Prod'},
    'TK-720':   {'max': 760,  'type': 'Prod'},
    'TK-6101':  {'max': 5700, 'type': 'Shore'},
    'UTK-308':  {'max': 5400, 'type': 'Shore'},
    'UTK-1106': {'max': 6650, 'type': 'Shore'}
}

# 기본 데이터
DEFAULT_DATA = {
    'qty': 0.0, 'av': 0.0, 'water': 0, 'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
}

# 세션 초기화
if 'daily_db' not in st.session_state:
    st.session_state.daily_db = {}
if 'correction_log' not in st.session_state:
    st.session_state.correction_log = []

# 데이터 가져오기
def get_daily_data(date_str):
    # 해당 날짜 데이터가 있으면 반환
    if date_str in st.session_state.daily_db:
        return st.session_state.daily_db[date_str]
    
    # 없으면 전날 데이터 찾기
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if prev_date in st.session_state.daily_db:
        new_data = copy.deepcopy(st.session_state.daily_db[prev_date])
    else:
        new_data = {k: DEFAULT_DATA.copy() for k in TANK_SPECS.keys()}
        
    st.session_state.daily_db[date_str] = new_data
    return new_data

# 블렌딩 계산
def calc_blending(curr_qty, curr_val, in_qty, in_val):
    total = curr_qty + in_qty
    if total == 0: return 0.0
    return ((curr_qty * curr_val) + (in_qty * in_val)) / total

# ---------------------------------------------------------
# 3. 메인 UI
# ---------------------------------------------------------
st.sidebar.title("🏭 생산/출하 시스템")
st.sidebar.caption("Ver 6.0 Safe Mode")

# 시스템 초기화 버튼
if st.sidebar.button("⚠️ 데이터 초기화 (Reset)"):
    st.session_state.daily_db = {}
    st.session_state.correction_log = []
    safe_rerun()

selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
date_key = selected_date.strftime("%Y-%m-%d")
current_data = get_daily_data(date_key)

menu = st.sidebar.radio("MENUS", 
    ["🔍 모니터링 (View)", 
     "① 1차 공정 (R-1140)", 
     "② 2차 정제 (EV-6000)", 
     "③ 3차 이송 (Shore)",
     "④ 수출 선적 (Ship)",
     "⑤ 실측 보정 (Correct)",
     "⑥ 오차 분석 (Analysis)"]
)

# [TAB 1] 모니터링
if menu == "🔍 모니터링 (View)":
    st.title(f"🔍 {date_key} 현황판")
    
    total_qty = sum(d['qty'] for d in current_data.values())
    st.metric("총 재고량", f"{total_qty:,.0f} MT")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    
    # 탱크 카드를 순서대로 배치
    tank_list = list(TANK_SPECS.keys())
    
    for i, t_name in enumerate(tank_list):
        # 3열 배치 로직
        with [col1, col2, col3][i % 3]:
            data = current_data[t_name]