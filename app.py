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
# --------------------------------