import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import copy

st.set_page_config(page_title="신항공장 통합 관리 System", layout="wide")

# ---------------------------------------------------------
# 1. 초기 설정 및 데이터 정의
# ---------------------------------------------------------

# 탱크 스펙
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

# [핵심] 오차 기록 저장소 초기화
if 'correction_log' not in st.session_state:
    st.session_state.correction_log = []

# 날짜별 DB 로드
def get_daily_data(date_str):
    if 'daily_db' not in st.session_state:
        # 테스트용 초기 데이터
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
# 2. 메인 UI 및 메뉴
# ---------------------------------------------------------
st.sidebar.title("🏭 생산/출하/QC 시스템")
selected_date = st.sidebar.date_input("기준 날짜", datetime.now())
date_key = selected_date.strftime("%Y-%m-%d")
current_data = get_daily_data(date_key)

menu = st.sidebar.radio("MENUS", 
    ["🔍 전체 탱크 모니터링 (View Only)", 
     "① 1차 공정 입력 (R-1140)", 
     "② 2차 정제 입력 (EV-6000)", 
     "③ 3차 이송 입력 (Shore)",
     "④ 수출 선적 입력 (Ship)",
     "⑤ 재고/품질 보정 (Correction)",
     "⑥ 예측 정확도 분석 (Analysis)"] # 메뉴 추가
)

# ---------------------------------------------------------
# [TAB 1] 모니터링
# ---------------------------------------------------------
if menu == "🔍 전체 탱크 모니터링 (View Only)":
    st.title(f"🔍 {date_key} 공장 현황판")
    
    total_qty = sum(d['qty'] for d in current_data.values())
    prod_qty = current_data['TK-710']['qty'] + current_data['TK-720']['qty']
    shore_qty = current_data['TK-6101']['qty'] + current_data['UTK-308']['qty'] + current_data['UTK-1106']['qty']
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 재고량", f"{total_qty:,.0f} MT")
    m2.metric("제품 (Prod)", f"{prod_qty:,.0f} MT")
    m3.metric("출하 대기 (Shore)", f"{shore_qty:,.0f} MT")
    m4.metric("Buffer 가동률", f"{(current_data['TK-310']['qty']/750)*100:.1f}%")
    st.markdown("---")

    def draw_tank_card(name, data, spec):
        fill_pct = (data['qty'] / spec['max']) * 100 if spec['max'] > 0 else 0
        total_cl = data['org_cl'] + data['inorg_cl']
        
        with st.container(border=True):
            c_head1, c_head2 = st.columns([2, 1])
            c_head1.markdown(f"### 🛢 {name}")
            c_head2.caption(f"{spec['type']}")
            st.progress(min(fill_pct/100, 1.0))
            
            k1, k2, k3 = st.columns(3)
            k1.metric("재고", f"{data['qty']:.0f}", f"{fill_pct:.1f}%")
            k2.metric("AV", f"{data['av']:.2f}")
            k3.metric("T-Cl", f"{total_cl:.1f}")
            
            with st.expander("상세 보기"):
                d1, d2 = st.columns(2)
                d1.write(f"수분: {data['water']:.0f}")
                d1.write(f"Org Cl: {data['org_cl']:.1f}")
                d1.write(f"InOrg Cl: {data['inorg_cl']:.1f}")
                d2.write(f"Metal: {data['metal']:.1f}")
                d2.write(f"P: {data['p']:.1f}")

    st.subheader("1️⃣ Buffer Tank")
    draw_tank_card('TK-310', current_data['TK-310'], TANK_SPECS['TK-310'])
    st.write("")
    st.subheader("2️⃣ Product Tanks")
    c1, c2 = st.columns(2)
    with c1: draw_tank_card('TK-710', current_data['TK-710'], TANK_SPECS['TK-710'])
    with c2: draw_tank_card('TK-720', current_data['TK-720'], TANK_SPECS['TK-720'])
    st.write("")
    st.subheader("3️⃣ Shore Tanks")
    s1, s2, s3 = st.columns(3)
    with s1: draw_tank_card('TK-6101', current_data['TK-6101'], TANK_SPECS['TK-6101'])
    with s2: draw_tank_card('UTK-308', current_data['UTK-308'], TANK_SPECS['UTK-308'])
    with s3: draw_tank_card('UTK-1106', current_data['UTK-1106'], TANK_SPECS['UTK-1106'])

# ---------------------------------------------------------
# [TAB 2~5] 입력 메뉴들
# ---------------------------------------------------------
elif menu == "① 1차 공정 입력 (R-1140)":
    st.title("🔥 1차 생산 입력")
    c1, c2 = st.columns(2)
    with c1: qty = st.number_input("생산량 (MT)", 0.0, 2000.0, step=10.0)
    with c2:
        av = st.number_input("AV", 0.0, 10.0, 0.5)
        ocl = st.number_input("Org Cl", 0, 500, 15)
    if st.button("저장"):
        tgt = current_data['TK-310']
        tgt['av'] = calc_blending(tgt['qty'], tgt['av'], qty, av)
        tgt['org_cl'] = calc_blending(tgt['qty'], tgt['org_cl'], qty, ocl)
        tgt['qty'] += qty
        st.success("저장 완료")

elif menu == "② 2차 정제 입력 (EV-6000)":
    st.title("✨ 2차 정제 입력")
    c1, c2, c3 = st.columns([1,0.2,1])
    with c1: f_qty = st.number_input("투입량 (MT)", 0.0, step=10.0)
    with c3:
        target = st.selectbox("IN: 제품 탱크", ["TK-710", "TK-720"])
        p_qty = st.number_input("생산량 (MT)", 0.0, step=10.0)
    with c2: st.markdown("<br>➡️", unsafe_allow_html=True)

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
            st.success("저장 완료")

elif menu == "③ 3차 이송 입력 (Shore)":
    st.title("🚚 이송 입력")
    c1, c2, c3 = st.columns([1,0.5,1])
    with c1:
        src_n = st.selectbox("From", ["TK-710", "TK-720"])
        src = current_data[src_n]
    with c3:
        tgt_n = st.selectbox("To", ["TK-6101", "UTK-308", "UTK-1106"])
        tgt = current_data[tgt_n]
    with c2: m_qty = st.number_input("이송량 (MT)", 0.0, step=10.0)
    if st.button("저장"):
        if src['qty'] < m_qty: st.error("재고 부족")
        else:
            for k in DEFAULT_DATA: 
                if k!='qty': tgt[k] = calc_blending(tgt['qty'], tgt[k], m_qty, src[k])
            src['qty'] -= m_qty; tgt['qty'] += m_qty
            st.success("저장 완료")

elif menu == "④ 수출 선적 입력 (Ship)":
    st.title("🚢 선적 입력")
    col1, col2 = st.columns(2)
    with col1:
        ship_tank_name = st.selectbox("출하 탱크", ["TK-6101", "UTK-308", "UTK-1106"])
        ship_tank = current_data[ship_tank_name]
    with col2: ship_qty = st.number_input("선적량 (MT)", 0.0, float(ship_tank['qty']), step=10.0)
    if st.button("출하 실행"):
        ship_tank['qty'] -= ship_qty
        if ship_tank['qty'] <= 0.01:
            ship_tank['qty'] = 0.0
            for k in DEFAULT_DATA: 
                if k!='qty': ship_tank[k] = 0.0
        st.success("출하 완료")

# ---------------------------------------------------------
# [TAB 5] 재고/품질 보정 (자동 로깅 기능 탑재)
# ---------------------------------------------------------
elif menu == "⑤ 재고/품질 보정 (Correction)":
    st.title("🛠️ 실측 보정 & 오차 기록")
    st.info("예측값(시스템 계산)을 Lab 실측값으로 수정하면, 그 차이를 자동으로 기록합니다.")
    
    target_tank_name = st.selectbox("보정할 탱크", list(TANK_SPECS.keys()))
    tank_data = current_data[target_tank_name]
    
    # 수정 폼
    with st.form("correction_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_qty = st.number_input("실측 재고 (MT)", 0.0, 10000.0, float(tank_data['qty']))
            new_av = st.number_input("실측 AV", 0.0, 10.0, float(tank_data['av']))
            new_water = st.number_input("실측 수분", 0, 5000, int(tank_data['water']))
        with col2:
            new_metal = st.number_input("실측 Metal", 0.0, 500.0, float(tank_data['metal']))
            new_p = st.number_input("실측 P", 0.0, 500.0, float(tank_data['p']))
        with col3:
            new_ocl = st.number_input("실측 Org Cl", 0.0, 500.0, float(tank_data['org_cl']))
            new_icl = st.number_input("실측 InOrg Cl", 0.0, 500.0, float(tank_data['inorg_cl']))
            
        submitted = st.form_submit_button("실측 데이터 반영 (Update)")
        
        if submitted:
            # 1. 오차 계산 및 로그 생성 (값이 다른 경우만 기록)
            changes = []
            
            # 비교 로직 (키, 라벨, 기존값, 신규값)
            compare_list = [
                ('qty', '재고', tank_data['qty'], new_qty),
                ('av', 'AV', tank_data['av'], new_av),
                ('water', '수분', tank_data['water'], new_water),
                ('org_cl', 'Org Cl', tank_data['org_cl'], new_ocl),
            ]
            
            for key, label, old_val, new_val in compare_list:
                if abs(old_val - new_val) > 0.001: # 미세 오차 제외
                    st.session_state.correction_log.append({
                        "날짜": date_key,
                        "탱크": target_tank_name,
                        "항목": label,
                        "예측값": round(old_val, 3),
                        "실측값": round(new_val, 3),
                        "오차(Diff)": round(new_val - old_val, 3)
                    })
            
            # 2. 데이터 업데이트
            tank_data['qty'] = new_qty
            tank_data['av'] = new_av
            tank_data['water'] = new_water
            tank_data['metal'] = new_metal
            tank_data['p'] = new_p
            tank_data['org_cl'] = new_ocl
            tank_data['inorg_cl'] = new_icl
            
            st.success("데이터가 수정되었습니다. 오차 정보가 기록되었습니다.")

# ---------------------------------------------------------
# [TAB 6] 예측 정확도 분석 (Analysis) - NEW
# ---------------------------------------------------------
elif menu == "⑥ 예측 정확도 분석 (Analysis)":
    st.title("📈 예측 vs 실측 오차 분석")
    
    if len(st.session_state.correction_log) == 0:
        st.info("아직 보정 기록이 없습니다. '⑤ 재고/품질 보정' 메뉴에서 데이터를 수정해보세요.")
    else:
        # 데이터프레임 변환
        df_log = pd.DataFrame(st.session_state.correction_log)
        
        # 1. 전체 기록 테이블
        st.subheader("📋 보정 이력 (History)")
        st.dataframe(df_log, use_container_width=True)
        
        st.markdown("---")
        
        # 2. 항목별 오차 분석 (필터링)
        st.subheader("📊 항목별 오차 추이")
        
        # 탭으로 구분
        tab_av, tab_qty, tab_cl = st.tabs(["AV 오차", "재고 오차", "염소 오차"])
        
        with tab_av:
            df_av = df_log[df_log['항목'] == 'AV']
            if not df_av.empty:
                st.line_chart(df_av, x='날짜', y='오차(Diff)', color='#ff4b4b')
                st.caption("그래프가 0 위에 있으면 실측이 더 높음, 아래면 실측이 더 낮음")
            else:
                st.write("AV 수정 기록이 없습니다.")
                
        with tab_qty:
            df_qty = df_log[df_log['항목'] == '재고']
            if not df_qty.empty:
                st.bar_chart(df_qty, x='날짜', y='오차(Diff)')
            else:
                st.write("재고 수정 기록이 없습니다.")
                
        with tab_cl:
            df_cl = df_log[df_log['항목'] == 'Org Cl']
            if not df_cl.empty:
                st.line_chart(df_cl, x='날짜', y='오차(Diff)')
            else:
                st.write("염소 수정 기록이 없습니다.")