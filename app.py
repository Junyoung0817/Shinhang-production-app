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
    
    /* Spec Out 경고 스타일 */
    .spec-out { 
        color: #e74c3c !important; 
        font-weight: 900 !important; 
        text-decoration: underline;
    }

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
    st.caption("Ver 33.0 (Error Fix)")
    
    st.markdown("---")
    selected_date = st.date_input("📆 기준 날짜", datetime.now())
    DATE_KEY = selected_date.strftime("%Y-%m-%d")
    TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)
    
    st.markdown("---")
    menu = st.radio("MENU", [
        "1. 통합 대시보드 (Dashboard)", 
        "2. 운영 실적 입력 (Input)", 
        "3. Lab 분석 보정 (Correction)",
        "4. 계약 품질 관리 (Contract)", 
        "5. QC 오차 분석 (Analysis)"
    ])
    
    st.markdown("---")
    if st.session_state.history_log:
        if st.button("↩️ 실행 취소 (Undo)"): undo_last_action(TODAY_DATA)
    
    # 백업/복구 시스템
    with st.expander("🛠️ 시스템 관리 (백업/복구)"):
        st.markdown("##### 💾 데이터 백업")
        
        db_json = json.dumps(st.session_state.daily_db, indent=4, ensure_ascii=False)
        st.download_button("DB 다운로드 (.json)", db_json, file_name="factory_db.json", mime="application/json")
        
        log_data = {'history': st.session_state.history_log, 'qc': st.session_state.qc_log, 'production': st.session_state.production_log}
        log_json = json.dumps(log_data, indent=4, ensure_ascii=False)
        st.download_button("로그 다운로드 (.json)", log_json, file_name="factory_logs.json", mime="application/json")
        
        cont_json = json.dumps(st.session_state.contracts, indent=4, ensure_ascii=False)
        st.download_button("계약서 다운로드 (.json)", cont_json, file_name="factory_contracts.json", mime="application/json")
        
        st.markdown("---")
        st.markdown("##### 🔄 데이터 복구")
        
        u_db = st.file_uploader("DB 파일", type=['json'], key="u_db")
        if u_db:
            try: st.session_state.daily_db = json.load(u_db); save_db_state(); st.success("DB 복구 완료")
            except: st.error("파일 오류")
            
        u_log = st.file_uploader("로그 파일", type=['json'], key="u_log")
        if u_log:
            try: 
                d = json.load(u_log)
                st.session_state.history_log = d.get('history', [])
                st.session_state.qc_log = d.get('qc', [])
                st.session_state.production_log = d.get('production', {})
                save_logs_state(); st.success("로그 복구 완료")
            except: st.error("파일 오류")
            
        u_cont = st.file_uploader("계약서 파일", type=['json'], key="u_cont")
        if u_cont:
            try: st.session_state.contracts = json.load(u_cont); save_contracts_state(); st.success("계약 복구 완료")
            except: st.error("파일 오류")

        if st.button("데이터 생성 (Test)"): generate_dummy_data(SPECS, DEFAULTS)
        if st.button("공장 초기화", type="primary"): factory_reset()

# 상단 헤더 (오류 수정됨: 한 줄로 연결)
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
    
    # [수정] 들여쓰기 문제를 피하기 위해 모든 HTML을 한 줄로 합침
    h1 = f'<div style="background-color:white; padding:20px 30px; border-radius:12px; box-shadow:0 4px 6px rgba(0,0,0,0.02); margin-bottom:25px; border-top:4px solid #e74c3c;"><div style="display:flex; justify-content:space-between; align-items:center;"><div><h3 style="margin:0; color:#32325d;">2026 신항공장 생산 통합 시스템 (Pro)</h3><span style="color:#8898aa; font-size:0.9rem;">Date: {DATE_KEY}</span></div><div style="text-align:right;"><span style="background:#d4edda; color:#155724; padding:5px 12px; border-radius:20px; font-size:0.85rem; font-weight:600;">● System Active</span></div></div>'
    h2 = f'<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:20px; width:100%; margin-top:20px; padding-top:20px; border-top:1px solid #e9ecef;"><div style="border-right:1px solid #eee; padding-right:20px;"><div style="font-size:0.9rem; color:#11cdef; font-weight:600; text-transform:uppercase; margin-bottom:8px;">● 월간 PTU 생산량</div><div style="font-size:1.8rem; font-weight:800; color:#32325d; line-height:1.2;">{monthly_prod:,.1f} <span style="font-size:1.0rem; color:#8898aa; font-weight:500;">Ton</span></div><div style="font-size:0.8rem; color:#aaa; margin-top:5px;">(TK-710 + 720 합계)</div></div>'
    h3 = f'<div style="border-right:1px solid #eee; padding-right:20px;"><div style="font-size:0.9rem; color:#5e72e4; font-weight:600; text-transform:uppercase; margin-bottom:8px;">TK-6101 (SHORE)</div><div style="font-size:1.8rem; font-weight:800; color:#32325d; line-height:1.2;">{tk_6101:,.1f} <span style="font-size:1.0rem; color:#8898aa; font-weight:500;">Ton</span></div></div>'
    h4 = f'<div style="border-right:1px solid #eee; padding-right:20px;"><div style="font-size:0.9rem; color:#5e72e4; font-weight:600; text-transform:uppercase; margin-bottom:8px;">UTK-308 (SHORE)</div><div style="font-size:1.8rem; font-weight:800; color:#32325d; line-height:1.2;">{utk_308:,.1f} <span style="font-size:1.0rem; color:#8898aa; font-weight:500;">Ton</span></div></div>'
    h5 = f'<div><div style="font-size:0.9rem; color:#5e72e4; font-weight:600; text-transform:uppercase; margin-bottom:8px;">UTK-1106 (SHORE)</div><div style="font-size:1.8rem; font-weight:800; color:#32325d; line-height:1.2;">{utk_1106:,.1f} <span style="font-size:1.0rem; color:#8898aa; font-weight:500;">Ton</span></div></div></div></div>'
    
    st.markdown(h1+h2+h3+h4+h5, unsafe_allow_html=True)

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
            # 계약 체크
            contract_check = {}
            if spec['type'] == 'Shore':
                c_list = list(st.session_state.contracts.keys())
                if c_list:
                    selected_c = st.selectbox(f"📦 {t_name} 출하처", ["선택안함"] + c_list, key=f"sel_{t_name}")
                    if selected_c != "선택안함":
                        contract_check = st.session_state.contracts[selected_c]
                else:
                    st.caption("등록된 계약 없음")

            def get_val_style(val, key):
                if spec['type'] != 'Shore': return ''
                if contract_check and key in contract_check:
                    limit = contract_check[key]
                    if val > limit: return f'color: #e74c3c; font-weight: 800; text-decoration: underline; cursor: help;'
                return ''

            st_av = get_val_style(d['av'], 'av')
            st_water = get_val_style(d['water'], 'water')
            st_cl = get_val_style(total_cl, 'total_cl')
            st_p = get_val_style(d['p'], 'p')
            st_metal = get_val_style(d['metal'], 'metal')
            
            # [수정] 카드 HTML도 한 줄로 연결
            c1 = f'<div class="tank-card"><div style="display:flex; justify-content:space-between; align-items:center;"><div style="font-weight:bold; font-size:1.1rem; color:#32325d;">{spec["icon"]} {t_name}</div><span style="background:{spec["color"]}20; color:{spec["color"]}; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">{spec["type"]}</span></div>'
            c2 = f'<div style="margin-top:15px; margin-bottom:10px;"><div class="metric-value" style="font-size:1.5rem;">{d["qty"]:.1f} <span class="metric-unit">Ton</span></div></div>'
            c3 = f'<div style="margin-bottom:15px;"><div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:3px; color:#8898aa;"><span>Level</span><span>{pct:.1f}%</span></div><div style="width:100%; background:#f6f9fc; height:6px; border-radius:10px;"><div style="width:{pct}%; background:{spec["color"]}; height:6px; border-radius:10px;"></div></div></div>'
            c4 = f'<div class="quality-grid"><div class="q-row"><span class="q-label">AV</span><span class="q-val" style="{st_av}">{d["av"]:.2f}</span></div><div class="q-row"><span class="q-label">Water</span><span class="q-val" style="{st_water}">{d["water"]:.1f}</span></div><div class="q-row"><span class="q-label">Total Cl</span><span class="q-val" style="{st_cl}">{total_cl:.1f}</span></div><div class="q-row"><span class="q-label">Total Metal</span><span class="q-val" style="{st_metal}">{d["metal"]:.1f}</span></div><div class="q-row"><span class="q-label" style="font-size:0.8em; padding-left:10px;">└ Org Cl</span><span class="q-val" style="font-size:0.8em;">{org_cl:.1f}</span></div><div class="q-row"><span class="q-label" style="font-size:0.8em; padding-left:10px;">└ InOrg Cl</span><span class="q-val" style="font-size:0.8em;">{inorg_cl:.1f}</span></div><div class="q-row"><span class="q-label">P</span><span class="q-val" style="{st_p}">{d["p"]:.1f}</span></div></div></div><div style="margin-bottom:20px"></div>'
            
            st.markdown(c1+c2+c3+c4, unsafe_allow_html=True)
            
    with st.expander("📋 전체 데이터 테이블 보기"):
        rows = []
        for t in SPECS:
            d = TODAY_DATA[t]
            rows.append({
                "탱크": t, "구분": SPECS[t]['type'],
                "재고": d['qty'], "AV": d['av'], "Water": d['water'],
                "Total Cl": d.get('org_cl', 0) + d.get('inorg_cl', 0),
                "Org Cl": d.get('org_cl', 0), "InOrg Cl": d.get('inorg_cl', 0),
                "P": d['p'], "Total Metal": d['metal']
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ---------------------------------------------------------
# 2. 운영 실적 입력
# ---------------------------------------------------------
elif menu == "2. 운영 실적 입력 (Input)":
    
    t1, t2, t3 = st.tabs(["1차 정제 공정", "2차 정제 공정", "이송/출하"])
    
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            tk = TODAY_DATA['TK-310']
            st.markdown("##### 🏭 TK-310 현황")
            with st.container(border=True):
                st.metric("현재고", f"{tk['qty']:.1f} Ton")
                st.markdown("---")
                col_a, col_b = st.columns(2)
                col_a.metric("AV", f"{tk['av']:.2f}")
                col_b.metric("Water", f"{tk['water']:.1f}")
                col_a.metric("Org Cl", f"{tk['org_cl']:.1f}")
                col_b.metric("InOrg Cl", f"{tk['inorg_cl']:.1f}")

        with c2:
            with st.container(border=True):
                st.markdown("#### 📝 1차 생산 실적 입력")
                with st.form("f1"):
                    qty = st.number_input("생산량 (Ton)", 0.0, step=10.0)
                    c_a, c_b = st.columns(2)
                    av = c_a.number_input("AV", 0.0, step=0.1, format="%.1f")
                    
                    cl_o = c_b.number_input("Org Cl (ppm)", 0.0, step=0.1, format="%.1f")
                    cl_i = c_b.number_input("InOrg Cl (ppm)", 0.0, step=0.1, format="%.1f")
                    
                    if st.form_submit_button("저장 (Save)", type="primary"):
                        log_action(DATE_KEY, "입고", f"1차 +{qty}", ['TK-310'], TODAY_DATA)
                        t = TODAY_DATA['TK-310']
                        t['av'] = calc_blend(t['qty'], t['av'], qty, av)
                        t['org_cl'] = calc_blend(t['qty'], t['org_cl'], qty, cl_o)
                        t['inorg_cl'] = calc_blend(t['qty'], t['inorg_cl'], qty, cl_i)
                        t['qty'] += qty
                        save_db_state(); st.success("저장 완료"); st.rerun()

    with t2:
        c1, c2 = st.columns([1, 2])
        with c1:
            tk = TODAY_DATA['TK-310']
            st.markdown("##### 🏭 원료(TK-310) 현황")
            with st.container(border=True):
                st.metric("투입 가능 재고", f"{tk['qty']:.1f} Ton")
                st.markdown("---")
                col_a, col_b = st.columns(2)
                col_a.metric("AV", f"{tk['av']:.2f}")
                col_b.metric("Water", f"{tk['water']:.1f}")
                
        with c2:
            with st.container(border=True):
                st.markdown("#### 📝 2차 정제 실적 입력")
                with st.form("f2"):
                    c_1, c_2, c_3 = st.columns(3)
                    f_q = c_1.number_input("투입량 (Ton)", 0.0)
                    dest = c_2.selectbox("생산 탱크", ["TK-710", "TK-720"])
                    p_q = c_3.number_input("생산량 (Ton)", 0.0)
                    st.markdown("---")
                    q1, q2 = st.columns(2)
                    qa = q1.number_input("AV", 0.0, step=0.1, format="%.1f")
                    qw = q1.number_input("Water", 0.0, step=0.1, format="%.1f")
                    qm = q1.number_input("Total Metal", 0.0, step=0.1, format="%.1f")
                    
                    qo = q2.number_input("Org Cl", 0.0, step=0.1, format="%.1f")
                    qi = q2.number_input("InOrg Cl", 0.0, step=0.1, format="%.1f")
                    qp = q2.number_input("P", 0.0, step=0.1, format="%.1f")
                    
                    if st.form_submit_button("저장 (Save)", type="primary"):
                        log_action(DATE_KEY, "생산", f"2차 {dest} +{p_q}", ['TK-310', dest], TODAY_DATA)
                        log_production(DATE_KEY, p_q)
                        src = TODAY_DATA['TK-310']; tgt = TODAY_DATA[dest]
                        if src['qty'] < f_q: st.error("재고 부족")
                        else:
                            tgt['av'] = calc_blend(tgt['qty'], tgt['av'], p_q, qa)
                            tgt['water'] = calc_blend(tgt['qty'], tgt['water'], p_q, qw)
                            tgt['metal'] = calc_blend(tgt['qty'], tgt['metal'], p_q, qm)
                            tgt['org_cl'] = calc_blend(tgt['qty'], tgt['org_cl'], p_q, qo)
                            tgt['inorg_cl'] = calc_blend(tgt['qty'], tgt['inorg_cl'], p_q, qi)
                            tgt['p'] = calc_blend(tgt['qty'], tgt['p'], p_q, qp)
                            src['qty'] -= f_q; tgt['qty'] += p_q
                            save_db_state(); st.success("저장 완료"); st.rerun()

    with t3:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("#### 🚛 이송 (Transfer)")
                with st.form("ft"):
                    f = st.selectbox("From", ["TK-710", "TK-720"])
                    t = st.selectbox("To", ["TK-6101", "UTK-308", "UTK-1106"])
                    q = st.number_input("이송량", 0.0)
                    if st.form_submit_button("이송 실행"):
                        log_action(DATE_KEY, "이송", f"{f}->{t} {q}", [f, t], TODAY_DATA)
                        src = TODAY_DATA[f]; tgt = TODAY_DATA[t]
                        if src['qty'] < q: st.error("부족")
                        else:
                            for k in DEFAULTS: 
                                if k!='qty': tgt[k] = calc_blend(tgt['qty'], tgt[k], q, src[k])
                            src['qty'] -= q; tgt['qty'] += q
                            save_db_state(); st.success("완료"); st.rerun()
        with c2:
            with st.container(border=True):
                st.markdown("#### 🚢 출하 (Shipment)")
                with st.form("fs"):
                    s = st.selectbox("출하 탱크", ["TK-6101", "UTK-308", "UTK-1106"])
                    q = st.number_input("선적량 (Ton)", 0.0)
                    if st.form_submit_button("선적 실행", type="primary"):
                        log_action(DATE_KEY, "선적", f"{s} -{q}", [s], TODAY_DATA)
                        tk = TODAY_DATA[s]
                        tk['qty'] -= q; 
                        if tk['qty'] < 0: tk['qty'] = 0
                        save_db_state(); st.success("완료"); st.rerun()

# ---------------------------------------------------------
# 3. Lab 분석 보정 (Correction)
# ---------------------------------------------------------
elif menu == "3. Lab 분석 보정 (Correction)":
    
    with st.container(border=True):
        st.subheader("🧪 Lab 데이터 보정")
        st.markdown("실험실 분석 결과를 입력하면, **오차만큼 미래 데이터까지 자동 보정**됩니다.")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            edit_date = st.date_input("분석(샘플링) 날짜", datetime.now() - timedelta(days=1))
            edit_key = edit_date.strftime("%Y-%m-%d")
            
            if edit_key not in st.session_state.daily_db:
                 new_db = get_today_data(edit_key, SPECS, DEFAULTS)
            edit_data = st.session_state.daily_db[edit_key]
            
            target_tank = st.selectbox("대상 탱크", list(SPECS.keys()))
            curr = edit_data[target_tank]
            
            st.markdown(f"###### 📊 {target_tank} 현재 전산값 (System Data)")
            sys_df = pd.DataFrame({
                "항목": ["재고", "AV", "Water", "Org Cl", "InOrg Cl", "P", "Total Metal"],
                "값": [
                    f"{curr['qty']:.1f}", f"{curr['av']:.2f}", f"{curr['water']:.1f}",
                    f"{curr['org_cl']:.1f}", f"{curr['inorg_cl']:.1f}",
                    f"{curr['p']:.1f}", f"{curr['metal']:.1f}"
                ]
            })
            st.dataframe(sys_df, hide_index=True, use_container_width=True)

        with c2:
            with st.form("correction_form"):
                st.markdown("##### 📝 실측값 입력 (Lab Data)")
                n_qty = st.number_input("실측 재고", value=float(curr['qty']))
                c_a, c_b = st.columns(2)
                n_av = c_a.number_input("실측 AV", value=float(curr['av']), step=0.1, format="%.1f")
                n_wa = c_b.number_input("실측 Water", value=float(curr['water']), step=0.1, format="%.1f")
                
                n_cl = c_a.number_input("실측 Org Cl", value=float(curr['org_cl']), step=0.1, format="%.1f")
                n_icl = c_b.number_input("실측 InOrg Cl", value=float(curr['inorg_cl']), step=0.1, format="%.1f")
                n_p = c_a.number_input("실측 P", value=float(curr['p']), step=0.1, format="%.1f")
                n_mt = c_b.number_input("실측 Total Metal", value=float(curr['metal']), step=0.1, format="%.1f")
                
                auto_sync = st.checkbox("✅ 미래 데이터 자동 보정 (Auto-Sync)", value=True)
                
                if st.form_submit_button("보정 실행", type="primary"):
                    deltas = {
                        'qty': n_qty - curr['qty'], 'av': n_av - curr['av'], 'water': n_wa - curr['water'],
                        'org_cl': n_cl - curr['org_cl'], 'inorg_cl': n_icl - curr['inorg_cl'],
                        'p': n_p - curr['p'], 'metal': n_mt - curr['metal']
                    }
                    log_action(edit_key, "분석반영", f"{target_tank} 보정", [target_tank], edit_data)
                    
                    check_list = [
                        ("재고", curr['qty'], n_qty), ("AV", curr['av'], n_av), ("Water", curr['water'], n_wa),
                        ("Org Cl", curr['org_cl'], n_cl), ("InOrg Cl", curr['inorg_cl'], n_icl),
                        ("P", curr['p'], n_p), ("Total Metal", curr['metal'], n_mt)
                    ]
                    for label, p_val, a_val in check_list:
                        log_qc_diff(edit_key, target_tank, label, p_val, a_val)
                    
                    curr['qty'] = n_qty; curr['av'] = n_av; curr['water'] = n_wa
                    curr['org_cl'] = n_cl; curr['inorg_cl'] = n_icl; curr['p'] = n_p; curr['metal'] = n_mt
                    
                    if auto_sync: propagate_changes(edit_key, target_tank, deltas)
                    save_db_state(); st.success("보정 완료"); st.rerun()

# ---------------------------------------------------------
# 4. 계약 품질 관리 (Contract)
# ---------------------------------------------------------
elif menu == "4. 계약 품질 관리 (Contract)":
    st.subheader("📑 거래처 계약 스펙 관리")
    
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.markdown("#### 신규 계약 등록")
            with st.form("contract_form"):
                c_name = st.text_input("거래처명 (Contractor)")
                st.caption("Max Quality Limits")
                l_av = st.number_input("Max AV", 0.0, step=0.1)
                l_water = st.number_input("Max Water", 0.0, step=10.0)
                l_cl = st.number_input("Max Total Cl", 0.0, step=1.0)
                l_p = st.number_input("Max P", 0.0, step=1.0)
                l_metal = st.number_input("Max Metal", 0.0, step=1.0)
                
                if st.form_submit_button("계약 등록/수정", type="primary"):
                    if c_name:
                        st.session_state.contracts[c_name] = {
                            'av': l_av, 'water': l_water, 'total_cl': l_cl, 'p': l_p, 'metal': l_metal
                        }
                        save_contracts_state()
                        st.success(f"{c_name} 등록 완료")
                        st.rerun()
                    else:
                        st.error("거래처명을 입력하세요.")
        
        with c2:
            st.markdown("#### 등록된 계약 목록")
            if st.session_state.contracts:
                c_data = []
                for name, specs in st.session_state.contracts.items():
                    row = specs.copy()
                    row['Contractor'] = name
                    c_data.append(row)
                
                df_c = pd.DataFrame(c_data)
                df_c = df_c[['Contractor', 'av', 'water', 'total_cl', 'p', 'metal']]
                st.dataframe(df_c, hide_index=True, use_container_width=True)
                
                d_target = st.selectbox("삭제할 거래처", ["선택"] + list(st.session_state.contracts.keys()))
                if st.button("계약 삭제"):
                    if d_target != "선택":
                        del st.session_state.contracts[d_target]
                        save_contracts_state()
                        st.success("삭제 완료")
                        st.rerun()
            else:
                st.write("등록된 계약이 없습니다.")

# ---------------------------------------------------------
# 5. QC 오차 분석 (Improved with Filters)
# ---------------------------------------------------------
elif menu == "5. QC 오차 분석 (Analysis)":
    st.subheader("📈 QC 오차 트렌드")
    
    if not st.session_state.qc_log:
        st.info("데이터가 없습니다.")
    else:
        df = pd.DataFrame(st.session_state.qc_log)
        
        # 필터링 기능
        with st.container(border=True):
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                tank_filter = st.selectbox("탱크 선택", df['탱크'].unique())
            with col_filter2:
                all_items = df['항목'].unique()
                item_filters = st.multiselect("항목 선택 (Multi-Select)", all_items, default=all_items)
            
            # 필터링 적용
            df_chart = df[(df['탱크'] == tank_filter) & (df['항목'].isin(item_filters))]
            
            if not df_chart.empty:
                st.line_chart(df_chart, x='날짜', y='오차', color='항목')
                st.caption("* 양수(+)는 예측보다 높음 / 음수(-)는 예측보다 낮음")
                
                st.markdown("##### 📋 상세 데이터")
                # [수정] background_gradient 제거 -> 일반 dataframe으로 변경
                st.dataframe(df_chart, use_container_width=True)
            else:
                st.warning("선택된 조건에 맞는 데이터가 없습니다.")