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
    
    .summary-header {
        background-color: white;
        padding: 20px 25px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        margin-bottom: 25px;
        border-top: 4px solid #e74c3c;
    }
    
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
    
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #32325d; }
    .metric-unit { font-size: 0.9rem; color: #8898aa; font-weight: 500; }
    
    /* 품질 데이터 그리드 */
    .quality-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 15px;
        margin-top: 15px;
        font-size: 0.85rem;
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
    }
    .q-item { 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        border-bottom: 1px dashed #e9ecef;
        padding-bottom: 4px;
    }
    .q-item:last-child { border-bottom: none; }
    
    .q-label { color: #6c757d; font-weight: 500; }
    .q-val { font-weight: 700; color: #495057; }
    
    /* 강조 스타일 */
    .highlight-label { color: #e74c3c; font-weight: 700; }
    .highlight-val { color: #c0392b; font-weight: 800; }

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
# 2. 데이터 관리 및 저장 로직
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
    st.caption("Ver 23.3 (Lab Correction Detail)")
    
    st.markdown("---")
    selected_date = st.date_input("📆 기준 날짜", datetime.now())
    DATE_KEY = selected_date.strftime("%Y-%m-%d")
    TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)
    
    st.markdown("---")
    menu = st.radio("MENU", [
        "1. 통합 대시보드 (Dashboard)", 
        "2. 운영 실적 입력 (Input)", 
        "3. Lab 분석 보정 (Correction)",
        "4. QC 오차 분석 (Analysis)"
    ])
    
    st.markdown("---")
    if st.session_state.history_log:
        if st.button("↩️ 실행 취소 (Undo)"): undo_last_action(TODAY_DATA)
    
    with st.expander("관리자 도구"):
        if st.button("데이터 생성"): generate_dummy_data(SPECS, DEFAULTS)
        if st.button("공장 초기화"): factory_reset()

# 상단 헤더
def render_header(data):
    total = sum(data[t]['qty'] for t in SPECS)
    prod = data['TK-710']['qty'] + data['TK-720']['qty']
    shore = sum(data[t]['qty'] for t in SPECS if SPECS[t]['type']=='Shore')
    
    st.markdown(f"""
    <div class="summary-header">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <h3 style="margin:0; color:#32325d;">2026 신항공장 생산 통합 시스템 (Pro)</h3>
                <span style="color:#8898aa; font-size:0.9rem;">Date: {DATE_KEY}</span>
            </div>
            <div style="text-align:right;">
                <span style="background:#d4edda; color:#155724; padding:5px 12px; border-radius:20px; font-size:0.85rem; font-weight:600;">● System Active</span>
            </div>
        </div>
        <div style="display: flex; gap: 40px; border-top: 1px solid #e9ecef; padding-top: 15px;">
            <div>
                <div class="metric-label" style="color:#2dce89;">● TOTAL STOCK</div>
                <div class="metric-value">{total:,.1f} <span class="metric-unit">Ton</span></div>
            </div>
            <div>
                <div class="metric-label" style="color:#11cdef;">● PRODUCT (BD)</div>
                <div class="metric-value">{prod:,.1f} <span class="metric-unit">Ton</span></div>
            </div>
            <div>
                <div class="metric-label" style="color:#5e72e4;">● SHORE TANK</div>
                <div class="metric-value">{shore:,.1f} <span class="metric-unit">Ton</span></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

render_header(TODAY_DATA)

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
        
        # [자동 계산] Total Cl
        org_cl = d.get('org_cl', 0)
        inorg_cl = d.get('inorg_cl', 0)
        total_cl = org_cl + inorg_cl
        
        with cols[i % 3]:
            st.markdown(f"""
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
                    <div class="q-item"><span class="q-label">AV</span><span class="q-val">{d['av']:.2f}</span></div>
                    <div class="q-item"><span class="q-label">Water</span><span class="q-val">{d['water']:.1f}</span></div>
                    
                    <div class="q-item">
                        <span class="q-label highlight-label">Total Cl</span>
                        <span class="q-val highlight-val">{total_cl:.1f}</span>
                    </div>
                    <div class="q-item"><span class="q-label">Total Metal</span><span class="q-val">{d['metal']:.1f}</span></div>
                    
                    <div class="q-item"><span class="q-label" style="font-size:0.8em">└ Org Cl</span><span class="q-val" style="font-size:0.8em">{org_cl:.1f}</span></div>
                    <div class="q-item"><span class="q-label" style="font-size:0.8em">└ InOrg Cl</span><span class="q-val" style="font-size:0.8em">{inorg_cl:.1f}</span></div>
                    
                    <div class="q-item"><span class="q-label">P</span><span class="q-val">{d['p']:.1f}</span></div>
                    <div class="q-item"></div>
                </div>
            </div>
            <div style="margin-bottom:20px"></div>
            """, unsafe_allow_html=True)
            
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
    
    t1, t2, t3 = st.tabs(["1차 공정 (R-1140)", "2차 정제 (EV-6000)", "이송/출하"])
    
    with t1:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info("📌 **Process Info**\n\n원료 투입 → 반응 → TK-310 입고")
            st.metric("TK-310 현재고", f"{TODAY_DATA['TK-310']['qty']:.1f} Ton")
        with c2:
            with st.container(border=True):
                st.markdown("#### 📝 1차 생산 실적")
                with st.form("f1"):
                    qty = st.number_input("생산량 (Ton)", 0.0, step=10.0)
                    c_a, c_b = st.columns(2)
                    av = c_a.number_input("AV", 0.0, step=0.1, format="%.1f")
                    
                    # Org Cl / InOrg Cl 분리 입력
                    cl_o = c_b.number_input("Org Cl (ppm)", 0.0, step=0.1, format="%.1f")
                    cl_i = c_b.number_input("InOrg Cl (ppm)", 0.0, step=0.1, format="%.1f")
                    
                    if st.form_submit_button("저장 (Save)", type="primary"):
                        log_action(DATE_KEY, "입고", f"1차 +{qty}", ['TK-310'], TODAY_DATA)
                        t = TODAY_DATA['TK-310']
                        t['av'] = calc_blend(t['qty'], t['av'], qty, av)
                        t['org_cl'] = calc_blend(t['qty'], t['org_cl'], qty, cl_o)
                        t['inorg_cl'] = calc_blend(t['qty'], t['inorg_cl'], qty, cl_i)
                        t['qty'] += qty
                        save_db(); st.success("저장 완료"); st.rerun()

    with t2:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info("📌 **Process Info**\n\nTK-310 → 정제 → 제품 탱크")
            st.metric("TK-310 잔량", f"{TODAY_DATA['TK-310']['qty']:.1f} Ton")
        with c2:
            with st.container(border=True):
                st.markdown("#### 📝 2차 정제 실적")
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
                    
                    # Org Cl / InOrg Cl 분리 입력
                    qo = q2.number_input("Org Cl", 0.0, step=0.1, format="%.1f")
                    qi = q2.number_input("InOrg Cl", 0.0, step=0.1, format="%.1f")
                    qp = q2.number_input("P", 0.0, step=0.1, format="%.1f")
                    
                    if st.form_submit_button("저장 (Save)", type="primary"):
                        log_action(DATE_KEY, "생산", f"2차 {dest} +{p_q}", ['TK-310', dest], TODAY_DATA)
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
                            save_db(); st.success("저장 완료"); st.rerun()

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
                            save_db(); st.success("완료"); st.rerun()
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
                        save_db(); st.success("완료"); st.rerun()

# ---------------------------------------------------------
# 3. Lab 분석 보정 (상세 보기 추가됨)
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
            # [상세 표] 현재 모든 품질값 표시
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
                
                # 나머지 항목 (Org/InOrg 분리)
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
                    
                    # QC 로깅 (모든 항목)
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
                    save_db(); st.success("보정 완료"); st.rerun()

# ---------------------------------------------------------
# 4. QC 오차 분석
# ---------------------------------------------------------
elif menu == "4. QC 오차 분석 (Analysis)":
    st.subheader("📈 QC 오차 트렌드")
    
    if not st.session_state.qc_log:
        st.info("데이터가 없습니다.")
    else:
        df = pd.DataFrame(st.session_state.qc_log)
        with st.container(border=True):
            tank_filter = st.selectbox("탱크 필터", df['탱크'].unique())
            df_tank = df[df['탱크'] == tank_filter]
            
            if not df_tank.empty:
                st.line_chart(df_tank, x='날짜', y='오차', color='항목')
                st.caption("* 오차 = 실측값 - 예상값")
            
            with st.expander("상세 데이터 보기"):
                st.dataframe(df, use_container_width=True)