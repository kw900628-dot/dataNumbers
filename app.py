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
# 2. 파일 업로드 (엑셀 전용 설정)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 Data Upload")
    uploaded_files = st.file_uploader(
        "회원 수 통계 데이터를 업로드해 주세요 (1월~12월)", 
        type=['xlsx'], 
        accept_multiple_files=True
    )

if not uploaded_files:
    st.info("👈 왼쪽 사이드바에서 엑셀 파일(.xlsx)을 업로드해주세요.")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 처리 로직 (엑셀 읽기)
# ---------------------------------------------------------
all_data = []
progress_bar = st.progress(0)

for i, file in enumerate(uploaded_files):
    try:
        # 파일명에서 월(Month) 정보 추출
        match = re.search(r'(\d+)월', file.name)
        if match:
            month = int(match.group(1))
        else:
            num_match = re.search(r'(\d+)', file.name)
            month = int(num_match.group(1)) if num_match else (i + 1)
        
        # 엑셀 읽기
        df_temp = pd.read_excel(file, index_col='커리큘럼', engine='openpyxl')
        
        # 전처리 (Wide -> Long)
        df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원수')
        df_melted['월'] = month
        df_melted['과정그룹'] = df_melted['커리큘럼'].str.split('과정').str[0] + '과정'
        
        all_data.append(df_melted)
        
    except Exception as e:
        st.error(f"❌ '{file.name}' 읽기 실패: {e}")

    progress_bar.progress((i + 1) / len(uploaded_files))

if not all_data:
    st.error("❌ 처리할 수 있는 데이터가 없습니다.")
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

st.success(f"✅ 총 {len(uploaded_files)}개 엑셀 파일 처리 완료!")
progress_bar.empty()

# ---------------------------------------------------------
# 5. 시각화 섹션 (탭 4개로 축소)
# ---------------------------------------------------------
# [수정됨] 원본 데이터 탭 삭제
tab1, tab2, tab3, tab4 = st.tabs(["🔥 연령별 선호도", "📉 이탈 분석", "🗓️ 시즌성", "👥 인구 변화"])

# [Tab 1] 연령별 선호도 (기존 Tab 2)
with tab1:
    st.subheader("🔥 연령별 선호도 심층 분석")
    
    chart_type = st.radio(
        "그래프 유형을 선택하세요", 
        ["📈 라인 차트 (연령 분포 비교)", "📊 누적 막대 (구성비 비교)", "heatmap (기존)"],
        horizontal=True
    )

    group_data = df_total.groupby(['과정그룹', '연령'])['회원수'].sum().reset_index()

    # 차트 그리기
    if chart_type.startswith("📈"):
        fig = px.line(group_data, x='연령', y='회원수', color='과정그룹', markers=True, symbol='과정그룹', title="과정별 회원 연령 분포 (Peak 지점)")
        st.plotly_chart(fig, use_container_width=True)
    elif chart_type.startswith("📊"):
        fig = px.bar(group_data, x='과정그룹', y='회원수', color='연령', title="과정별 연령대 구성 비율", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.density_heatmap(group_data, x='과정그룹', y='연령', z='회원수', text_auto=True, color_continuous_scale='Blues', title="과정별 연령 분포 히트맵")
        st.plotly_chart(fig, use_container_width=True)

    # 💡 [자동 인사이트 도출]
    st.markdown("### 💡 AI Data Insight")
    top_ages = group_data.loc[group_data.groupby('과정그룹')['회원수'].idxmax()]
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📌 과정별 주력 타깃 연령 (Most Popular Age)**")
        for _, row in top_ages.iterrows():
            st.write(f"- **{row['과정그룹']}**: `{row['연령']}` (총 {row['회원수']:,}명)")
    with col2:
        st.info("Tip: 그래프의 산이 가장 높게 솟은 지점이 해당 과정의 핵심 타깃 연령입니다.")

# [Tab 2] 이탈 분석 (기존 Tab 3)
with tab2:
    st.subheader("커리큘럼별 회원 유지 현황")
    ages = st.multiselect("분석할 연령대를 선택하세요", age_order, default=['미취학', '8', '성인'])
    
    if ages:
        filtered_df = df_total[df_total['연령'].isin(ages)]
        line_data = filtered_df.groupby(['커리큘럼', '연령'])['회원수'].sum().reset_index()
        
        fig = px.line(line_data, x='커리큘럼', y='회원수', color='연령', markers=True, title="단계별 회원수 변화")
        st.plotly_chart(fig, use_container_width=True)
        
        # 💡 [자동 인사이트 도출]
        st.markdown("### 💡 Retention Analysis")
        start_sum = filtered_df[filtered_df['커리큘럼'].astype(str).str.contains('1단계')]['회원수'].sum()
        end_sum = filtered_df[filtered_df['커리큘럼'].astype(str).str.contains('4단계')]['회원수'].sum()
        
        retention_rate = (end_sum / start_sum * 100) if start_sum > 0 else 0
        
        st.metric(label="선택된 연령대의 1단계 대비 4단계 평균 유지율", value=f"{retention_rate:.1f}%")
        
        if retention_rate < 50:
            st.warning(f"⚠️ 경고: 선택된 연령대의 유지율이 {retention_rate:.1f}%로 낮습니다. 커리큘럼 난이도나 만족도를 점검할 필요가 있습니다.")
        else:
            st.success(f"✅ 양호: 선택된 연령대의 유지율이 {retention_rate:.1f}%로 안정적입니다.")

# [Tab 3] 시즌성 분석 (기존 Tab 4)
with tab3:
    st.subheader("과정별 월간 추이")
    trend_data = df_total.groupby(['월', '과정그룹'])['회원수'].sum().reset_index()
    fig = px.line(trend_data, x='월', y='회원수', color='과정그룹', markers=True, title="월별 과정 등록 추이")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [자동 인사이트 도출]
    st.markdown("### 💡 Seasonality Insight")
    peak_months = trend_data.loc[trend_data.groupby('과정그룹')['회원수'].idxmax()]
    
    st.markdown("**📅 과정별 회원수 피크(Peak) 시즌**")
    cols = st.columns(4)
    for idx, (_, row) in enumerate(peak_months.iterrows()):
        with cols[idx % 4]:
            st.metric(label=f"{row['과정그룹']} 피크", value=f"{row['월']}월", delta=f"{row['회원수']:,}명")
    
    st.caption("※ 피크 시즌 1~2개월 전이 해당 과정의 마케팅 골든타임입니다.")

# [Tab 4] 인구 변화 분석 (기존 Tab 5)
with tab4:
    st.subheader("월별 회원 구성비 변화")
    bar_data = df_total.groupby(['월', '연령'])['회원수'].sum().reset_index()
    fig = px.bar(bar_data, x='월', y='회원수', color='연령', title="월별 연령 구성 비율", text_auto=True)
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)
    
    # 💡 [자동 인사이트 도출]
    st.markdown("### 💡 Demographic Shift")
    last_month = df_total['월'].max()
    last_month_data = bar_data[bar_data['월'] == last_month]
    top_age_group = last_month_data.loc[last_month_data['회원수'].idxmax()]
    
    st.info(f"📊 **최신 트렌드 ({last_month}월 기준):** 현재 학원에서 가장 비중이 큰 연령대는 **'{top_age_group['연령']}'** 입니다. (전체의 약 {top_age_group['회원수']/last_month_data['회원수'].sum()*100:.1f}%)")