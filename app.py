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

# [NEW] 미래 데이터 연쇄 수정 함수 (Ripple Effect)
def propagate_stock_change(start_date_str, tank_name, qty_diff):
    # 등록된 모든 날짜를 가져와서 정렬
    all_dates = sorted(list(st.session_state.daily_db.keys()))
    
    count = 0
    for d_key in all_dates:
        # 수정 기준일보다 미래인 날짜만 찾음
        if d_key > start_date_str:
            if tank_name in st.session_state.daily_db[d_key]:
                # 재고 차이만큼 더하거나 뺌
                st.session_state.daily_db[d_key][tank_name]['qty'] += qty_diff
                # 음수 방지
                if st.session_state.daily_db[d_key][tank_name]['qty'] < 0:
                    st.session_state.daily_db[d_key][tank_name]['qty'] = 0.0
                count += 1
    
    if count > 0:
        st.toast(f"🔄 이후 {count}일간의 데이터에도 재고 변경({qty_diff:+.1f}MT)이 반영되었습니다.")

# ==========================================
# 메인 실행 로직
# ==========================================

SPECS, DEFAULTS = load_data()

st.sidebar.title("🏭 생산관리 System")
st.sidebar.caption("Ver 14.0 (Cascade Update)")

# 날짜 선택
selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
DATE_KEY = selected_date.strftime("%Y-%m-%d")

# 데이터 로드
TODAY_DATA = get_today_data(DATE_KEY, SPECS, DEFAULTS)

# [수정됨] 금일 데이터 삭제 버튼
st.sidebar.markdown("---")
if st.sidebar.button(f"🗑️ [{DATE_KEY}] 데이터 초기화"):
    reset_today_data(DATE_KEY, SPECS, DEFAULTS)
st.sidebar.caption(f"⚠️ {DATE_KEY} 데이터를 전일 마감 상태로 되돌립니다.")

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