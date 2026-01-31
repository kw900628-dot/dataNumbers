import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import matplotlib.font_manager as fm  # 폰트 매니저 추가
import re  # <--- [중요] 이 줄이 반드시 있어야 합니다!

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="회원 데이터 분석", layout="wide")
st.title("📊 학원 커리큘럼 분석 대시보드")

@st.cache_data
def font_setup():
    # 리눅스(Streamlit Cloud) 환경인지 확인
    if os.name == 'posix':
        # packages.txt로 설치된 나눔고딕 폰트 경로
        font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
            plt.rc('font', family='NanumGothic')
        else:
            # 폰트가 없을 경우를 대비해 기본 설정 유지 (에러 방지)
            pass
    else:
        # 윈도우/맥(로컬) 환경일 경우
        if os.name == 'nt': # Windows
            plt.rc('font', family='Malgun Gothic')
        elif os.name == 'darwin': # Mac
            plt.rc('font', family='AppleGothic')
            
    plt.rcParams['axes.unicode_minus'] = False

# 폰트 설정 실행
font_setup()

# ---------------------------------------------------------
# 2. 파일 업로드 (사이드바)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 데이터 업로드")
    uploaded_files = st.file_uploader(
        "엑셀 파일 업로드 (다중 선택 가능)", 
        type=['xlsx'], 
        accept_multiple_files=True
    )

# =========================================================
# [중요] 파일이 없으면 여기서 실행을 멈춤 (에러 방지 핵심)
# =========================================================
if not uploaded_files:
    st.info("👈 왼쪽 사이드바에서 엑셀 파일을 업로드하면 분석이 시작됩니다.")
    st.stop()  # 코드는 여기서 멈추고, 아래 내용을 실행하지 않습니다.

# ---------------------------------------------------------
# 3. 데이터 처리 로직 (파일이 있을 때만 실행됨)
# ---------------------------------------------------------
all_data = []
progress_bar = st.progress(0)

for i, file in enumerate(uploaded_files):
    try:
        # 파일명에서 월(Month) 정보 찾기
        match = re.search(r'(\d+)월', file.name)
        if match:
            month = int(match.group(1))
        else:
            # 월이 없으면 파일명 내 아무 숫자나 찾기
            num_match = re.search(r'(\d+)', file.name)
            month = int(num_match.group(1)) if num_match else (i + 1)
        
        # 엑셀 읽기
        df_temp = pd.read_excel(file, index_col='커리큘럼')
        
        # 데이터 구조 변환 (Melt)
        df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원수')
        df_melted['월'] = month
        
        # 과정 그룹 추출
        df_melted['과정그룹'] = df_melted['커리큘럼'].str.split('과정').str[0] + '과정'
        
        all_data.append(df_melted)
        
    except Exception as e:
        st.warning(f"⚠️ '{file.name}' 처리 중 문제 발생: {e}")

    # 진행률 업데이트
    progress_bar.progress((i + 1) / len(uploaded_files))

# ---------------------------------------------------------
# 4. 데이터 병합 및 시각화
# ---------------------------------------------------------
# 처리된 데이터가 하나라도 있어야 합치기를 시도함
if not all_data:
    st.error("❌ 처리할 수 있는 데이터가 없습니다. 엑셀 파일 내용을 확인해주세요.")
    st.stop()

# 여기 도달했다는 건 데이터가 안전하게 있다는 뜻
df_total = pd.concat(all_data, ignore_index=True)

# 정렬 순서 정의
age_order = ['미취학'] + [str(x) for x in range(8, 20)] + ['성인']
curriculum_order = [f"{p}과정 {s}단계" for p in ['A', 'B', 'C', 'D'] for s in range(1, 5)]

# 범주형 변환 (정렬용)
df_total['연령'] = df_total['연령'].astype(str)
df_total['연령'] = pd.Categorical(df_total['연령'], categories=[str(x) for x in age_order], ordered=True)
df_total['커리큘럼'] = pd.Categorical(df_total['커리큘럼'], categories=curriculum_order, ordered=True)

st.success(f"✅ 총 {len(uploaded_files)}개 파일 처리 완료!")

# -------------------- 탭 시각화 --------------------
tab1, tab2, tab3, tab4 = st.tabs(["🔥 연령별 선호도", "📉 이탈 분석", "🗓️ 시즌성", "👥 인구 변화"])

with tab1:
    st.subheader("연령대별 과정 선호도")
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    pivot_heat = df_total.pivot_table(index='연령', columns='과정그룹', values='회원수', aggfunc='sum')
    sns.heatmap(pivot_heat, annot=True, fmt='d', cmap='YlGnBu', ax=ax1)
    st.pyplot(fig1)

with tab2:
    st.subheader("커리큘럼별 회원 유지 현황")
    fig2, ax2 = plt.subplots(figsize=(14, 6))
    sns.lineplot(data=df_total, x='커리큘럼', y='회원수', hue='연령', estimator='sum', errorbar=None, marker='o', ax=ax2)
    plt.xticks(rotation=45)
    st.pyplot(fig2)

with tab3:
    st.subheader("과정별 월간 추이")
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    monthly_trend = df_total.groupby(['월', '과정그룹'])['회원수'].sum().reset_index()
    sns.lineplot(data=monthly_trend, x='월', y='회원수', hue='과정그룹', marker='s', ax=ax3)
    ax3.set_xticks(range(1, 13))
    st.pyplot(fig3)

with tab4:
    st.subheader("월별 회원 구성비 변화")
    fig4, ax4 = plt.subplots(figsize=(12, 7))
    pivot_demo = df_total.pivot_table(index='월', columns='연령', values='회원수', aggfunc='sum')
    pivot_demo_pct = pivot_demo.div(pivot_demo.sum(axis=1), axis=0) * 100
    pivot_demo_pct.plot(kind='bar', stacked=True, colormap='Spectral', ax=ax4)
    plt.xticks(rotation=0)
    st.pyplot(fig4)