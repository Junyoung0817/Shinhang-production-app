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
# 2. 영구 저장 및 데이터 관리 함수
# ---------------------------------------------------------

DB_FILE = 'factory_db.json'
LOG_FILE = 'factory_logs.json'

def load_data_from_file():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def load_logs_from_file():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('history', []), data.get('qc', [])
        except:
            return [], []
    return [], []

def save_db():
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.daily_db, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"DB 저장 실패: {e}")

def save_logs():
    try:
        data = {
            'history': st.session_state.history_log,
            'qc': st.session_state.qc_log
        }
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"로그 저장 실패: {e}")

def init_system():
    tank_specs = {
        'TK-310':   {'max': 750,  'type': 'Buffer'},
        'TK-710':   {'max': 760,  'type': 'Prod'},
        'TK-720':   {'max': 760,  'type': 'Prod'},
        'TK-6101':  {'max': 5700, 'type': 'Shore'},
        'UTK-308':  {'max': 5400, 'type': 'Shore'},
        'UTK-1106': {'max': 6650, 'type': 'Shore'}
    }
    
    # [변경] 모든 값을 소수점(float)으로 초기화 (수분 포함)
    default_vals = {
        'qty': 0.0, 'av': 0.0, 'water': 0.0, 
        'metal': 0.0, 'p': 0.0, 'org_cl': 0.0, 'inorg_cl': 0.0
    }
    
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = load_data_from_file()
    if 'history_log' not in st.session_state:
        h_log, q_log = load_logs_from_file()
        st.session_state.history_log = h_log
        st.session_state.qc_log = q_log
        
    return tank_specs, default_vals

def get_today_data(date_key, specs, defaults):
    if date_key in st.session_state.daily_db:
        data = st.session_state.daily_db[date_key]
        if sum(t['qty'] for t in data.values()) == 0:
            past = find_past_data(date_key)
            if past:
                st.session_state.daily_db[date_key] = past
                save_db()
                return past
        return data
    
    past = find_past_data(date_key)
    if past:
        st.session_state.daily_db[date_key] = past
    else:
        new_data = {t: defaults.copy() for t in specs}
        st.session_state.daily_db[date_key] = new_data
    save_db()
    return st.session_state.daily_db[date_key]

def find_past_data(current_date_str):
    curr = datetime.strptime(current_date_str, "%Y-%m-%d")
    for i in range(1, 366):
        past = (curr - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            data = st.