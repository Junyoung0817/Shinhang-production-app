import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy
import time
import random
import json
import os

# 1. 페이지 설정
st.set_page_config(
    page_title="2026 신항공장 생산 통합 시스템",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# [UI 디자인] Custom CSS
# ---------------------------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
        background-color: #f4f6f9;
    }
    
    /* 상단 요약 헤더 */
    .summary-header {
        background-color: white;
        padding: 20px 25px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        margin-bottom: 25px;
        border-top: 4px solid #e74c3c;
    }
    
    /* 카드 스타일 */
    .tank-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        transition: transform 0.2s;
    }
    .tank-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.08);
    }
    
    /* 메트릭 폰트 */
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #32325d; }
    .metric-unit { font-size: 0.9rem; color: #8898aa; font-weight: 500; }
    
    /* 품질 데이터 그리드 (수정됨) */
    .quality-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 15px;
        font-size: 0.85rem;
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
    }
    
    .q-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #e9ecef;
        padding-bottom: 5px;
        margin-bottom: 5px;
    }
    .q-row:last-child { border-bottom: none; margin-bottom: 0; }
    
    .q-label { color: #6c757d; font-weight: 500; }
    .q-val { font-weight: 700; color: #495057; }
    
    /* Total Cl 강조 */
    .highlight { color: #e74c3c !important; font-weight: 800 !important; }
    
    /* 버튼 스타일 */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        height: 45px;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 데이터 로직
# ---------------------------------------------------------

DB_FILE = 'factory_db.json'
LOG_FILE = 'factory_logs.json'

def load_data_from_file():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def load_logs_from_file():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('history', []), data.get('qc', [])
        except: return [], []
    return [], []

def save_db():
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.daily_db, f, indent=4, ensure_ascii=False)
    except: pass

def save_logs():
    try:
        data = {'history': st.session_state.history_log, 'qc': st.session_state.qc_log}
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

def init_system():
    tank_specs = {
        'TK-310':   {'max': 750,  'type': 'Buffer', 'icon': '🧪', 'color': '#2dce89'},
        'TK-710':   {'max': 760,  'type': 'Prod',   'icon': '🛢️', 'color': '#11cdef'},
        'TK-720':   {'max': 760,  'type': 'Prod',   'icon': '🛢️', 'color': '#11cdef'},
        'TK-6101':  {'max': 5700, 'type': 'Shore',  'icon': '🚢', 'color': '#5e72e4'},
        'UTK-308':  {'max': 5400, 'type': 'Shore',  'icon': '🚢', 'color': '#5e72e4'},
        'UTK-1106': {'max': 6650, 'type': 'Shore',  'icon': '🚢', 'color': '#5e72e4'}
    }
    default_vals = {'qty': 0.0, 'av': 0.0, 'water': 0.0, 'metal': 0.0, 'p': 0.0, 'org_cl': 0.0, 'inorg_cl': 0.0}
    
    if 'daily_db' not in st.session_state: st.session_state.daily_db = load_data_from_file()
    if 'history_log' not in st.session_state:
        h, q = load_logs_from_file()
        st.session_state.history_log = h; st.session_state.qc_log = q
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
    if past: st.session_state.daily_db[date_key] = past
    else: st.session_state.daily_db[date_key] = {t: defaults.copy() for t in specs}
    save_db()
    return st.session_state.daily_db[date_key]

def find_past_data(current_date_str):
    curr = datetime.strptime(current_date_str, "%Y-%m-%d")
    for i in range(1, 366):
        past = (curr - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            data = st.session_state.daily_db[past]
            if sum(t['qty'] for t in data.values()) > 0: return copy.deepcopy(data)
    return None

def reset_today_data(date_key, specs, defaults):
    past = find_past_data(date_key)
    if past: st.session_state.daily_db[date_key] = past
    else: st.session_state.daily_db[date_key] = {t: defaults.copy() for t in specs}
    save_db(); time.sleep(0.5); st.rerun()

def generate_dummy_data(specs, defaults):
    base = datetime.now()
    for i in range(14, -1, -1):
        d_key = (base - timedelta(days=i)).strftime("%Y-%m-%d")
        new_data = {}
        for t in specs:
            data = defaults.copy()
            data['qty'] = round(random.uniform(100, 500), 1)
            data['av'] = round(random.uniform(0.1, 1.0), 3)
            data['org_cl'] = round(random.uniform(5, 20), 1)
            data['inorg_cl'] = round(random.uniform(1, 5), 1)
            data['water'] = round(random.uniform(10, 100), 1)
            data['metal'] = round(random.uniform(1, 10), 1)
            new_data[t] = data
        st.session_state.daily_db[d_key] = new_data
    save_db(); st.toast("테스트 데이터 생성 완료"); time.sleep(0.5); st.rerun()

def factory_reset():
    st.session_state.daily_db = {}; st.session_state.history_log = []; st.session_state.qc_log = []
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    st.rerun()

def log_action(date_key, action_type, desc, tanks_involved, current_db):
    snapshot = {}
    for t in tanks_involved: snapshot[t] = copy.deepcopy(current_db[t])
    st.session_state.history_log.append({
        "time": datetime.now().strftime("%H:%M:%S"), "date": date_key, "type": action_type, "desc": desc, "snapshot": snapshot
    })
    save_logs()

def log_qc_diff(date_key, tank_name, param, predicted, actual):
    if abs(actual - predicted) > 0.001:
        st.session_state.qc_log.append({
            "날짜": date_key, "탱크": tank_name, "항목": param, "예상값": round(predicted, 3), "실측값": round(actual, 3), "오차": round(actual - predicted, 3)
        })
        save_logs()

def undo_last_action(current_db):
    if not st.session_state.history_log: return
    last = st.session_state.history_log.pop()
    if not last['snapshot']: return
    for t, data in last['snapshot'].items(): current_db[t] = data
    save_db(); save_logs(); st.toast(f"취소 완료: {last['desc']}"); time.sleep(0.5); st.rerun()

def calc_blend(cq, cv, iq, iv):
    if cq + iq == 0: return 0.0
    return ((cq * cv) + (iq * iv)) / (cq + iq)

def propagate_changes(start_date, tank, changes):
    dates = sorted(st.session_state.daily_db.keys())
    for d in dates:
        if d > start_date and tank in st.session_state.daily_db[d]:
            tgt = st.session_state.daily_db[d][tank]
            for k, v in changes.items():
                if abs(v) > 0.0001: tgt[k] = max(0.0, tgt[k] + v)
    save_db()

# ==========================================
# 3. 메인 화면 구성
# ==========================================

SPECS, DEFAULTS = init_system()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2823/2823528.png", width=50)
    st.title("신항공장 생산관리")
    st.caption("Ver 23.4 (Fix HTML Error)")
    
    st.markdown("---")
    selected_date = st.date_input("📆 기준 날짜", datetime.now())
    DATE_KEY = selected_date.strftime("%Y-%m-%d")
    TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)
    
    st.markdown("---")
    menu = st.radio("MENU", [
        "1. 통합 대시보드 (Dashboard)", 
        "2. 운영 실적 입력 (Input)", 
        "3. Lab