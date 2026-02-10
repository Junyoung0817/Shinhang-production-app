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
    
    if 'daily_db' not in st.session_state:
        st.session_state.daily_db = {}
    if 'history_log' not in st.session_state:
        st.session_state.history_log = []
    if 'qc_log' not in st.session_state:
        st.session_state.qc_log = []
        
    return tank_specs, default_vals

def get_today_data(date_key, specs, defaults):
    if date_key in st.session_state.daily_db:
        return st.session_state.daily_db[date_key]
    
    current_date = datetime.strptime(date_key, "%Y-%m-%d")
    found_data = None
    
    for i in range(1, 366):
        past = (current_date - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            found_data = copy.deepcopy(st.session_state.daily_db[past])
            break
            
    if found_data:
        st.session_state.daily_db[date_key] = found_data
    else:
        new_data = {}
        for t_name in specs:
            new_data[t_name] = defaults.copy()
        st.session_state.daily_db[date_key] = new_data
            
    return st.session_state.daily_db[date_key]

def reset_today_data(date_key, specs, defaults):
    current_date = datetime.strptime(date_key, "%Y-%m-%d")
    found_data = None
    
    # 전일 데이터 찾기
    for i in range(1, 366):
        past = (current_date - timedelta(days=i)).strftime("%Y-%m-%d")
        if past in st.session_state.daily_db:
            found_data = copy.deepcopy(st.session_state.daily_db[past])
            break
    
    if found_data:
        st.session_state.daily_db[date_key] = found_data
        st.toast(f"✅ {date_key} 데이터를 삭제하고 {past} 데이터를 불러왔습니다.")
    else:
        new_data = {}
        for t_name in specs:
            new_data[t_name] = defaults.copy()
        st.session_state.daily_db[date_key] = new_data
        st.toast(f"✅ {date_key} 데이터를 0으로 초기화했습니다.")
    
    time.sleep(1.0)
    st.rerun()

def log_action(date_key, action_type, desc, tanks_involved, current_db):
    snapshot = {}
    for t_name in tanks_involved:
        snapshot[t_name] = copy.deepcopy(current_db[t_name])
    
    st.session_state.history_log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": date_key,
        "type": action_type,
        "desc": desc,
        "snapshot": snapshot
    })

def log_qc_diff(date_key, tank_name, param, predicted, actual):
    diff = actual - predicted
    if abs(diff) > 0.001:
        st.session_state.qc_log.append({
            "날짜": date_key,
            "탱크": tank_name,
            "항목": param,
            "예상값(System)": round(predicted, 3),
            "실측값(Lab)": round(actual, 3),
            "오차(Diff)": round(diff, 3)
        })

def undo_last_action(current_db):
    if not st.session_state.history_log:
        st.sidebar.error("취소할 작업이 없습니다.")
        return

    last = st.session_state.history_log.pop()
    
    if not last['snapshot']:
        st.sidebar.error("초기화 작업은 취소할 수 없습니다.")
        return

    for t_name, prev_data in last['snapshot'].items():
        current_db[t_name] = prev_data
        
    st.sidebar.success(f"취소 완료: {last['desc']}")
    time.sleep(0.5)
    st.rerun()

def calc_blend(curr_qty, curr_val, in_qty, in_val):
    total = curr_qty + in_qty
    if total == 0: return 0.0
    numerator = (curr_qty * curr_val) + (in_qty * in_val)
    return numerator / total_qty

# ==========================================
# 메인 실행 로직
# ==========================================

SPECS, DEFAULTS = load_data()

st.sidebar.title("🏭 생산관리 System")
st.sidebar.caption("Ver 13.1 (Safe Reset)")

# 날짜 선택
selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
DATE_KEY = selected_date.strftime("%Y-%m-%d")

# 데이터 로드
TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)

# [수정됨] 금일 데이터 삭제 버튼 (날짜 표시)
st.sidebar.markdown("---")
# 버튼 이름에 날짜를 넣어서 실수 방지
if st.sidebar.button(f"🗑️ [{DATE_KEY}] 데이터 초기화"):
    reset_today_data(DATE_KEY, SPECS, DEFAULTS)
st.sidebar.caption(f"⚠️ {DATE_KEY}의 입력 데이터를 모두 지우고, 전일 마감 상태로 되돌립니다.")

# 실행 취소
st.sidebar.markdown("---")
st.sidebar.markdown("### ↩️ 실행 취소")
if st.session_state.history_log:
    last_job = st.session_state.history_log[-1]['desc']
    st.sidebar.info(f"Last: {last_job}")
    if st.sidebar.button("방금 작업 취소 (Undo)"):
        undo_last_action(TODAY_DATA)
else:
    st.sidebar.write("기록 없음")

# 메뉴
st.sidebar.markdown("---")
menu = st.sidebar.radio("메뉴 이동", 
    ["1. 전체 모니터링", 
     "2. 1차 공정 (R-1140)", 
     "3. 2차 정제 (EV-6000)", 
     "4. 이송 및 선적", 
     "5. 데이터 강제 수정",
     "6. QC 오차 분석 (Analysis)"]
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
            log_action(DATE_KEY, "입고", f"1차공정 (+{in_qty}MT)", ['TK-310'], TODAY_DATA)
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
                log_action(DATE_KEY, "생산", f"2차정제 ({target_tk} +{prod_qty}MT)", ['TK-310', target_tk], TODAY_DATA)
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
                    log_action(DATE_KEY, "이송", f"이송 ({f_tk}->{t_tk} {m_qty}MT)", [f_tk, t_tk], TODAY_DATA)
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
                log_action(DATE_KEY, "선적", f"선적 ({s_tk} -{out_qty}MT)", [s_tk], TODAY_DATA)
                tk_data['qty'] -= out_qty
                if tk_data['qty'] < 0: tk_data['qty'] = 0
                st.success("출하 완료")
                st.rerun()

# ---------------------------------------------------------
# 5. 데이터 보정
# ---------------------------------------------------------
elif menu == "5. 데이터 강제 수정":
    st.warning("실측값(Lab)으로 데이터를 보정합니다. (오차는 자동으로 기록됩니다)")
    target = st.selectbox("수정할 탱크", list(SPECS.keys()))
    curr = TODAY_DATA[target]
    
    with st.form("form_correct"):
        c1, c2 = st.columns(2)
        with c1:
            n_qty = st.number_input("실측 재고", value=float(curr['qty']))
            n_av = st.number_input("실측 AV", value=float(curr['av']))
        with c2:
            n_cl = st.number_input("실측 Org Cl", value=float(curr['org_cl']))
            
        if st.form_submit_button("보정 및 QC기록 저장"):
            # 1. Undo를 위한 전체 스냅샷 저장
            log_action(DATE_KEY, "강제수정", f"데이터 보정 ({target})", [target], TODAY_DATA)
            
            # 2. QC 분석을 위한 항목별 오차 기록
            log_qc_diff(DATE_KEY, target, "재고", curr['qty'], n_qty)
            log_qc_diff(DATE_KEY, target, "AV", curr['av'], n_av)
            log_qc_diff(DATE_KEY, target, "Org Cl", curr['org_cl'], n_cl)
            
            # 3. 데이터 업데이트
            curr['qty'] = n_qty
            curr['av'] = n_av
            curr['org_cl'] = n_cl
            
            st.success("수정 및 QC 로그 저장 완료!")
            st.rerun()

# ---------------------------------------------------------
# 6. QC 오차 분석
# ---------------------------------------------------------
elif menu == "6. QC 오차 분석 (Analysis)":
    st.title("📈 예측 vs 실측 오차 분석")
    st.info("5번 메뉴에서 수정한 데이터(예상값과 실측값의 차이)를 분석합니다.")
    
    tab_list, tab_graph = st.tabs(["📋 상세 내역 (List)", "📊 그래프 분석 (Chart)"])
    
    if len(st.session_state.qc_log) == 0:
        st.write("아직 기록된 오차 데이터가 없습니다.")
    else:
        df_qc = pd.DataFrame(st.session_state.qc_log)
        
        with tab_list:
            st.dataframe(df_qc, use_container_width=True)
            
        with tab_graph:
            tank_list = df_qc['탱크'].unique()
            sel_tank = st.selectbox("분석할 탱크 선택", tank_list)
            
            df_tank = df_qc[df_qc['탱크'] == sel_tank]
            
            if df_tank.empty:
                st.write("선택한 탱크의 데이터가 없습니다.")
            else:
                params = df_tank['항목'].unique()
                for p in params:
                    st.subheader(f"📌 {sel_tank} - {p} 오차 추이")
                    df_p = df_tank[df_tank['항목'] == p]
                    st.line_chart(df_p, x='날짜', y='오차(Diff)')
                    
                    avg_diff = df_p['오차(Diff)'].mean()
                    st.caption(f"평균 오차: {avg_diff:.3f}")