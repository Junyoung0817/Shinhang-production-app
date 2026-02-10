import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy
import time
import random
import json
import os

# 1. 페이지 설정
st.set_page_config(page_title="신항공장 생산관리", layout="wide")

# ---------------------------------------------------------
# 2. 영구 저장 및 데이터 관리 함수 (핵심 기능)
# ---------------------------------------------------------

DB_FILE = 'factory_db.json'

def load_data_from_file():
    """파일에서 데이터를 불러옵니다. 없으면 빈 DB 반환"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data_to_file(db):
    """데이터를 파일에 저장합니다."""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"데이터 저장 실패: {e}")

# 초기 설정
def init_system():
    tank_specs = {
        'TK-310':   {'max': 750,  'type': 'Buffer'},
        'TK-710':   {'max': 760,  'type': 'Prod'},
        'TK-720':   {'max': 760,  'type': 'Prod'},
        'TK-6101':  {'max': 5700, 'type': 'Shore'},
        'UTK-308':  {'max': 5400, 'type': 'Shore'},
        'UTK-1106': {'max': 6650, 'type': 'Shore'}
    }
    
    default_vals = {
        'qty': 0.0, 'av': 0.0, 'water': 0, 
        'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
    }
    
    # 세션에 DB가 없으면 파일에서 로드
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = load_data_from_file()
        
    if 'history_log' not in st.session_state:
        st.session_state.history_log = []
    if 'qc_log' not in st.session_state:
        st.session_state.qc_log = []
        
    return tank_specs, default_vals

# [핵심] 지능형 데이터 가져오기
def get_today_data(date_key, specs, defaults):
    # 1. 데이터가 이미 존재하는 경우
    if date_key in st.session_state.daily_db:
        data = st.session_state.daily_db[date_key]
        
        # [중요] 데이터는 있지만 전부 '0'인 경우 (빈 껍데기) -> 과거 데이터 재검색 시도
        total_qty = sum(t['qty'] for t in data.values())
        if total_qty == 0:
            past_data = find_past_data(date_key)
            if past_data:
                # 과거 데이터가 발견되면 덮어씌움 (자동 이월)
                st.session_state.daily_db[date_key] = past_data
                save_data_to_file(st.session_state.daily_db) # 저장
                return past_data
        
        return data
    
    # 2. 데이터가 없는 경우 -> 과거 데이터 찾기 (Look-back)
    past_data = find_past_data(date_key)
    
    if past_data:
        st.session_state.daily_db[date_key] = past_data
    else:
        # 과거 데이터도 없으면 0으로 초기화
        new_data = {}
        for t_name in specs:
            new_data[t_name] = defaults.copy()
        st.session_state.daily_db[date_key] = new_data
        
    save_data_to_file(st.session_state.daily_db) # 신규 생성 저장
    return st.session_state.daily_db[date_key]

def find_past_data(current_date_str):
    """가장 최근의 과거 데이터를 찾아 반환"""
    current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
    for i in range(1, 366):
        past = (current_date - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            # 과거 데이터가 0이 아닌 경우에만 유효하다고 판단
            past_data = st.session_state.daily_db[past]
            if sum(t['qty'] for t in past_data.values()) > 0:
                return copy.deepcopy(past_data)
    return None

def reset_today_data(date_key, specs, defaults):
    # 전일 데이터 찾기
    past_data = find_past_data(date_key)
    
    if past_data:
        st.session_state.daily_db[date_key] = past_data
        st.toast(f"✅ {date_key} 초기화: 전일 데이터를 불러왔습니다.")
    else:
        new_data = {}
        for t_name in specs:
            new_data[t_name] = defaults.copy()
        st.session_state.daily_db[date_key] = new_data
        st.toast(f"✅ {date_key} 초기화: 데이터가 없어 0으로 설정했습니다.")
    
    save_data_to_file(st.session_state.daily_db) # 저장
    time.sleep(1.0)
    st.rerun()

# 공통: 변경사항이 생길 때마다 파일 저장 호출
def persist():
    save_data_to_file(st.session_state.daily_db)

# ---------------------------------------------------------
# 더미 데이터 및 초기화
# ---------------------------------------------------------
def generate_dummy_data(specs, defaults):
    base_date = datetime.now()
    for i in range(7, -1, -1):
        d_key = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
        new_data = {}
        for t_name in specs:
            data = defaults.copy()
            data['qty'] = round(random.uniform(100, 500), 1)
            data['av'] = round(random.uniform(0.1, 1.0), 3)
            data['org_cl'] = round(random.uniform(5, 20), 1)
            data['water'] = random.randint(10, 100)
            new_data[t_name] = data
        st.session_state.daily_db[d_key] = new_data
    
    persist() # 저장
    st.toast("✅ 테스트 데이터 생성 완료")
    time.sleep(1.0)
    st.rerun()

def factory_reset():
    st.session_state.daily_db = {}
    st.session_state.history_log = []
    st.session_state.qc_log = []
    
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE) # 파일 삭제
        
    st.toast("🧹 공장 초기화 완료")
    time.sleep(1.0)
    st.rerun()

# ---------------------------------------------------------
# 로깅 및 계산 함수
# ---------------------------------------------------------
def log_action(date_key, action_type, desc, tanks_involved, current_db):
    snapshot = {}
    for t_name in tanks_involved:
        snapshot[t_name] = copy.deepcopy(current_db[t_name])
    st.session_state.history_log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": date_key, "type": action_type, "desc": desc, "snapshot": snapshot
    })

def log_qc_diff(date_key, tank_name, param, predicted, actual):
    diff = actual - predicted
    if abs(diff) > 0.001:
        st.session_state.qc_log.append({
            "날짜": date_key, "탱크": tank_name, "항목": param,
            "예상값":