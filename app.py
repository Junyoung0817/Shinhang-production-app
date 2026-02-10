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

def get_data_for_date(date_key, specs, defaults):
    # 1. 해당 날짜 데이터가 있으면 반환
    if date_key in st.session_state.daily_db:
        return st.session_state.daily_db[date_key]
    
    # 2. 없으면 과거 데이터 찾기 (Look-back)
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
            "날짜": date_key, "탱크": tank_name, "항목": param,
            "예상값": round(predicted, 3), "실측값": round(actual, 3), "오차": round(diff, 3)
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
    return ((curr_qty * curr_val) + (in_qty * in_val)) / total

# [핵심] 연쇄 수정 함수 (과거 수정 시 미래 데이터 자동 보정)
def propagate_changes(start_date_str, tank_name, changes):
    all_dates = sorted(list(st.session_state.daily_db.keys()))
    count = 0
    for d_key in all_dates:
        if d_key > start_date_str: # 수정일 이후의 날짜들
            if tank_name in st.session_state.daily_db[d_key]:
                target = st.session_state.daily_db[d_key][tank_name]
                
                # 차이만큼 더해주기 (Shift)
                for k, v in changes.items():
                    if abs(v) > 0.0001:
                        target[k] += v
                        if target[k] < 0: target[k] = 0.0 # 음수 방지
                count += 1
    
    if count > 0:
        st.toast(f"🔄 {start_date_str} 이후 {count}일간의 데이터도 함께 수정되었습니다.")

# ==========================================
# 메인 실행 로직
# ==========================================

SPECS, DEFAULTS = load_data()

st.sidebar.title("🏭 생산관리 System")
st.sidebar.caption("Ver 16.0 (Past Edit Mode)")

# [메인 날짜 선택] - 조회용
selected_date = st.sidebar.date_input("기준 날짜 (조회/입력)", datetime.now())
DATE_KEY = selected_date.strftime("%Y-%m-%d")

# 데이터 로드
TODAY_DATA = get_data_for_date(DATE_KEY, SPECS, DEFAULTS)

# 버튼들
st.sidebar.markdown("---")
if st.sidebar.button(f"🗑️ [{DATE_KEY}] 초기화"):
    reset_today_data(DATE_KEY, SPECS, DEFAULTS)

st.sidebar.markdown("---")
if st.session_state.history_log:
    if st.sidebar.button("↩️ 실행 취소 (Undo)"):
        undo_last_action(TODAY_DATA)

# 메뉴 구조 변경
menu = st.sidebar.radio("메뉴 이동", 
    ["1. 전체 모니터링", 
     "2. 1차 공정 (R-1140)", 
     "3. 2차 정제 (EV-6000)", 
     "4. 이송 및 선적", 
     "5. 과거 데이터 수정 (Time Machine)", # 이름 변경
     "6. QC 오차 분석"]
)

st.header(f"📅 {DATE_KEY} : {menu}")

# ---------------------------------------------------------
# 1. 모니터링
# ---------------------------------------------------------
if menu == "1. 전체 모니터링":
    st.subheader("📊 탱크별 재고 및 품질 현황")
    rows = []
    for t in SPECS:
        d = TODAY_DATA[t]
        rows.append({
            "탱크": t, "구분": SPECS[t]['type'],
            "재고": f"{d['qty']:.1f}", "AV": f"{d['av']:.3f}",
            "Org Cl": f"{d['org_cl']:.1f}", "InOrg Cl": f"{d['inorg_cl']:.1f}",
            "P": f"{d['p']:.1f}", "수분": f"{d['water']:.0f}", "Metal": f"{d['metal']:.1f}"
        })
    st.table(pd.DataFrame(rows))

# ---------------------------------------------------------
# 2~4. 입력 메뉴들
# ---------------------------------------------------------
elif menu == "2. 1차 공정 (R-1140)":
    st.info("원료 → R-1140 → TK-310")
    st.write(f"현재 TK-310: {TODAY_DATA['TK-310']['qty']:.1f} MT")
    with st.form("f1"):
        c1, c2 = st.columns(2)
        with c1: qty = st.number_input("생산량", 0.0, step=10.0)
        with c2: 
            av = st.number_input("AV", 0.0, step=0.1)
            cl = st.number_input("Org Cl", 0.0, step=1.0)
        if st.form_submit_button("저장"):
            log_action(DATE_KEY, "입고", f"1차 +{qty}", ['TK-310'], TODAY_DATA)
            t = TODAY_DATA['TK-310']
            t['av'] = calc_blend(t['qty'], t['av'], qty, av)
            t['org_cl'] = calc_blend(t['qty'], t['org_cl'], qty, cl)
            t['qty'] += qty
            st.success("저장 완료"); st.rerun()

elif menu == "3. 2차 정제 (EV-6000)":
    st.info("TK-310 → EV-6000 → 제품탱크")
    with st.form("f2"):
        c1, c2, c3 = st.columns(3)
        with c1: f_q = st.number_input("TK-310 투입", 0.0)
        with c2: dest = st.selectbox("To", ["TK-710", "TK-720"])
        with c3: p_q = st.number_input("제품 생산", 0.0)
        st.markdown("---")
        q1, q2 = st.columns(2)
        with q1: 
            qa = st.number_input("AV", 0.0)
            qw = st.number_input("수분", 0)
            qm = st.number_input("Metal", 0.0)
        with q2: 
            qo = st.number_input("Org Cl", 0.0)
            qi = st.number_input("InOrg Cl", 0.0)
            qp = st.number_input("P", 0.0)
        if st.form_submit_button("저장"):
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
                st.success("저장 완료"); st.rerun()

elif menu == "4. 이송 및 선적":
    t1, t2 = st.tabs(["이송", "선적"])
    with t1:
        with st.form("ft"):
            c1, c2, c3 = st.columns(3)
            with c1: f = st.selectbox("From", ["TK-710", "TK-720"])
            with c2: t = st.selectbox("To", ["TK-6101", "UTK-308", "UTK-1106"])
            with c3: q = st.number_input("이송량", 0.0)
            if st.form_submit_button("이송"):
                log_action(DATE_KEY, "이송", f"{f}->{t} {q}", [f, t], TODAY_DATA)
                src = TODAY_DATA[f]; tgt = TODAY_DATA[t]
                if src['qty'] < q: st.error("부족")
                else:
                    for k in DEFAULTS: 
                        if k!='qty': tgt[k] = calc_blend(tgt['qty'], tgt[k], q, src[k])
                    src['qty'] -= q; tgt['qty'] += q
                    st.success("완료"); st.rerun()
    with t2:
        with st.form("fs"):
            c1, c2 = st.columns(2)
            with c1: s = st.selectbox("출하 탱크", ["TK-6101", "UTK-308", "UTK-1106"])
            with c2: q = st.number_input("선적량", 0.0)
            if st.form_submit_button("선적"):
                log_action(DATE_KEY, "선적", f"{s} -{q}", [s], TODAY_DATA)
                tk = TODAY_DATA[s]
                tk['qty'] -= q
                if tk['qty'] < 0: tk['qty'] = 0
                st.success("완료"); st.rerun()

# ---------------------------------------------------------
# [핵심] 5. 과거 데이터 수정 (Time Machine)
# ---------------------------------------------------------
elif menu == "5. 과거 데이터 수정 (Time Machine)":
    st.title("🕰️ 과거 기록 수정 (타임머신)")
    st.markdown("""
    **사용법:**
    1. 수정하고 싶은 **과거 날짜**를 아래에서 선택하세요.
    2. 탱크의 값을 수정하고 저장하면, **그 차이만큼 미래 날짜(오늘 포함)까지 자동으로 반영**됩니다.
    """)
    
    # 1. 수정할 과거 날짜 선택 (메인 날짜와 별도)
    edit_date = st.date_input("📅 수정할 날짜 선택", datetime.now() - timedelta(days=1))
    edit_key = edit_date.strftime("%Y-%m-%d")
    
    # 해당 날짜 데이터 불러오기
    if edit_key not in st.session_state.daily_db:
        st.warning(f"{edit_key} 데이터가 없습니다. (먼저 해당 날짜를 조회하여 데이터를 생성해주세요)")
    else:
        edit_data = st.session_state.daily_db[edit_key]
        
        # 탱크 선택
        target_tank = st.selectbox("수정할 탱크", list(SPECS.keys()))
        curr = edit_data[target_tank]
        
        st.markdown(f"### 📝 {edit_key} / {target_tank} 수정")
        
        with st.form("past_edit_form"):
            c1, c2 = st.columns(2)
            with c1:
                n_qty = st.number_input("재고 (MT)", value=float(curr['qty']))
                n_av = st.number_input("AV", value=float(curr['av']))
                n_wa = st.number_input("수분", value=int(curr['water']))
            with c2:
                n_cl = st.number_input("Org Cl", value=float(curr['org_cl']))
                n_icl = st.number_input("InOrg Cl", value=float(curr['inorg_cl']))
                n_p = st.number_input("P (인)", value=float(curr['p']))
            
            # 미래 반영 옵션 (기본 체크)
            auto_sync = st.checkbox("✅ 수정된 차이를 미래 날짜(내일~오늘)에도 반영합니다.", value=True)
            
            if st.form_submit_button("수정 내용 저장"):
                # 변경량(Delta) 계산
                deltas = {
                    'qty': n_qty - curr['qty'],
                    'av': n_av - curr['av'],
                    'water': n_wa - curr['water'],
                    'org_cl': n_cl - curr['org_cl'],
                    'inorg_cl': n_icl - curr['inorg_cl'],
                    'p': n_p - curr['p']
                }
                
                # 로그 기록
                log_action(edit_key, "과거수정", f"{edit_key} {target_tank} 수정", [target_tank], edit_data)
                
                # 1. 과거 날짜 데이터 업데이트
                curr['qty'] = n_qty; curr['av'] = n_av; curr['water'] = n_wa
                curr['org_cl'] = n_cl; curr['inorg_cl'] = n_icl; curr['p'] = n_p
                
                # 2. 미래 데이터 연쇄 수정
                if auto_sync:
                    propagate_changes(edit_key, target_tank, deltas)
                    
                st.success(f"{edit_key} 데이터 수정 완료! (미래 데이터 동기화 됨)")
                time.sleep(1.0)
                st.rerun()

# ---------------------------------------------------------
# 6. QC 분석
# ---------------------------------------------------------
elif menu == "6. QC 오차 분석":
    st.title("📈 오차 분석")
    if not st.session_state.qc_log:
        st.info("데이터 없음")
    else:
        df = pd.DataFrame(st.session_state.qc_log)
        st.dataframe(df, use_container_width=True)