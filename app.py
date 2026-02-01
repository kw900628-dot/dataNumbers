import streamlit as st
import pandas as pd
import plotly.express as px
import re
import io

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="회원 데이터 분석", layout="wide")
st.title("📊 과정별 회원 수 분석 대시보드")

# ---------------------------------------------------------
# 2. 파일 업로드
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Upload")
    st.markdown("""
    **지원하는 방식:**
    1. 월별로 파일이 따로따로 있는 경우 (여러 개 선택)
    2. 하나의 파일에 시트별로 월이 나눠진 경우 (하나만 선택)
    """)
    
    uploaded_files = st.file_uploader(
        "엑셀 파일 업로드 (.xlsx)", 
        type=['xlsx'], 
        accept_multiple_files=True
    )

if not uploaded_files:
    st.info("👈 왼쪽 사이드바에서 엑셀 파일(.xlsx)을 업로드해 주세요.")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 처리 로직 (BytesIO + Hybrid)
# ---------------------------------------------------------
all_data = []
progress_bar = st.progress(0)
total_files = len(uploaded_files)
error_logs = []

for i, file in enumerate(uploaded_files):
    try:
        # [핵심] 파일을 메모리로 읽어서 포인터 오류 방지
        file_bytes = file.getvalue()
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes), engine='openpyxl')
        
        sheet_names = excel_file.sheet_names
        
        # 파일명에서 '월' 찾기
        file_month_match = re.search(r'(\d+)월', file.name)
        file_month = int(file_month_match.group(1)) if file_month_match else None
        
        for sheet_name in sheet_names:
            # 시트명에서 '월' 찾기
            sheet_month_strict = re.search(r'(\d+)월', sheet_name)
            
            if sheet_month_strict:
                month = int(sheet_month_strict.group(1))
            elif file_month:
                month = file_month
            else:
                num_match = re.search(r'(\d+)', sheet_name)
                month = int(num_match.group(1)) if num_match else 1
            
            # 데이터 읽기
            df_temp = pd.read_excel(excel_file, sheet_name=sheet_name, index_col='커리큘럼')
            
            if not df_temp.empty:
                df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원 수')
                df_melted['월'] = month
                df_melted['과정 그룹'] = df_melted['커리큘럼'].str.split('과정').str[0] + '과정'
                all_data.append(df_melted)
            
    except Exception as e:
        error_logs.append(f"'{file.name}' 처리 실패: {e}")

    progress_bar.progress((i + 1) / total_files)

if not all_data:
    st.error("❌ 처리할 수 있는 데이터가 없습니다.")
    if error_logs:
        st.write(error_logs)
    st.stop()

df_total = pd.concat(all_data, ignore_index=True)

# 정렬 및 카테고리화
age_order = ['미취학'] + [str(x) for x in range(8, 20)] + ['성인']
curriculum_order = [f"{p}과정 {s}단계" for p in ['A', 'B', 'C', 'D'] for s in range(1, 5)]

df_total['연령'] = df_total['연령'].astype(str)
df_total['연령'] = pd.Categorical(df_total['연령'], categories=age_order, ordered=True)
df_total['커리큘럼'] = pd.Categorical(df_total['커리큘럼'], categories=curriculum_order, ordered=True)
df_total = df_total.sort_values(['월', '커리큘럼', '연령'])

st.success(f"✅ 데이터 병합 완료! (총 {len(all_data)}개 데이터 세트)")
progress_bar.empty()

# ---------------------------------------------------------
# 5. 시각화 섹션
# ---------------------------------------------------------

# 🎨 [색상 정의]
process_color_map = {
    'A과정': '#FFD700', 'B과정': '#FF8C00', 'C과정': '#2ECC71', 'D과정': '#3498DB'
}

age_color_map = {
    '미취학': '#F48FB1',
    '8': '#E3F2FD', '9': '#BBDEFB', '10': '#90CAF9', '11': '#64B5F6', '12': '#42A5F5', '13': '#1E88E5',
    '14': '#A5D6A7', '15': '#66BB6A', '16': '#43A047',
    '17': '#FFCC80', '18': '#FFB74D', '19': '#FB8C00',
    '성인': '#78909C' 
}

# [수정됨] 탭을 3개로 줄임 (이탈 분석 삭제)
tab1, tab2, tab3 = st.tabs(["🔥 연령별 선호도", "🗓️ 시즌성", "👥 회원 구성 변화"])

# [Tab 1] 연령별 선호도
with tab1:
    st.subheader("🔥 연령별 선호도 심층 분석")
    chart_type = st.radio("그래프 유형", ["📈 라인 차트", "📊 누적 막대", "히트맵"], horizontal=True)
    group_data = df_total.groupby(['과정 그룹', '연령'])['회원 수'].sum().reset_index()

    if "라인" in chart_type:
        fig = px.line(group_data, x='연령', y='회원 수', color='과정 그룹', markers=True, symbol='과정 그룹', color_discrete_map=process_color_map)
        st.plotly_chart(fig, use_container_width=True)
    elif "막대" in chart_type:
        fig = px.bar(group_data, x='과정 그룹', y='회원 수', color='연령', text_auto=True, color_discrete_map=age_color_map)
        fig.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': ['A과정', 'B과정', 'C과정', 'D과정']})
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.density_heatmap(group_data, x='과정 그룹', y='연령', z='회원 수', text_auto=True, color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)

    # 💡 [인사이트]
    st.markdown("### 💡 AI Data Insight")
    top_ages = group_data.loc[group_data.groupby('과정 그룹')['회원 수'].idxmax()]
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📌 과정별 주력 타깃 연령**")
        for _, row in top_ages.iterrows():
            st.write(f"- **{row['과정 그룹']}**: `{row['연령']}` ({row['회원 수']:,}명)")
    with col2:
        st.info("Tip: 그래프의 산이 가장 높게 솟은 지점이 핵심 타깃 연령입니다.")

# [Tab 2] 시즌성 분석 (기존 Tab 3)
with tab2:
    st.subheader("과정별 월간 추이")
    trend_data = df_total.groupby(['월', '과정 그룹'])['회원 수'].sum().reset_index()
    fig = px.line(trend_data, x='월', y='회원 수', color='과정 그룹', markers=True, color_discrete_map=process_color_map)
    fig.update_xaxes(tickvals=list(range(1, 13)), range=[0.5, 12.5], title_text="월 (Month)")
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [인사이트]
    st.markdown("### 💡 Seasonality Insight")
    if df_total['월'].nunique() > 1:
        peak_months = trend_data.loc[trend_data.groupby('과정 그룹')['회원 수'].idxmax()]
        cols = st.columns(4)
        for idx, (_, row) in enumerate(peak_months.iterrows()):
            with cols[idx % 4]:
                st.metric(label=f"{row['과정 그룹']} 피크", value=f"{row['월']}월", delta=f"{row['회원 수']:,}명")
    else:
        st.info("ℹ️ 현재 1개월치 데이터만 있습니다. 여러 달의 데이터를 업로드하면 추세선이 연결됩니다.")

# [Tab 3] 회원 구성 변화 (기존 Tab 4)
with tab3:
    st.subheader("월별 회원 구성비 변화")
    bar_data = df_total.groupby(['월', '연령'])['회원 수'].sum().reset_index()
    fig = px.bar(bar_data, x='월', y='회원 수', color='연령', text_auto=True, color_discrete_map=age_color_map)
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [인사이트]
    st.markdown("### 💡 Demographic Shift")
    last_month = df_total['월'].max()
    last_month_data = bar_data[bar_data['월'] == last_month]
    top_age = last_month_data.loc[last_month_data['회원 수'].idxmax()]
    
    st.info(f"📊 **최신 트렌드 ({last_month}월):** 가장 비중이 큰 연령대는 **'{top_age['연령']}'** 입니다.")