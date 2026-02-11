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
    
    /* 상단 헤더 (Flexbox) */
    .summary-header {
        background-color: white;
        padding: 20px 30px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        margin-bottom: 25px;
        border-top: 4px solid #e74c3c;
    }
    
    .header-row {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: flex-start;
        width: 100%;
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid #e9ecef;
    }
    
    .header-item {
        flex: 1;
        padding-left: 20px;
        border-left: 1px solid #eee;
    }
    .header-item:first-child { padding-left: 0; border-left: none; }
    
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
    
    /* 폰트 스타일 */
    .metric-label { font-size: 0.9rem; color: #8898aa; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;}
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #32325d; line-height: 1.2;}
    .metric-unit { font-size: 1.0rem; color: #8898aa; font-weight: 500; }
    
    /* 품질 그리드 */
    .quality-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 10px;
        margin-top: 15px;
        font-size: 0.85rem;
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
    }
    .q-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px dashed #e9ecef;
        padding-bottom: 3px;
    }
    .q-row:last-child { border-bottom: none; }
    
    .q-label { color: #6c757d; font-weight: 500; }
    .q-val { font-weight: 700; color: #495057; }
    
    .highlight-label { color: #e74c3c; font-weight: 700; }
    .highlight-val { color: #c0392b; font-weight: 800; }

    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        height: 45px;
    }
    
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 데이터 관리
# ---------------------------------------------------------

DB_FILE = 'factory_db.json'
LOG_FILE = 'factory_logs.json'
CONTRACT_FILE = 'factory_contracts.json'

def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_json(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except: pass

def load_db(): return load_json(DB_FILE)
def load_logs(): 
    data = load_json(LOG_FILE)
    return data.get('history', []), data.get('qc', []), data.get('production', {})
def load_contracts(): return load_json(CONTRACT_FILE)

def save_db_state(): save_json(DB_FILE, st.session_state.daily_db)
def save_logs_state():
    data = {
        'history': st.session_state.history_log,
        'qc': st.session_state.qc_log,
        'production': st.session_state.production_log
    }
    save_json(LOG_FILE, data)
def save_contracts_state(): save_json(CONTRACT_FILE, st.session_state.contracts)

def init_system():
    tank_specs = {
        'TK-310':   {'max': 750,  'type': 'Buffer', 'icon': '🏭', 'color': '#2dce89'},
        'TK-710':   {'max': 760,  'type': 'Prod',   'icon': '🏭', 'color': '#11cdef'},
        'TK-720':   {'max': 760,  'type': 'Prod',   'icon': '🏭', 'color': '#11cdef'},
        'TK-6101':  {'max': 5700, 'type': 'Shore',  'icon': '🚢', 'color': '#5e72e4'},
        'UTK-308':  {'max': 5400, 'type': 'Shore',  'icon': '🚢', 'color': '#5e72e4'},
        'UTK-1106': {'max': 6650, 'type': 'Shore',  'icon': '🚢', 'color': '#5e72e4'}
    }
    default_vals = {'qty': 0.0, 'av': 0.0, 'water': 0.0, 'metal': 0.0, 'p': 0.0, 'org_cl': 0.0, 'inorg_cl': 0.0}
    
    if 'daily_db' not in st.session_state: st.session_state.daily_db = load_db()
    
    if ('history_log' not in st.session_state) or ('production_log' not in st.session_state):
        h, q, p = load_logs()
        if 'history_log' not in st.session_state: st.session_state.history_log = h
        if 'qc_log' not in st.session_state: st.session_state.qc_log = q
        if 'production_log' not in st.session_state: st.session_state.production_log = p
        
    if 'contracts' not in st.session_state:
        st.session_state.contracts = load_contracts()
        
    return tank_specs, default_vals

def get_today_data(date_key, specs, defaults):
    if date_key in st.session_state.daily_db:
        data = st.session_state.daily_db[date_key]
        if sum(t['qty'] for t in data.values()) == 0:
            past = find_past_data(date_key)
            if past:
                st.session_state.daily_db[date_key] = past
                save_db_state()
                return past
        return data
    past = find_past_data(date_key)
    if past: st.session_state.daily_db[date_key] = past
    else: st.session_state.daily_db[date_key] = {t: defaults.copy() for t in specs}
    save_db_state()
    return st.session_state.daily_db[date_key]

def find_past_data(current_date_str):
    curr = datetime.strptime(current_date_str, "%Y-%m-%d")
    for i in range(1, 366):
        past = (curr - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            data = st.session_state.daily_db[past]
            if sum(t['qty'] for t in data.values()) > 0: return copy.deepcopy(data)
    return None

def generate_dummy_data(specs, defaults):
    base = datetime.now()
    st.session_state.production_log = {} 
    
    for i in range(30, -1, -1):
        d_date = base - timedelta(days=i)
        d_key = d_date.strftime("%Y-%m-%d")
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
        st.session_state.production_log[d_key] = round(random.uniform(200, 400), 1)
        
    save_db_state(); save_logs_state(); st.toast("테스트 데이터 생성 완료"); time.sleep(0.5); st.rerun()

def factory_reset():
    st.session_state.daily_db = {}
    st.session_state.history_log = []
    st.session_state.qc_log = []
    st.session_state.production_log = {}
    st.session_state.contracts = {}
    for f in [DB_FILE, LOG_FILE, CONTRACT_FILE]:
        if os.path.exists(f): os.remove(f)
    st.rerun()

def log_action(date_key, action_type, desc, tanks_involved, current_db):
    snapshot = {}
    for t in tanks_involved: snapshot[t] = copy.deepcopy(current_db[t])
    st.session_state.history_log.append({
        "time": datetime.now().strftime("%H:%M:%S"), "date": date_key, "type": action_type, "desc": desc, "snapshot": snapshot
    })
    save_logs_state()

def log_production(date_key, amount):
    if date_key in st.session_state.production_log:
        st.session_state.production_log[date_key] += amount
    else:
        st.session_state.production_log[date_key] = amount
    save_logs_state()

def log_qc_diff(date_key, tank_name, param, predicted, actual):
    if abs(actual - predicted) > 0.001:
        st.session_state.qc_log.append({
            "날짜": date_key, "탱크": tank_name, "항목": param, "예상값": round(predicted, 3), "실측값": round(actual, 3), "오차": round(actual - predicted, 3)
        })
        save_logs_state()

def undo_last_action(current_db):
    if not st.session_state.history_log: return
    last = st.session_state.history_log.pop()
    if not last['snapshot']: return
    for t, data in last['snapshot'].items(): current_db[t] = data
    save_db_state(); save_logs_state(); st.toast(f"취소 완료: {last['desc']}"); time.sleep(0.5); st.rerun()

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
    save_db_state()

# ==========================================
# 3. 메인 화면 구성
# ==========================================

SPECS, DEFAULTS = init_system()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2823/2823528.png", width=50)
    st.title("신항공장 생산관리")
    st.caption("Ver 27.0 (Final Complete)")
    
    st.markdown("---")
    selected_date = st.date_input("📆 기준 날짜", datetime.now())
    DATE_KEY = selected_date.strftime("%Y-%m-%d")
    TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)
    
    st.markdown("---")
    menu = st.radio("MENU", [
        "1. 통합 대시보드 (Dashboard)", 
        "2. 운영 실적 입력 (Input)", 
        "3. Lab 분석 보정 (Correction)",
        "4. 거래처 계약 관리 (Contract)", 
        "5. QC 오차 분석 (Analysis)"
    ])
    
    st.markdown("---")
    if st.session_state.history_log:
        if st.button("↩️ 실행 취소 (Undo)"): undo_last_action(TODAY_DATA)
    
    with st.expander("관리자 도구"):
        if st.button("데이터 생성"): generate_dummy_data(SPECS, DEFAULTS)
        if st.button("공장 초기화"): factory_reset()

# 상단 헤더
def render_header(data, selected_dt):
    current_month_str = selected_dt.strftime("%Y-%m")
    monthly_prod = 0.0
    
    if 'production_log' in st.session_state:
        for d_key, amount in st.session_state.production_log.items():
            if d_key.startswith(current_month_str) and d_key <= DATE_KEY:
                monthly_prod += amount
            
    tk_6101 = data['TK-6101']['qty']
    utk_308 = data['UTK-308']['qty']
    utk_1106 = data['UTK-1106']['qty']
    
    html_code = f"""
<div class="summary-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h3 style="margin:0; color:#32325d;">2026 신항공장 생산 통합 시스템 (Pro)</h3>
            <span style="color:#8898aa; font-size:0.9rem;">Date: {DATE_KEY}</span>
        </div>
        <div style="text-align:right;">
            <span style="background:#d4edda; color:#155724; padding:5px 12px; border-radius:20px; font-size:0.85rem; font-weight:600;">● System Active</span>
        </div>
    </div>
    
    <div class="header-row">
        <div class="header-item">
            <div class="metric-label" style="color:#11cdef;">● 월간 PTU 생산량</div>
            <div class="metric-value">{monthly_prod:,.1f} <span class="metric-unit">Ton</span></div>
            <div style="font-size:0.8rem; color:#aaa; margin-top:5px;">(TK-710 + 720 합계)</div>
        </div>
        <div class="header-item">
            <div class="metric-label" style="color:#5e72e4;">TK-6101 (SHORE)</div>
            <div class="metric-value">{tk_6101:,.1f} <span class="metric-unit">Ton</span></div>
        </div>
        <div class="header-item">
            <div class="metric-label" style="color:#5e72e4;">UTK-308 (SHORE)</div>
            <div class="metric-value">{utk_308:,.1f} <span class="metric-unit">Ton</span></div>
        </div>
        <div class="header-item">
            <div class="metric-label" style="color:#5e72e4;">UTK-1106 (SHORE)</div>
            <div class="metric-value">{utk_1106:,.1f} <span class="metric-unit">Ton</span></div>
        </div>
    </div>
</div>
"""
    st.markdown(html_code, unsafe_allow_html=True)

render_header(TODAY_DATA, selected_date)

# ---------------------------------------------------------
# 1. 통합 대시보드
# ---------------------------------------------------------
if menu == "1. 통합 대시보드 (Dashboard)":
    
    if sum(TODAY_DATA['TK-310']['qty'] for t in SPECS) == 0:
        st.info("💡 데이터가 없습니다. 사이드바의 '데이터 생성'을 눌러 테스트 데이터를 만들어보세요.")

    st.markdown("#### 📊 Tank Level Monitoring")
    cols = st.columns(3)
    
    for i, t_name in enumerate(SPECS):
        spec = SPECS[t_name]
        d = TODAY_DATA[t_name]
        pct = min(d['qty'] / spec['max'], 1.0) * 100
        
        org_cl = d.get('org_cl', 0)
        inorg_cl = d.get('inorg_cl', 0)
        total_cl = org_cl + inorg_cl
        
        with cols[i % 3]:
            # 계약 체크 로직
            contract_check = {}
            if spec['type'] == 'Shore':
                c_list = list(st.session_state.contracts.keys())
                if c_list:
                    selected_c = st.selectbox(f"📦 {t_name} 출하처", ["선택안함"] + c_list, key=f"sel_{t_name}")
                    if selected_c != "선택안함":
                        contract_check = st.session_state.contracts[selected_c]
                else:
                    st.caption("등록된 계약 없음")

            # 스타일 생성 함수 (Inline Style로 빨간색 강제 적용)
            def get_val_style(val, key):
                if contract_check and key in contract_check:
                    limit = contract_check[key]
                    if val > limit:
                        return f'color: #e74c3c; font-weight: 800; text-decoration: underline; cursor: help;'
                return ''

            st_av = get_val_style(d['av'], 'av')
            st_water = get_val_style(d['water'], 'water')
            st_cl = get_val_style(total_cl, 'total_cl')
            st_p = get_val_style(d['p'], 'p')
            st_metal = get_val_style(d['metal'], 'metal')
            
            card_html = f"""
<div class="tank-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="font-weight:bold; font-size:1.1rem; color:#32325d;">{spec['icon']} {t_name}</div>
        <span style="background:{spec['color']}20; color:{spec['color']}; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{spec['type']}</span>
    </div>
    <div style="margin-top:15px; margin-bottom:10px;">
        <div class="metric-value" style="font-size:1.5rem;">{d['qty']:,.1f} <span class="metric-unit">Ton</span></div>
    </div>
    <div style="margin-bottom:15px;">
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:3px; color:#8898aa;">
            <span>Level</span><span>{pct:.1f}%</span>
        </div>
        <div style="width:100%; background:#f6f9fc; height:6px; border-radius:10px;">
            <div style="width:{pct}%; background:{spec['color']}; height:6px; border-radius:10px;"></div>
        </div>
    </div>
    <div class="quality-grid">
        <div class="q-row">
            <span class="q-label">AV</span>
            <span class="q-val" style="{st_av}">{d['av']:.2f}</span>
        </div>
        <div class="q-row">
            <span class="q-label">Water</span>
            <span class="q-val" style="{st_water}">{d['water']:.1f}</span>
        </div>
        <div class="q-row">
            <span class="q-label highlight-label">Total Cl</span>
            <span class="q-val highlight-val" style="{st_cl}">{total_cl:.1f}</span>
        </div>
        <div class="q-row">
            <span class="q-label">Total Metal</span>
            <span class="q-val" style="{st_metal}">{d['metal']:.1f}</span>
        </div>
        <div class="q-row">
            <span class="q-label" style="font-size:0.8em; padding-left:10px;">└ Org Cl</span>
            <span class="q-val" style="font-size:0.8em;">{org_cl:.1f}</span>
        </div>
        <div class="q-row">
            <span class="q-label" style="font-size:0.8em; padding-left:10px;">└ InOrg Cl</span>
            <span class="q-val" style="font-size:0.8em;">{inorg_cl:.1f}</span>
        </div>
        <div class="q-row">
            <span class="q-label">P</span>
            <span class="q-val" style="{st_p}">{d['p']:.1f}</span>
        </div>
    </div>
</div>
<div style="margin-bottom:20px"></div>
"""
            st.markdown(card_html, unsafe_allow_html=True)
            
    with st.expander("📋 전체 데이터 테이블 보기"):
        rows = []
        for t in SPECS:
            d = TODAY_DATA[t]
            rows.append({
                "탱크": t, "구분": SPECS[t]['type'],
                "재고": d['qty'], "AV": d['av'], "Water": d['water'],
                "Total Cl": d.get('org_cl', 0) + d.get('inorg_cl',