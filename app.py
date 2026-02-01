import streamlit as st
import pandas as pd
import plotly.express as px
import re

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="회원 데이터 분석", layout="wide")
st.title("📊 과정별 회원 수 분석 대시보드")

# ---------------------------------------------------------
# 2. 파일 업로드 (다중 파일 + 다중 시트 모두 지원)
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
# 3. 데이터 처리 로직 (Hybrid: 파일 -> 시트 순회)
# ---------------------------------------------------------
all_data = []
progress_bar = st.progress(0)
total_files = len(uploaded_files)

for i, file in enumerate(uploaded_files):
    try:
        xls = pd.ExcelFile(file, engine='openpyxl')
        sheet_names = xls.sheet_names
        
        file_month_match = re.search(r'(\d+)월?', file.name)
        file_month = int(file_month_match.group(1)) if file_month_match else None
        
        for sheet_name in sheet_names:
            sheet_match = re.search(r'(\d+)월?', sheet_name)
            
            if sheet_match:
                month = int(sheet_match.group(1))
            elif file_month:
                month = file_month
            else:
                continue
            
            df_temp = pd.read_excel(file, sheet_name=sheet_name, index_col='커리큘럼', engine='openpyxl')
            
            df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원 수')
            df_melted['월'] = month
            df_melted['과정 그룹'] = df_melted['커리큘럼'].str.split('과정').str[0] + '과정'
            
            all_data.append(df_melted)
            
    except Exception as e:
        st.warning(f"⚠️ '{file.name}' 처리 중 일부 오류 발생: {e}")

    progress_bar.progress((i + 1) / total_files)

if not all_data:
    st.error("❌ 처리할 수 있는 데이터가 없습니다. 파일명이나 시트명에 '월' 또는 숫자가 포함되어 있는지 확인해주세요.")
    st.stop()

df_total = pd.concat(all_data, ignore_index=True)

# ---------------------------------------------------------
# 4. 정렬 및 카테고리화
# ---------------------------------------------------------
age_order = ['미취학'] + [str(x) for x in range(8, 20)] + ['성인']
curriculum_order = [f"{p}과정 {s}단계" for p in ['A', 'B', 'C', 'D'] for s in range(1, 5)]

df_total['연령'] = df_total['연령'].astype(str)
df_total['연령'] = pd.Categorical(df_total['연령'], categories=age_order, ordered=True)
df_total['커리큘럼'] = pd.Categorical(df_total['커리큘럼'], categories=curriculum_order, ordered=True)
df_total = df_total.sort_values(['월', '커리큘럼', '연령'])

st.success(f"✅ 데이터 병합 완료! (총 {len(all_data)}개 데이터 세트 처리됨)")
progress_bar.empty()

# ---------------------------------------------------------
# 5. 시각화 섹션
# ---------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["🔥 연령별 선호도", "📉 이탈 분석", "🗓️ 시즌성", "👥 인구 변화"])

# [Tab 1] 연령별 선호도
with tab1:
    st.subheader("🔥 연령별 선호도 심층 분석")
    
    chart_type = st.radio(
        "그래프 유형을 선택하세요", 
        ["📈 라인 차트 (연령 분포 비교)", "📊 누적 막대 (구성비 비교)", "히트맵"],
        horizontal=True
    )

    group_data = df_total.groupby(['과정 그룹', '연령'])['회원 수'].sum().reset_index()

    # 🎨 1. 라인 차트용 색상 (과정별)
    process_color_map = {
        'A과정': '#FFD700', # Gold
        'B과정': '#FF8C00', # DarkOrange
        'C과정': '#2ECC71', # Emerald Green
        'D과정': '#3498DB'  # Dodger Blue
    }

    # 🎨 2. 누적 막대용 색상 (연령 그룹별 톤온톤)
    age_color_map = {
        '미취학': '#F48FB1', # Pink (독립)
        
        # 초등 (8~13) - Blue Scale
        '8': '#E3F2FD', '9': '#BBDEFB', '10': '#90CAF9', 
        '11': '#64B5F6', '12': '#42A5F5', '13': '#1E88E5',
        
        # 중등 (14~16) - Green Scale
        '14': '#A5D6A7', '15': '#66BB6A', '16': '#43A047',
        
        # 고등 (17~19) - Orange Scale
        '17': '#FFCC80', '18': '#FFB74D', '19': '#FB8C00',
        
        # 성인 - Grey Scale
        '성인': '#78909C' 
    }

    if chart_type.startswith("📈"):
        fig = px.line(
            group_data, x='연령', y='회원 수', color='과정 그룹', 
            markers=True, symbol='과정 그룹', 
            title="과정별 회원 연령 분포 (Peak 지점)",
            color_discrete_map=process_color_map # 과정별 색상 적용
        )
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type.startswith("📊"):
        fig = px.bar(
            group_data, x='과정 그룹', y='회원 수', color='연령', 
            title="과정별 연령대 구성 비율", text_auto=True,
            color_discrete_map=age_color_map # 연령별 톤온톤 색상 적용
        )
        # 막대 순서가 꼬이지 않게 명시적 정렬
        fig.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': ['A과정', 'B과정', 'C과정', 'D과정']})
        st.plotly_chart(fig, use_container_width=True)

    else:
        fig = px.density_heatmap(
            group_data, x='과정 그룹', y='연령', z='회원 수', 
            text_auto=True, color_continuous_scale='Blues', 
            title="과정별 연령 분포 히트맵"
        )
        st.plotly_chart(fig, use_container_width=True)

    # 💡 [자동 인사이트]
    st.markdown("### 💡 AI Data Insight")
    top_ages = group_data.loc[group_data.groupby('과정 그룹')['회원 수'].idxmax()]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📌 과정별 주력 타깃 연령 (Most Popular Age)**")
        for _, row in top_ages.iterrows():
            st.write(f"- **{row['과정 그룹']}**: `{row['연령']}` (총 {row['회원 수']:,}명)")
    with col2:
        st.info("Tip: 그래프의 산이 가장 높게 솟은 지점이 해당 과정의 핵심 타깃 연령입니다.")

# [Tab 2] 이탈 분석
with tab2:
    st.subheader("커리큘럼별 회원 유지 현황")
    ages = st.multiselect("분석할 연령대를 선택하세요", age_order, default=['미취학', '8', '성인'])
    
    if ages:
        filtered_df = df_total[df_total['연령'].isin(ages)]
        line_data = filtered_df.groupby(['커리큘럼', '연령'])['회원 수'].sum().reset_index()
        
        fig = px.line(line_data, x='커리큘럼', y='회원 수', color='연령', markers=True, title="단계별 회원 수 변화")
        st.plotly_chart(fig, use_container_width=True)
        
        # 💡 [자동 인사이트]
        st.markdown("### 💡 Retention Analysis")
        start_sum = filtered_df[filtered_df['커리큘럼'].astype(str).str.contains('1단계')]['회원 수'].sum()
        end_sum = filtered_df[filtered_df['커리큘럼'].astype(str).str.contains('4단계')]['회원 수'].sum()
        retention_rate = (end_sum / start_sum * 100) if start_sum > 0 else 0
        
        st.metric(label="선택된 연령대의 1단계 대비 4단계 평균 유지율", value=f"{retention_rate:.1f}%")
        
        if retention_rate < 50:
            st.warning(f"⚠️ 경고: 유지율({retention_rate:.1f}%)이 낮습니다.")
        else:
            st.success(f"✅ 양호: 유지율({retention_rate:.1f}%)이 안정적입니다.")

# [Tab 3] 시즌성 분석
with tab3:
    st.subheader("과정별 월간 추이")
    trend_data = df_total.groupby(['월', '과정 그룹'])['회원 수'].sum().reset_index()
    fig = px.line(trend_data, x='월', y='회원 수', color='과정 그룹', markers=True, title="월별 과정 등록 추이")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [자동 인사이트]
    st.markdown("### 💡 Seasonality Insight")
    peak_months = trend_data.loc[trend_data.groupby('과정 그룹')['회원 수'].idxmax()]
    
    st.markdown("**📅 과정별 회원 수 피크(Peak) 시즌**")
    cols = st.columns(4)
    for idx, (_, row) in enumerate(peak_months.iterrows()):
        with cols[idx % 4]:
            st.metric(label=f"{row['과정 그룹']} 피크", value=f"{row['월']}월", delta=f"{row['회원 수']:,}명")

# [Tab 4] 인구 변화 분석
with tab4:
    st.subheader("월별 회원 구성비 변화")
    bar_data = df_total.groupby(['월', '연령'])['회원 수'].sum().reset_index()
    fig = px.bar(bar_data, x='월', y='회원 수', color='연령', title="월별 연령 구성 비율", text_auto=True)
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [자동 인사이트]
    st.markdown("### 💡 Demographic Shift")
    last_month = df_total['월'].max()
    last_month_data = bar_data[bar_data['월'] == last_month]
    top_age_group = last_month_data.loc[last_month_data['회원 수'].idxmax()]
    
    st.info(f"📊 **최신 트렌드 ({last_month}월 기준):** 가장 비중이 큰 연령대는 **'{top_age_group['연령']}'** 입니다.")