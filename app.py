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
    
    # [변경] 모든 값을 소수점(float)으로 초기화
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
            data = st.session_state.daily_db[past]
            if sum(t['qty'] for t in data.values()) > 0:
                return copy.deepcopy(data)
    return None

def reset_today_data(date_key, specs, defaults):
    past = find_past_data(date_key)
    if past:
        st.session_state.daily_db[date_key] = past
        st.toast(f"✅ {date_key} 데이터 복구 완료")
    else:
        st.session_state.daily_db[date_key] = {t: defaults.copy() for t in specs}
        st.toast(f"✅ {date_key} 초기화 (0)")
    save_db()
    time.sleep(1.0)
    st.rerun()

def generate_dummy_data(specs, defaults):
    base = datetime.now()
    for i in range(7, -1, -1):
        d_key = (base - timedelta(days=i)).strftime("%Y-%m-%d")
        new_data = {}
        for t in specs:
            data = defaults.copy()
            data['qty'] = round(random.uniform(100, 500), 1)
            data['av'] = round(random.uniform(0.1, 1.0), 3)
            data['org_cl'] = round(random.uniform(5, 20), 1)
            data['water'] = round(random.uniform(10, 100), 1)
            new_data[t] = data
        st.session_state.daily_db[d_key] = new_data
    save_db()
    st.toast("✅ 테스트 데이터 생성 완료")
    time.sleep(1.0)
    st.rerun()

def factory_reset():
    st.session_state.daily_db = {}
    st.session_state.history_log = []
    st.session_state.qc_log = []
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
    st.toast("🧹 공장 초기화 완료")
    time.sleep(1.0)
    st.rerun()

def log_action(date_key, action_type, desc, tanks_involved, current_db):
    snapshot = {}
    for t in tanks_involved:
        snapshot[t] = copy.deepcopy(current_db[t])
    st.session_state.history_log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "date": date_key, "type": action_type, "desc": desc, "snapshot": snapshot
    })
    save_logs()

def log_qc_diff(date_key, tank_name, param, predicted, actual):
    diff = actual - predicted
    if abs(diff) > 0.001:
        st.session_state.qc_log.append({
            "날짜": date_key, "탱크": tank_name, "항목": param,
            "예상값": round(predicted, 3), "실측값": round(actual, 3), "오차": round(diff, 3)
        })
        save_logs()

def undo_last_action(current_db):
    if not st.session_state.history_log:
        st.sidebar.error("취소할 작업 없음")
        return
    last = st.session_state.history_log.pop()
    if not last['snapshot']:
        st.sidebar.error("초기화는 취소 불가")
        return
    for t, data in last['snapshot'].items():
        current_db[t] = data
    save_db()
    save_logs()
    st.sidebar.success(f"취소 완료: {last['desc']}")
    time.sleep(0.5)
    st.rerun()

def calc_blend(curr_qty, curr_val, in_qty, in_val):
    total = curr_qty + in_qty
    if total == 0: return 0.0
    return ((curr_qty * curr_val) + (in_qty * in_val)) / total

def propagate_changes(start_date_str, tank_name, changes):
    all_dates = sorted(list(st.session_state.daily_db.keys()))
    count = 0
    for d_key in all_dates:
        if d_key > start_date_str:
            if tank_name in st.session_state.daily_db[d_key]:
                target = st.session_state.daily_db[d_key][tank_name]
                for k, v in changes.items():
                    if abs(v) > 0.0001:
                        target[k] += v
                        if target[k] < 0: target[k] = 0.0
                count += 1
    if count > 0:
        save_db()
        st.toast(f"🔄 이후 {count}일간 데이터 자동 보정됨")

# ==========================================
# 메인 실행 로직
# ==========================================

SPECS, DEFAULTS = init_system()

st.sidebar.title("🏭 생산관리 System")
st.sidebar.caption("Ver 20.1 (Syntax Fix)")

with st.sidebar.expander("🛠️ 시스템 관리"):
    if st.button("🎲 더미 데이터 생성"):
        generate_dummy_data(SPECS, DEFAULTS)
    if st.button("🔥 공장 초기화"):
        factory_reset()

st.sidebar.markdown("---")

selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
DATE_KEY = selected_date.strftime("%Y-%m-%d")
TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)

if st.session_state.history_log:
    if st.sidebar.button("↩️ 실행 취소 (Undo)"):
        undo_last_action(TODAY_DATA)

menu = st.sidebar.radio("메뉴 이동", 
    ["1. 전체 모니터링", 
     "2. 1차 공정 (R-1140)", 
     "3. 2차 정제 (EV-6000)", 
     "4. 이송 및 선적", 
     "5. 실제 분석 데이터 입력",
     "6. QC 오차 분석"]
)

st.header(f"📅 {DATE_KEY} : {menu}")

# ---------------------------------------------------------
# 1. 모니터링
# ---------------------------------------------------------
if menu == "1. 전체 모니터링":
    st.subheader("📊 탱크별 재고 및 품질 현황")
    if sum(TODAY_DATA['TK-310']['qty'] for t in SPECS) == 0:
        st.warning("⚠️ 현재 데이터가 모두 0입니다.")
        if st.button("🔄 전일 데이터 강제 불러오기"):
             reset_today_data(DATE_KEY, SPECS, DEFAULTS)
             
    rows = []
    for t in SPECS:
        d = TODAY_DATA[t]
        rows.append({
            "탱크": t, "구분": SPECS[t]['type'],
            "재고": f"{d['qty']:.1f}", "AV": f"{d['av']:.3f}",
            "Org Cl": f"{d['org_cl']:.1f}", "InOrg Cl": f"{d['inorg_cl']:.1f}",
            "P": f"{d['p']:.1f}", "수분": f"{d['water']:.1f}",
            "Metal": f"{d['metal']:.1f}"
        })
    st.table(pd.DataFrame(rows))

# ---------------------------------------------------------
# 2. 1차 공정
# ---------------------------------------------------------
elif menu == "2. 1차 공정 (R-1140)":
    st.info("원료 → R-1140 → TK-310")
    st.metric("현재 TK-310", f"{TODAY_DATA['TK-310']['qty']:.1f} MT")
    with st.form("f1"):
        c1, c2 = st.columns(2)
        with c1: qty = st.number_input("생산량", 0.0, step=10.0)
        with c2: 
            av = st.number_input("AV", 0.0, step=0.1, format="%.1f")
            cl = st.number_input("Org Cl", 0.0, step=0.1, format="%.1f")
        if st.form_submit_button("저장"):
            log_action(DATE_KEY, "입고", f"1차 +{qty}", ['TK-310'], TODAY_DATA)
            t = TODAY_DATA['TK-310']
            t['av'] = calc_blend(t['qty'], t['av'], qty, av)
            t['org_cl'] = calc_blend(t['qty'], t['org_cl'], qty, cl)
            t['qty'] += qty
            save_db()
            st.success("저장 완료"); st.rerun()

# ---------------------------------------------------------
# 3. 2차 정제
# ---------------------------------------------------------
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
            qa = st.number_input("AV", 0.0, step=0.1, format="%.1f")
            qw = st.number_input("수분", 0.0, step=0.1, format="%.1f")
            qm = st.number_input("Metal", 0.0, step=0.1, format="%.1f")
        with q2: 
            qo = st.number_input("Org Cl", 0.0, step=0.1, format="%.1f")
            qi = st.number_input("InOrg Cl", 0.0, step=0.1, format="%.1f")
            qp = st.number_input("P", 0.0, step=0.1, format="%.1f")
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
                save_db()
                st.success("저장 완료"); st.rerun()

# ---------------------------------------------------------
# 4. 이송 및 선적
# ---------------------------------------------------------
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
                    save_db()
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
                save_db()
                st.success("완료"); st.rerun()

# ---------------------------------------------------------
# 5. 실제 분석 데이터 입력
# ---------------------------------------------------------
elif menu == "5. 실제 분석 데이터 입력":
    st.title("🧪 Lab 분석 결과 반영")
    edit_date = st.date_input("📅 분석 날짜", datetime.now() - timedelta(days=1))
    edit_key = edit_date.strftime("%Y-%m-%d")
    
    if edit_key not in st.session_state.daily_db:
         new_db = get_today_data(edit_key, SPECS, DEFAULTS)
    
    edit_data = st.session_state.daily_db[edit_key]
    target_tank = st.selectbox("분석 탱크", list(SPECS.keys()))
    curr = edit_data[target_tank]
    
    st.write(f"**{edit_key} 기준** 현재값: 재고 {curr['qty']:.1f} / AV {curr['av']:.3f}")

    with st.form("correction_form"):
        c1, c2 = st.columns(2)
        with c1:
            # [핵심] step=0.1, format="%.1f" 적용 (수분 포함)
            n_qty = st.number_input("실측 재고", value=float(curr['qty']))
            n_av = st.number_input("실측 AV", value=float(curr['av']), step=0.1, format="%.1f")
            n_wa = st.number_input("실측 수분", value=float(curr['water']), step=0.1, format="%.1f")
        with c2:
            n_cl = st.number_input("실측 Org Cl", value=float(curr['org_cl']), step=0.1, format="%.1f")
            n_icl = st.number_input("실측 InOrg Cl", value=float(curr['inorg_cl']), step=0.1, format="%.1f")
            n_p = st.number_input("실측 P", value=float(curr['p']), step=0.1, format="%.1f")
        
        auto_sync = st.checkbox("✅ 차이를 미래 날짜에도 반영", value=True)
        
        if st.form_submit_button("반영"):
            deltas = {
                'qty': n_qty - curr['qty'], 'av': n_av - curr['av'], 'water': n_wa - curr['water'],
                'org_cl': n_cl - curr['org_cl'], 'inorg_cl': n_icl - curr['inorg_cl'], 'p': n_p - curr['p']
            }
            log_action(edit_key, "분석반영", f"{target_tank} 실측보정", [target_tank], edit_data)
            
            check_list = [
                ("재고", curr['qty'], n_qty), ("AV", curr['av'], n_av), ("수분", curr['water'], n_wa),
                ("Org Cl", curr['org_cl'], n_cl), ("InOrg Cl", curr['inorg_cl'], n_icl), ("P", curr['p'], n_p)
            ]
            for label, pred_val, act_val in check_list:
                log_qc_diff(edit_key, target_tank, label, pred_val, act_val)

            curr['qty'] = n_qty; curr['av'] = n_av; curr['water'] = n_wa
            curr['org_cl'] = n_cl; curr['inorg_cl'] = n_icl; curr['p'] = n_p
            
            if auto_sync: propagate_changes(edit_key, target_tank, deltas)
            
            save_db()
            st.success("✅ 분석 데이터 반영 및 QC 로그 저장 완료")
            st.rerun()

# ---------------------------------------------------------
# 6. QC 오차 분석
# ---------------------------------------------------------
elif menu == "6. QC 오차 분석":
    st.title("📈 예측 vs 실측 오차")
    if not st.session_state.qc_log:
        st.info("데이터 없음")
    else:
        df = pd.DataFrame(st.session_state.qc_log)
        st.dataframe(df, use_container_width=True)