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
# 3. 데이터 처리 로직 (수정됨: 파일명 우선순위 강화)
# ---------------------------------------------------------
all_data = []
progress_bar = st.progress(0)
total_files = len(uploaded_files)

for i, file in enumerate(uploaded_files):
    try:
        xls = pd.ExcelFile(file, engine='openpyxl')
        sheet_names = xls.sheet_names
        
        # [수정 1] 파일명에서 '월'이 붙은 숫자만 확실하게 찾기 (연도 '2025' 혼동 방지)
        file_month_match = re.search(r'(\d+)월', file.name)
        file_month = int(file_month_match.group(1)) if file_month_match else None
        
        for sheet_name in sheet_names:
            # [수정 2] 시트 이름 분석 로직 개선
            # 시트 이름에 명확히 'N월'이라고 적혀 있는지 확인
            sheet_month_strict = re.search(r'(\d+)월', sheet_name)
            
            if sheet_month_strict:
                # 1순위: 시트 이름에 '월'이 있으면 무조건 그걸 따름 (시트별로 월이 다른 경우)
                month = int(sheet_month_strict.group(1))
            elif file_month:
                # 2순위: 시트 이름이 애매하면(Sheet1 등), 파일명에 있는 '월'을 따름
                month = file_month
            else:
                # 3순위: 둘 다 없으면 시트 이름의 숫자라도 가져옴 (최후의 수단)
                num_match = re.search(r'(\d+)', sheet_name)
                month = int(num_match.group(1)) if num_match else 1
            
            # 엑셀 읽기
            df_temp = pd.read_excel(file, sheet_name=sheet_name, index_col='커리큘럼', engine='openpyxl')
            
            df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원 수')
            df_melted['월'] = month
            df_melted['과정 그룹'] = df_melted['커리큘럼'].str.split('과정').str[0] + '과정'
            
            all_data.append(df_melted)
            
    except Exception as e:
        st.warning(f"⚠️ '{file.name}' 처리 중 일부 오류 발생: {e}")

    progress_bar.progress((i + 1) / total_files)

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

# 🎨 [색상 정의] 모든 탭에서 공통으로 사용하기 위해 탭 생성 전에 정의
# 1. 과정별 색상
process_color_map = {
    'A과정': '#FFD700', # Gold
    'B과정': '#FF8C00', # DarkOrange
    'C과정': '#2ECC71', # Emerald Green
    'D과정': '#3498DB'  # Dodger Blue
}

# 2. 연령별 색상 (톤온톤)
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
            color_discrete_map=age_color_map # 연령별 색상 적용
        )
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

# [Tab 2] 이탈 분석 (연령별 색상 적용 + 0인 데이터 숨김 기능 추가)
with tab2:
    st.subheader("커리큘럼별 회원 유지 현황")
    
    # 1. 연령대 선택
    ages = st.multiselect("분석할 연령대를 선택하세요", age_order, default=['미취학', '8', '성인'])
    
    if ages:
        # 선택된 연령대 데이터만 필터링
        filtered_df = df_total[df_total['연령'].isin(ages)]
        
        # 그룹핑 (커리큘럼 x 연령)
        line_data = filtered_df.groupby(['커리큘럼', '연령'])['회원 수'].sum().reset_index()
        
        # -------------------------------------------------------------
        # [✨ 핵심 수정] 데이터가 모두 0인 연령대(Line) 자동 제거 로직
        # -------------------------------------------------------------
        # 각 연령별 총 회원 수를 구함
        total_by_age = line_data.groupby('연령')['회원 수'].sum()
        
        # 총합이 0보다 큰 연령대만 남김 (데이터가 있는 연령만 추출)
        valid_ages = total_by_age[total_by_age > 0].index.tolist()
        
        # 실제 그릴 데이터에서 0인 연령대 제외
        final_line_data = line_data[line_data['연령'].isin(valid_ages)]
        
        # 제거된 연령이 있다면 사용자에게 알림 (선택 사항)
        removed_ages = set(ages) - set(valid_ages)
        if removed_ages:
            st.caption(f"※ 데이터가 0인 연령대는 그래프에서 자동 제외되었습니다: {', '.join(removed_ages)}")
        # -------------------------------------------------------------

        if not final_line_data.empty:
            fig = px.line(
                final_line_data, x='커리큘럼', y='회원 수', color='연령', 
                markers=True, 
                title="단계별 회원 수 변화 (색상: 연령 그룹)",
                color_discrete_map=age_color_map # 연령별 색상 적용
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 💡 [자동 인사이트]
            st.markdown("### 💡 Retention Analysis")
            
            # 1단계와 4단계 비교 (여기서도 valid_ages에 있는 데이터만으로 계산해야 안전함)
            # 전체 filtered_df를 쓰되, 0인 데이터는 어차피 합계에 영향 없으므로 그대로 진행
            start_sum = filtered_df[filtered_df['커리큘럼'].astype(str).str.contains('1단계')]['회원 수'].sum()
            end_sum = filtered_df[filtered_df['커리큘럼'].astype(str).str.contains('4단계')]['회원 수'].sum()
            
            retention_rate = (end_sum / start_sum * 100) if start_sum > 0 else 0
            
            st.metric(label="선택된 연령대의 1단계 대비 4단계 평균 유지율", value=f"{retention_rate:.1f}%")
            
            if retention_rate < 50:
                st.warning(f"⚠️ 경고: 유지율({retention_rate:.1f}%)이 낮습니다.")
            else:
                st.success(f"✅ 양호: 유지율({retention_rate:.1f}%)이 안정적입니다.")
        else:
            st.warning("선택하신 연령대의 데이터가 모두 0입니다.")

# [Tab 3] 시즌성 분석 (과정별 색상 적용)
with tab3:
    st.subheader("과정별 월간 추이")
    
    # 데이터 집계
    trend_data = df_total.groupby(['월', '과정 그룹'])['회원 수'].sum().reset_index()
    
    # 라인 차트 생성
    fig = px.line(
        trend_data, x='월', y='회원 수', color='과정 그룹', 
        markers=True, 
        title="월별 과정 등록 추이 (색상: 과정 그룹)",
        color_discrete_map=process_color_map # 과정별 색상 적용
    )
    
    # -------------------------------------------------------------
    # [✨ 핵심 수정] X축을 1월~12월로 강제 고정하여 마이너스 방지
    # -------------------------------------------------------------
    fig.update_xaxes(
        tickvals=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # 눈금을 1~12로 지정
        range=[0.5, 12.5],  # 그래프 보여주는 범위를 0.5~12.5로 고정
        title_text="월 (Month)"
    )
    # -------------------------------------------------------------
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [자동 인사이트]
    st.markdown("### 💡 Seasonality Insight")
    
    # 데이터가 한 달치만 있으면 피크 분석이 의미가 없으므로 예외 처리
    if df_total['월'].nunique() > 1:
        peak_months = trend_data.loc[trend_data.groupby('과정 그룹')['회원 수'].idxmax()]
        
        st.markdown("**📅 과정별 회원 수 피크(Peak) 시즌**")
        cols = st.columns(4)
        for idx, (_, row) in enumerate(peak_months.iterrows()):
            with cols[idx % 4]:
                st.metric(label=f"{row['과정 그룹']} 피크", value=f"{row['월']}월", delta=f"{row['회원 수']:,}명")
    else:
        st.info("ℹ️ 현재 데이터가 1개 월(Month)뿐이라 추세선이 점으로 표시됩니다. 2개 이상의 월 데이터를 업로드하면 선이 연결됩니다.")

# [Tab 4] 인구 변화 분석 (연령별 색상 적용)
with tab4:
    st.subheader("월별 회원 구성비 변화")
    bar_data = df_total.groupby(['월', '연령'])['회원 수'].sum().reset_index()
    fig = px.bar(
        bar_data, x='월', y='회원 수', color='연령', 
        title="월별 연령 구성 비율 (색상: 연령 그룹)", 
        text_auto=True,
        color_discrete_map=age_color_map # [수정] 연령별 색상 적용
    )
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [자동 인사이트]
    st.markdown("### 💡 Demographic Shift")
    last_month = df_total['월'].max()
    last_month_data = bar_data[bar_data['월'] == last_month]
    top_age_group = last_month_data.loc[last_month_data['회원 수'].idxmax()]
    
    st.info(f"📊 **최신 트렌드 ({last_month}월 기준):** 가장 비중이 큰 연령대는 **'{top_age_group['연령']}'** 입니다.")