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
    # 탱크 스펙 정의
    tank_specs = {
        'TK-310':   {'max': 750,  'type': 'Buffer'},
        'TK-710':   {'max': 760,  'type': 'Prod'},
        'TK-720':   {'max': 760,  'type': 'Prod'},
        'TK-6101':  {'max': 5700, 'type': 'Shore'},
        'UTK-308':  {'max': 5400, 'type': 'Shore'},
        'UTK-1106': {'max': 6650, 'type': 'Shore'}
    }
    
    # 기본 데이터값 (0으로 초기화)
    default_vals = {
        'qty': 0.0, 'av': 0.0, 'water': 0, 
        'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
    }
    
    # DB 초기화
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = {}
        
    # 작업 이력(History) 저장소 초기화
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

# 작업 기록 함수 (Undo용)
def log_action(desc, tanks_involved, current_db):
    snapshot = {}
    for t_name in tanks_involved:
        snapshot[t_name] = copy.deepcopy(current_db[t_name])
    
    # 에러가 났던 부분 수정 (안전하게 작성)
    log_entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "desc": desc,
        "snapshot": snapshot
    }
    st.session_state.history_log.append(log_entry)

# 실행 취소 함수
def undo_last_action(current_db):
    if not st.session_state.history_log:
        st.sidebar.error("취소할 작업이 없습니다.")
        return

    last_action = st.session_state.history_log.pop()
    
    for t_name, prev_data in last_action['snapshot'].items():
        current_db[t_name] = prev_data
        
    st.sidebar.success(f"취소 완료: {last_action['desc']}")
    time.sleep(0.5)
    st.rerun()

# 블렌딩 계산 함수
def calc_blend(curr_qty, curr_val, in_qty, in_val):
    total_qty = curr_qty + in_qty
    if total_qty == 0:
        return 0.0
    
    numerator = (curr_qty * curr_val) + (in_qty * in_val)
    return numerator / total_qty

# ==========================================
# 메인 실행 로직
# ==========================================

SPECS, DEFAULTS = load_data()

st.sidebar.title("🏭 생산관리 System")
st.sidebar.caption("Ver 9.3 (Fix)")

# 날짜 선택
selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
DATE_KEY = selected_date.strftime("%Y-%m-%d")

# 데이터 로드
TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)

# 실행 취소 UI
st.sidebar.markdown("---")
st.sidebar.markdown("### ↩️ 실행 취소")
if st.session_state.history_log:
    last_job = st.session_state.history_log[-1]['desc']
    st.sidebar.info(f"마지막: {last_job}")
    if st.sidebar.button("방금 작업 취소 (Undo)"):
        undo_last_action(TODAY_DATA)
else:
    st.sidebar.write("기록된 작업 없음")

# 메뉴
st.sidebar.markdown("---")
menu = st.sidebar.radio("메뉴 이동", 
    ["1. 전체 모니터링", 
     "2. 1차 공정 (R-1140)", 
     "3. 2차 정제 (EV-6000)", 
     "4. 이송 및 선적", 
     "5. 데이터 강제 수정"]
)

st.header(f"📅 {DATE_KEY} : {menu}")

# ---------------------------------------------------------
# 1. 모니터링
# ---------------------------------------------------------
if menu == "1. 전체 모니터링":
    st.subheader("📊 탱크별 재고 및 품질 현황")
    
    display_rows = []
    for t_name in SPECS:
        d = TODAY_DATA[t_name]
        display_rows.append({
            "탱크명": t_name,
            "구분": SPECS[t_name]['type'],
            "재고 (MT)": f"{d['qty']:.1f}",
            "AV": f"{d['av']:.3f}",
            "Org Cl": f"{d['org_cl']:.1f}",
            "InOrg Cl": f"{d['inorg_cl']:.1f}",
            "P (인)": f"{d['p']:.1f}",
            "수분": f"{d['water']:.0f}",
            "Metal": f"{d['metal']:.1f}"
        })
    df = pd.DataFrame(display_rows)
    st.table(df)

# ---------------------------------------------------------
# 2. 1차 공정
# ---------------------------------------------------------
elif menu == "2. 1차 공정 (R-1140)":
    st.info("원료 → R-1140 → TK-310 입고")
    st.metric("현재 TK-310 재고", f"{TODAY_DATA['TK-310']['qty']:.1f} MT")

    with st.form("form_process_1"):
        c1, c2 = st.columns(2)
        with c1: in_qty = st.number_input("생산량 (MT)", min_value=0.0, step=10.0)
        with c2:
            in_av = st.number_input("R-1140 AV", min_value=0.0, step=0.1)
            in_cl = st.number_input("R-1140 Org Cl", min_value=0.0, step=1.0)
            
        if st.form_submit_button("💾 TK-310 입고 저장"):
            log_action(f"1차공정 입고 (+{in_qty}MT)", ['TK-310'], TODAY_DATA)
            
            tgt = TODAY_DATA['TK-310']
            tgt['av'] = calc_blend(tgt['qty'], tgt['av'], in_qty, in_av)
            tgt['org_cl'] = calc_blend(tgt['qty'], tgt['org_cl'], in_qty, in_cl)
            tgt['qty'] += in_qty
            
            st.success("저장 완료!")
            st.rerun()

# ---------------------------------------------------------
# 3. 2차 정제
# ---------------------------------------------------------
elif menu == "3. 2차 정제 (EV-6000)":
    st.info("TK-310 → EV-6000 → 제품탱크")
    st.write(f"**Source: TK-310** (재고: {TODAY_DATA['TK-310']['qty']:.1f} MT)")

    with st.form("form_process_2"):
        c1, c2, c3 = st.columns(3)
        with c1: feed_qty = st.number_input("TK-310 투입량 (MT)", 0.0)
        with c2: target_tk = st.selectbox("받는 탱크", ["TK-710", "TK-720"])
        with c3: prod_qty = st.number_input("제품 생산량 (MT)", 0.0)
            
        st.markdown("---")
        q1, q2 = st.columns(2)
        with q1:
            q_av = st.number_input("AV", 0.0)
            q_wa = st.number_input("수분", 0)
            q_me = st.number_input("Metal", 0.0)
        with q2:
            q_oc = st.number_input("Org Cl", 0.0)
            q_ic = st.number_input("InOrg Cl", 0.0)
            q_p = st.number_input("P (인)", 0.0)
            
        if st.form_submit_button("💾 정제 생산 저장"):
            src = TODAY_DATA['TK-310']
            tgt = TODAY_DATA[target_tk]
            
            if src['qty'] < feed_qty:
                st.error("재고 부족")
            else:
                log_action(f"2차정제 ({target_tk} +{prod_qty}MT)", ['TK-310', target_tk], TODAY_DATA)
                
                tgt['av'] = calc_blend(tgt['qty'], tgt['av'], prod_qty, q_av)
                tgt['water'] = calc_blend(tgt['qty'], tgt['water'], prod_qty, q_wa)
                tgt['metal'] = calc_blend(tgt['qty'], tgt['metal'], prod_qty, q_me)
                tgt['org_cl'] = calc_blend(tgt['qty'], tgt['org_cl'], prod_qty, q_oc)
                tgt['inorg_cl'] = calc_blend(tgt['qty'], tgt['inorg_cl'], prod_qty, q_ic)
                tgt['p'] = calc_blend(tgt['qty'], tgt['p'], prod_qty, q_p)
                
                src['qty'] -= feed_qty
                tgt['qty'] += prod_qty
                
                st.success("저장 완료!")
                st.rerun()

# ---------------------------------------------------------
# 4. 이송 및 선적
# ---------------------------------------------------------
elif menu == "4. 이송 및 선적":
    tab1, tab2 = st.tabs(["🚛 탱크 간 이송", "🚢 수출 선적"])
    
    with tab1:
        with st.form("form_transfer"):
            c1, c2, c3 = st.columns(3)
            with c1: f_tk = st.selectbox("From", ["TK-710", "TK-720"])
            with c2: t_tk = st.selectbox("To", ["TK-6101", "UTK-308", "UTK-1106"])
            with c3: m_qty = st.number_input("이송량 (MT)", 0.0)
                
            if st.form_submit_button("이송 실행"):
                s_data = TODAY_DATA[f_tk]
                t_data = TODAY_DATA[t_tk]
                
                if s_data['qty'] < m_qty:
                    st.error("재고 부족")
                else:
                    log_action(f"이송 ({f_tk}->{t_tk} {m_qty}MT)", [f_tk, t_tk], TODAY_DATA)
                    
                    for k in DEFAULTS:
                        if k != 'qty': t_data[k] = calc_blend(t_data['qty'], t_data[k], m_qty, s_data[k])
                    s_data['qty'] -= m_qty
                    t_data['qty'] += m_qty
                    st.success("이송 완료")
                    st.rerun()

    with tab2:
        with st.form("form_ship"):
            c1, c2 = st.columns(2)
            with c1: s_tk = st.selectbox("출하 탱크", ["TK-6101", "UTK-308", "UTK-1106"])
            with c2: out_qty = st.number_input("선적량 (MT)", 0.0)
                
            if st.form_submit_button("선적 실행"):
                tk_data = TODAY_DATA[s_tk]
                
                log_action(f"선적 ({s_tk} -{out_qty}MT)", [s_tk], TODAY_DATA)
                
                tk_data['qty'] -= out_qty
                if tk_data['qty'] < 0: tk_data['qty'] = 0
                st.success("출하 완료")
                st.rerun()

# ---------------------------------------------------------
# 5. 데이터 보정
# ---------------------------------------------------------
elif menu == "5. 데이터 강제 수정":
    st.warning("실측값으로 데이터를 강제 수정합니다.")
    target = st.selectbox("수정할 탱크", list(SPECS.keys()))
    curr = TODAY_DATA[target]
    
    with st.form("form_correct"):
        c1, c2 = st.columns(2)
        with c1:
            n_qty = st.number_input("실측 재고", value=float(curr['qty']))
            n_av = st.number_input("실측 AV", value=float(curr['av']))
        with c2:
            n_cl = st.number_input("실측 Org Cl", value=float(curr['org_cl']))
            
        if st.form_submit_button("수정 데이터 반영"):
            log_action(f"데이터 보정 ({target})", [target], TODAY_DATA)
            
            curr['qty'] = n_qty
            curr['av'] = n_av
            curr['org_cl'] = n_cl
            st.success("수정되었습니다.")
            st.rerun()