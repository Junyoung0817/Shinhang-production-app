import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy
import time

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
        
    # [NEW] 작업 이력(History) 저장소 초기화
    if 'history_log' not in st.session_state:
        st.session_state.history_log = []
        
    return tank_specs, default_vals

def get_today_data(date_key, specs, defaults):
    if date_key not in st.session_state.daily_db:
        date_obj = datetime.strptime(date_key, "%Y-%m-%d")
        prev_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if prev_date in st.session_state.daily_db:
            st.session_state.daily_db[date_key] = copy.deepcopy(st.session_state.daily_db[prev_date])
        else:
            new_data = {}
            for t_name in specs:
                new_data[t_name] = defaults.copy()
            st.session_state.daily_db[date_key] = new_data
            
    return st.session_state.daily_db[date_key]

# [NEW] 작업 기록 함수 (변경 전 상태 저장)
def log_action(desc, tanks_involved, current_db):
    # 변경될 탱크들의 '현재 상태(변경 전)'를 깊은 복사로 저장
    snapshot = {}
    for t_name in tanks_involved:
        snapshot[t_name] = copy.deepcopy(current_db[t_name])
    
    # 로그에 추가
    st.session_state.history_log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "desc": desc,
        "snapshot": snapshot # 복구용 데이터
    })

# [NEW] 실행 취소 함수
def undo_last_action(current_db):
    if not st.session_state.history_log:
        st.sidebar.error("취소할 작업이 없습니다.")
        return

    # 마지막 작업 꺼내기
    last_action = st.session_state.history_log.pop()
    
    # 스냅샷을 이용해 데이터 복구
    for t_name, prev_data in last_action['snapshot'].items():
        current_db[t_name] = prev_data
        
    st.sidebar.success(f"취소 완료: {last_action['desc']}")
    time.sleep(0.5)
    st.rerun()

# 블렌딩 계산
def calc_blend(curr_qty, curr_val, in_qty, in_val):
    total_qty = curr_qty + in_qty
    if total_qty == 0: return 0.0
    return ((curr_qty * curr_val) +