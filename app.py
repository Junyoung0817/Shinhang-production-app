import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy

# 1. 페이지 설정
st.set_page_config(page_title="신항공장 생산관리", layout="wide")

# 2. 데이터 초기화 함수
def init_data():
    # 탱크 스펙 정의
    tank_specs = {
        'TK-310':   {'max': 750},
        'TK-710':   {'max': 760},
        'TK-720':   {'max': 760},
        'TK-6101':  {'max': 5700},
        'UTK-308':  {'max': 5400},
        'UTK-1106': {'max': 6650}
    }
    
    # 기본 데이터 구조
    default_vals = {
        'qty': 0.0, 'av': 0.0, 'water': 0, 
        'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
    }
    
    # 세션 상태 초기화
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = {}
    
    return tank_specs, default_vals

# 3. 날짜별 데이터 가져오기
def get_data(date_key, tank_specs, default_vals):
    # DB에 없으면 생성
    if date_key not in st.session_state.daily_db:
        # 전날 데이터 확인
        date_obj = datetime.strptime(date_key, "%Y-%m-%d")
        prev_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if prev_date in st.session_state.daily_db:
            # 전날 데이터 복사
            st.session_state.daily_db[date_key] = copy.deepcopy(st.session_state.daily_db[prev_date])
        else:
            # 0으로 초기화
            new_data = {}
            for t in tank_specs:
                new_data[t] = default_vals.copy()
            st.session_state.daily_db[date_key] = new_data
            
    return st.session_state.daily_db[date_key]

# 4. 블