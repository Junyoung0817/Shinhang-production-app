import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy

st.set_page_config(page_title="신항공장 통합 모니터링", layout="wide")

# ---------------------------------------------------------
# 1. 초기 설정 (단위: MT)
# ---------------------------------------------------------

# 탱크 스펙 (사용자 실제 운용 중량 반영)
TANK_SPECS = {
    'TK-310':   {'max': 750,  'type': 'Buffer'},
    'TK-710':   {'max': 760,  'type': 'Prod'},
    'TK-720':   {'max': 760,  'type': 'Prod'},
    'TK-6101':  {'max': 5700, 'type': 'Shore'},
    'UTK-308':  {'max': 5400, 'type': 'Shore'},
    'UTK-1106': {'max': 6650, 'type': 'Shore'}
}

# 기본 데이터 구조
DEFAULT_DATA = {
    'qty': 0.0, 'av': 0.0, 'water': 0, 'metal': 0, 'p': 0, 'org_cl': 0, 'inorg_cl': 0
}

# 날짜별 DB 로드 및 생성
def get_daily_data(date_str):
    if 'daily_db' not in st.session_state:
        # 최초 실행 시 테스트 데이터
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        st.session_state.daily_db = {
            yesterday: {
                'TK-310':   {'qty': 300, 'av': 0.5, 'water': 800, 'metal': 5, 'p':10, 'org_cl': 15, 'inorg_cl': 5},
                'TK-710':   {'qty': 600, 'av': 0.3, 'water': 50,  'metal': 1, 'p':2,  'org_cl': 5,  'inorg_cl': 1},
                'TK-720':   {'qty': 50,  'av': 0.4, 'water': 60,  'metal': 2, 'p':3,  'org_cl': 6,  'inorg_cl': 2},
                'TK-6101':  {'qty': 2000,'av': 0.35,'water': 55,  'metal': 1, 'p':2,  'org_cl': 5,  'inorg_cl': 1},
                'UTK-308':  {'qty': 0,   'av': 0,   'water': 0,   'metal': 0, 'p':0,  'org_cl': 0,  'inorg_cl': 0},
                'UTK-1106': {'qty': 0,   'av': 0,   'water': 0,   'metal': 0, 'p':0,  'org_cl': 0,  'inorg_cl': 0},
            }
        }

    if date_str in st.session_state.daily_db:
        return st.session_state.daily_db[date_str]
    
    # 데이터 이월 로직
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    prev_date = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if prev_date in st.session_state.daily_db:
        new_data = copy.deepcopy(st.session_state.daily_db[prev_date])
    else:
        new_data = {k: DEFAULT_DATA.copy() for k in TANK_SPECS.keys()}
        
    st.session_state.daily_db[date_str] = new_data
    return new_data

# 블렌딩 계산 함수
def calc_blending(curr_qty, curr_val, in_qty, in_val):
    total = curr_qty + in_qty
    if total == 0: return 0.0
    return ((curr_qty * curr_val) + (in_qty * in_val)) / total

# ---------------------------------------------------------
# 2. 메인 UI 구성
# ---------------------------------------------------------
st.sidebar.title("🏭 생산/출하 시스템")
selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
date_key = selected_date.strftime("%Y-%m-%d")
current_data = get_daily_data(date_key)

# 메뉴 구성
menu = st.sidebar.radio("MENUS", 
    ["🔍 전체 탱크 모니터링 (View Only)", 
     "① 1차 공정 입력 (R-1140)", 
     "② 2차 정제 입력 (EV-6000)", 
     "③ 3차 이송 입력 (Shore)",
     "④ 수출 선적 입력 (Ship)"]
)

# ---------------------------------------------------------
# [TAB 1] 모니터링 전용 페이지 (업그레이드 됨)
# ---------------------------------------------------------
if menu == "🔍 전체 탱크 모니터링 (View Only)":
    st.title(f"🔍 {date_key} 공장 현황판")
    
    # 1. 상단 요약 지표 (Total Summary)
    total_qty = sum(d['qty'] for d in current_data.values())
    prod_qty = current_data['TK-710']['qty'] + current_data['TK-720']['qty']
    shore_qty = current_data['TK-6101']['qty'] + current_data['UTK-308']['qty'] + current_data['UTK-1106']['qty']
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 재고량", f"{total_qty:,.0f} MT")
    m2.metric("제품 (Prod)", f"{prod_qty:,.0f} MT")
    m3.metric("출하 대기 (Shore)", f"{shore_qty:,.0f} MT")
    m4.metric("가동률(Buffer)", f"{(current_data['TK-310']['qty']/750)*100:.1f}%")
    
    st.markdown("---")

    # 탱크 카드 그리는 함수
    def draw_tank_card(name, data, spec):
        fill_pct = (data['qty'] / spec['max']) * 100
        total_cl = data['org_cl'] + data['inorg_cl']
        
        # 카드 디자인 (테두리 상자)
        with st.container(border=True):
            # 헤더: 이름과 타입
            c_head1, c_head2 = st.columns([2, 1])
            c_head1.markdown(f"### 🛢 {name}")
            c_head2.caption(f"{spec['type']}")
            
            # 레벨 바 (Level Bar)
            st.progress(min(fill_pct/100, 1.0))
            
            # 핵심 데이터 (큰 글씨)
            k1, k2, k3 = st.columns(3)
            k1.metric("재고 (MT)", f"{data['qty']:.0f}", f"{fill_pct:.1f}%")
            k2.metric("AV", f"{data['av']:.2f}")
            k3.metric("Total Cl", f"{total_cl:.1f}")
            
            # 상세 품질 (클릭하면 펼쳐짐)
            with st.expander("상세 품질 보기"):
                d1, d2 = st.columns(2)
                d1.write(f"💧 수분: {data['water']:.0f}")
                d1.write(f"🧪 Org Cl: {data['org_cl']:.1f}")
                d1.write(f"🧪 InOrg Cl: {data['inorg_cl']:.1f}")
                d2.write(f"🔩 Metal: {data['metal']:.1f}")
                d2.write(f"⚡ P (인): {data['p']:.1f}")
                d2.write(f"📏 Capa: {spec['max']:,} MT")

    # 2. 탱크 배치 (Layout)
    
    st.subheader("1️⃣ Buffer Tank (중간 저장)")
    draw_tank_card('TK-310', current_data['TK-310'], TANK_SPECS['TK-310'])
    
    st.write("") # 여백
    st.subheader("2️⃣ Product Tanks (완제품)")
    c1, c2 = st.columns(2)
    with c1: draw_tank_card('TK-710', current_data['TK-710'], TANK_SPECS['TK-710'])
    with c2: draw_tank_card('TK-720', current_data['TK-720'], TANK_SPECS['TK-720'])
    
    st.write("") # 여백
    st.subheader("3️⃣ Shore Tanks (수출 출하)")
    s1, s2, s3 = st.columns(3)
    with s1: draw_tank_card('TK-6101', current_data['TK-6101'], TANK_SPECS['TK-6101'])
    with s2: draw_tank_card('UTK-308', current_data['UTK-308'], TANK_SPECS['UTK-308'])
    with s3: draw_tank_card('UTK-1106', current_data['UTK-1106'], TANK_SPECS['UTK-1106'])

# ---------------------------------------------------------
# [TAB 2] 1차 공정 (입력 전용)
# ---------------------------------------------------------
elif menu == "① 1차 공정 입력 (R-1140)":
    st.title("🔥 1차 생산 입력")
    c1, c2 = st.columns(2)
    with c1:
        qty = st.number_input("생산량 (MT)", 0.0, 2000.0, step=10.0)
    with c2:
        st.write("🔬 **R-1140 분석값**")
        av = st.number_input("AV", 0.0, 10.0, 0.5)
        ocl = st.number_input("Org Cl", 0, 500, 15)
        
    if st.button("저장"):
        tgt = current_data['TK-310']
        tgt['av'] = calc_blending(tgt['qty'], tgt['av'], qty, av)
        tgt['org_cl'] = calc_blending(tgt['qty'], tgt['org_cl'], qty, ocl)
        tgt['qty'] += qty
        st.success(f"TK-310 입고 완료! (+{qty} MT)")

# ---------------------------------------------------------
# [TAB 3] 2차 정제 (입력 전용)
# ---------------------------------------------------------
elif menu == "② 2차 정제 입력 (EV-6000)":
    st.title("✨ 2차 정제 입력")
    c1, c2, c3 = st.columns([1,0.2,1])
    with c1:
        st.info(f"OUT: TK-310 ({current_data['TK-310']['qty']:.0f} MT)")
        f_qty = st.number_input("투입량 (MT)", 0.0, step=10.0)
    with c3:
        target = st.selectbox("IN: 제품 탱크", ["TK-710", "TK-720"])
        st.success(f"IN: {target} ({current_data[target]['qty']:.0f} MT)")
        p_qty = st.number_input("생산량 (MT)", 0.0, step=10.0)
    with c2: st.markdown("<br>➡️", unsafe_allow_html=True)

    if f_qty > 0: st.caption(f"수율: {(p_qty/f_qty)*100:.1f}%")
        
    st.write("🔬 **EV-6000 후단 품질**")
    qc1, qc2, qc3 = st.columns(3)
    e_av = qc1.number_input("AV", 0.0, 5.0, 0.3)
    e_wa = qc1.number_input("수분", 0, 1000, 50)
    e_met = qc2.number_input("Metal", 0, 100, 1)
    e_p = qc2.number_input("P", 0, 100, 2)
    e_ocl = qc3.number_input("Org Cl", 0, 100, 5)
    e_icl = qc3.number_input("InOrg Cl", 0, 100, 1)
    
    if st.button("저장"):
        src, tgt = current_data['TK-310'], current_data[target]
        if src['qty'] < f_qty: st.error("재고 부족")
        else:
            tgt['av'] = calc_blending(tgt['qty'], tgt['av'], p_qty, e_av)
            tgt['water'] = calc_blending(tgt['qty'], tgt['water'], p_qty, e_wa)
            tgt['metal'] = calc_blending(tgt['qty'], tgt['metal'], p_qty, e_met)
            tgt['p'] = calc_blending(tgt['qty'], tgt['p'], p_qty, e_p)
            tgt['org_cl'] = calc_blending(tgt['qty'], tgt['org_cl'], p_qty, e_ocl)
            tgt['inorg_cl'] = calc_blending(tgt['qty'], tgt['inorg_cl'], p_qty, e_icl)
            src['qty'] -= f_qty; tgt['qty'] += p_qty
            st.success("정제 생산 완료!")

# ---------------------------------------------------------
# [TAB 4] 3차 이송 (입력 전용)
# ---------------------------------------------------------
elif menu == "③ 3차 이송 입력 (Shore)":
    st.title("🚚 이송 입력")
    c1, c2, c3 = st.columns([1,0.5,1])
    with c1:
        src_n = st.selectbox("From", ["TK-710", "TK-720"])
        src = current_data[src_n]
        st.write(f"재고: {src['qty']:.0f}")
    with c3:
        tgt_n = st.selectbox("To", ["TK-6101", "UTK-308", "UTK-1106"])
        tgt = current_data[tgt_n]
        st.write(f"재고: {tgt['qty']:.0f}")
    with c2: m_qty = st.number_input("이송량 (MT)", 0.0, step=10.0)
        
    if st.button("이송 확정"):
        if src['qty'] < m_qty: st.error("재고 부족")
        else:
            for k in DEFAULT_DATA.keys():
                if k != 'qty': tgt[k] = calc_blending(tgt['qty'], tgt[k], m_qty, src[k])
            src['qty'] -= m_qty; tgt['qty'] += m_qty
            st.success("이송 완료")

# ---------------------------------------------------------
# [TAB 5] 수출 선적 (입력 전용)
# ---------------------------------------------------------
elif menu == "④ 수출 선적 입력 (Ship)":
    st.title("🚢 선적 입력")
    col1, col2 = st.columns(2)
    with col1:
        ship_tank_name = st.selectbox("출하 탱크", ["TK-6101", "UTK-308", "UTK-1106"])
        ship_tank = current_data[ship_tank_name]
        st.metric("현재 재고", f"{ship_tank['qty']:.0f} MT")
    with col2:
        ship_qty = st.number_input("선적량 (MT)", 0.0, float(ship_tank['qty']), step=10.0)
        st.metric("예상 잔량", f"{(ship_tank['qty'] - ship_qty):.0f} MT")

    if st.button("출하 실행"):
        ship_tank['qty'] -= ship_qty
        if ship_tank['qty'] <= 0.01:
            ship_tank['qty'] = 0.0
            for k in DEFAULT_DATA: 
                if k!='qty': ship_tank[k] = 0.0
            st.success("전량 출하 완료 (Empty)")
        else:
            st.success("선적 완료")