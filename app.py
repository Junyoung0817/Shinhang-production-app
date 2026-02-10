import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy
import time
import json

# 1. 페이지 설정
st.set_page_config(page_title="신항공장 생산관리", layout="wide")

# ---------------------------------------------------------
# 2. 초기 설정 및 데이터 관리 함수
# ---------------------------------------------------------

def load_data():
    # 탱크 스펙
    tank_specs = {
        'TK-310':   {'max': 750,  'type': 'Buffer'},
        'TK-710':   {'max': 760,  'type': 'Prod'},
        'TK-720':   {'max': 760,  'type': 'Prod'},
        'TK-6101':  {'max': 5700, 'type': 'Shore'},
        'UTK-308':  {'max': 5400, 'type': 'Shore'},
        'UTK-1106': {'max': 6650, 'type': 'Shore'}
    }
    
    # 기본값
    default_vals = {
        'qty': 0.0, 'av': 0.0, 'water': 0, 
        'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
    }
    
    # DB 초기화
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = {}
        
    # 작업 이력 초기화
    if 'history_log' not in st.session_state:
        st.session_state.history_log = []
        
    return tank_specs, default_vals

def get_today_data(date_key, specs, defaults):
    # 1. 데이터가 이미 있으면 그냥 반환 (자동 덮어쓰기 방지)
    if date_key in st.session_state.daily_db:
        return st.session_state.daily_db[date_key]
    
    # 2. 없으면 과거 데이터 찾기 (Look-back)
    current_date = datetime.strptime(date_key, "%Y-%m-%d")
    found_data = None
    
    # 최대 365일 전까지 검색
    for i in range(1, 366):
        past = (current_date - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            found_data = copy.deepcopy(st.session_state.daily_db[past])
            break
            
    if found_data:
        st.session_state.daily_db[date_key] = found_data
    else:
        # 과거 데이터도 없으면 0으로 초기화
        new_data = {}
        for t_name in specs:
            new_data[t_name] = defaults.copy()
        st.session_state.daily_db[date_key] = new_data
            
    return st.session_state.daily_db[date_key]

# [NEW] 전일 데이터 강제 불러오기 함수
def force_load_prev(date_key):
    current_date = datetime.strptime(date_key, "%Y-%m-%d")
    found_data = None
    found_date_str = ""
    
    # 과거 데이터 검색
    for i in range(1, 366):
        past = (current_date - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            found_data = copy.deepcopy(st.session_state.daily_db[past])
            found_date_str = past
            break
    
    if found_data:
        st.session_state.daily_db[date_key] = found_data
        st.sidebar.success(f"✅ {found_date_str} 데이터를 불러왔습니다.")
        time.sleep(0.7)
        st.rerun()
    else:
        st.sidebar.error("❌ 불러올 과거 데이터가 없습니다.")

# 작업 기록 함수
def log_action(desc, tanks_involved, current_db):
    snapshot = {}
    for t_name in tanks_involved:
        snapshot[t_name] = copy.deepcopy(current_db[t_name])
    
    st.session_state.history_log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "desc": desc,
        "snapshot": snapshot
    })

# 실행 취소 함수
def undo_last_action(current_db):
    if not st.session_state.history_log:
        st.sidebar.error("취소할 작업이 없습니다.")
        return

    last = st.session_state.history_log.pop()
    for t_name, prev_data in last['snapshot'].items():
        current_db[t_name] = prev_data
        
    st.sidebar.success(f"취소 완료: {last['desc']}")
    time.sleep(0.5)
    st.rerun()

# 블렌딩 계산
def calc_blend(curr_qty, curr_val, in_qty, in_val):
    total = curr_qty + in_qty
    if total == 0: return 0.0
    return ((curr_qty * curr_val) + (in_qty * in_val)) / total

# ==========================================
# 메인 실행 로직
# ==========================================

SPECS, DEFAULTS = load_data()

st.sidebar.title("🏭 생산관리 System")
st.sidebar.caption("Ver 11.0 (Manual Sync)")

# 날짜 선택
selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
DATE_KEY = selected_date.strftime("%Y-%m-%d")

# 데이터 로드
TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)

# [핵심] 전일 데이터 불러오기 버튼
st.sidebar.markdown("---")
if st.sidebar.button("🔄 전일 마감 재고 불러오기"):
    force_load_prev(DATE_KEY)
st.sidebar.caption("⚠️ 주의: 현재 날짜의 데이터를 전일 데이터로 덮어씁니다.")

# 실행 취소
st.sidebar.markdown("---")
st.sidebar.markdown("### ↩️ 실행 취소")
if st.session_state.history_log:
    last_job = st.session_state.history_log[-1]['desc']
    st.sidebar.info(f"Last: {last_job}")
    if st.sidebar