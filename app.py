import streamlit as st
import pandas as pd
import plotly.express as px
import re

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(page_title="회원 데이터 분석", layout="wide")
st.title("📊 학원 커리큘럼 분석 대시보드")

# ---------------------------------------------------------
# 2. 파일 업로드 (엑셀 전용 설정)
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 데이터 업로드")
    # [중요] 엑셀 파일(xlsx)만 허용하도록 설정
    uploaded_files = st.file_uploader(
        "1월~12월 엑셀 파일을 모두 선택해주세요", 
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
            # 파일명에 '월'이 없으면 숫자라도 찾기
            num_match = re.search(r'(\d+)', file.name)
            month = int(num_match.group(1)) if num_match else (i + 1)
        
        # [중요] 엑셀 파일 읽기 (read_excel 사용)
        # index_col='커리큘럼'은 데이터 첫 열이 커리큘럼 명칭일 경우 사용
        df_temp = pd.read_excel(file, index_col='커리큘럼', engine='openpyxl')
        
        # 데이터 전처리 (Wide -> Long Format 변환)
        df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원수')
        df_melted['월'] = month
        
        # 'A과정 1단계' -> 'A과정' 그룹핑
        df_melted['과정그룹'] = df_melted['커리큘럼'].str.split('과정').str[0] + '과정'
        
        all_data.append(df_melted)
        
    except Exception as e:
        st.error(f"❌ '{file.name}' 파일을 읽는 중 오류 발생: {e}")

    progress_bar.progress((i + 1) / len(uploaded_files))

# 데이터 병합 확인
if not all_data:
    st.error("❌ 처리할 수 있는 데이터가 없습니다.")
    st.stop()

df_total = pd.concat(all_data, ignore_index=True)

# ---------------------------------------------------------
# 4. 정렬 및 카테고리화 (그래프 순서 정리)
# ---------------------------------------------------------
# 연령대 순서 (사용자 데이터에 맞게 조정하세요)
age_order = ['미취학'] + [str(x) for x in range(8, 20)] + ['성인']

# 커리큘럼 순서
curriculum_order = [f"{p}과정 {s}단계" for p in ['A', 'B', 'C', 'D'] for s in range(1, 5)]

# 범주형 변환 (순서 강제 적용)
df_total['연령'] = df_total['연령'].astype(str)
df_total['연령'] = pd.Categorical(df_total['연령'], categories=age_order, ordered=True)
df_total['커리큘럼'] = pd.Categorical(df_total['커리큘럼'], categories=curriculum_order, ordered=True)

# 보기 좋게 정렬
df_total = df_total.sort_values(['월', '커리큘럼', '연령'])

st.success(f"✅ 총 {len(uploaded_files)}개 엑셀 파일 처리 완료!")
progress_bar.empty()

# ---------------------------------------------------------
# 5. 시각화 섹션 (Plotly 사용)
# ---------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 원본 데이터", "🔥 연령별 선호도", "📉 이탈 분석", "🗓️ 시즌성", "👥 인구 변화"])

with tab1:
    st.subheader("📋 통합 데이터 확인")
    st.dataframe(df_total, use_container_width=True)

with tab2:
    st.subheader("연령대별 과정 선호도 (Heatmap)")
    heat_data = df_total.groupby(['연령', '과정그룹'])['회원수'].sum().reset_index()
    fig = px.density_heatmap(
        heat_data, x='과정그룹', y='연령', z='회원수',
        text_auto=True, color_continuous_scale='Blues',
        title="과정별 연령 분포"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("커리큘럼별 회원 유지 현황")
    ages = st.multiselect("분석할 연령대를 선택하세요", age_order, default=['미취학', '8', '성인'])
    if ages:
        filtered_df = df_total[df_total['연령'].isin(ages)]
        line_data = filtered_df.groupby(['커리큘럼', '연령'])['회원수'].sum().reset_index()
        fig = px.line(
            line_data, x='커리큘럼', y='회원수', color='연령',
            markers=True, title="단계별 회원수 변화"
        )
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("과정별 월간 추이")
    trend_data = df_total.groupby(['월', '과정그룹'])['회원수'].sum().reset_index()
    fig = px.line(
        trend_data, x='월', y='회원수', color='과정그룹',
        markers=True, title="월별 과정 등록 추이"
    )
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("월별 회원 구성비 변화")
    bar_data = df_total.groupby(['월', '연령'])['회원수'].sum().reset_index()
    fig = px.bar(
        bar_data, x='월', y='회원수', color='연령',
        title="월별 연령 구성 비율", text_auto=True
    )
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)