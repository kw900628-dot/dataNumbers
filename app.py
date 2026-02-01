import streamlit as st
import pandas as pd
import plotly.express as px
import re
import io  # [중요] 파일 읽기 오류 해결을 위한 라이브러리

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
# 3. 데이터 처리 로직 (BytesIO로 완벽 해결)
# ---------------------------------------------------------
all_data = []
progress_bar = st.progress(0)
total_files = len(uploaded_files)

# 오류 디버깅을 위한 리스트
error_logs = []

for i, file in enumerate(uploaded_files):
    try:
        # [✨ 핵심 수정] 파일을 메모리(Bytes)로 먼저 읽어옵니다.
        # 이렇게 하면 '파일을 이미 다 읽어서 못 읽는다'는 오류가 절대 발생하지 않습니다.
        file_bytes = file.getvalue()
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes), engine='openpyxl')
        
        sheet_names = excel_file.sheet_names
        
        # 파일명에서 '월' 정보 미리 찾기
        file_month_match = re.search(r'(\d+)월', file.name)
        file_month = int(file_month_match.group(1)) if file_month_match else None
        
        for sheet_name in sheet_names:
            # 시트 이름 분석
            sheet_month_strict = re.search(r'(\d+)월', sheet_name)
            
            if sheet_month_strict:
                month = int(sheet_month_strict.group(1))
            elif file_month:
                month = file_month
            else:
                num_match = re.search(r'(\d+)', sheet_name)
                month = int(num_match.group(1)) if num_match else 1
            
            # [✨ 핵심 수정] 위에서 만든 excel_file 객체를 재사용
            df_temp = pd.read_excel(excel_file, sheet_name=sheet_name, index_col='커리큘럼')
            
            # 데이터가 비어있지 않은지 확인
            if not df_temp.empty:
                df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원 수')
                df_melted['월'] = month
                df_melted['과정 그룹'] = df_melted['커리큘럼'].str.split('과정').str[0] + '과정'
                all_data.append(df_melted)
            
    except Exception as e:
        error_msg = f"⚠️ '{file.name}' 처리 실패: {e}"
        st.toast(error_msg)
        error_logs.append(error_msg)

    progress_bar.progress((i + 1) / total_files)

# ---------------------------------------------------------
# 4. 데이터 병합 및 시각화 (오류 방지 코드 추가)
# ---------------------------------------------------------
if not all_data:
    st.error("❌ 처리할 수 있는 데이터가 없습니다.")
    if error_logs:
        with st.expander("오류 상세 내용 보기"):
            for log in error_logs:
                st.write(log)
    st.stop()

# 여기서 all_data가 비어있지 않음이 보장되므로 concat 오류가 나지 않습니다.
df_total = pd.concat(all_data, ignore_index=True)

# 정렬 및 카테고리화
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

tab1, tab2, tab3, tab4 = st.tabs(["🔥 연령별 선호도", "📉 이탈 분석", "🗓️ 시즌성", "👥 인구 변화"])

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

# [Tab 2] 이탈 분석
with tab2:
    st.subheader("커리큘럼별 회원 유지 현황")
    ages = st.multiselect("분석할 연령대", age_order, default=['미취학', '8', '성인'])
    if ages:
        filtered_df = df_total[df_total['연령'].isin(ages)]
        line_data = filtered_df.groupby(['커리큘럼', '연령'])['회원 수'].sum().reset_index()
        
        # 0인 데이터 숨기기
        total_by_age = line_data.groupby('연령')['회원 수'].sum()
        valid_ages = total_by_age[total_by_age > 0].index.tolist()
        final_line_data = line_data[line_data['연령'].isin(valid_ages)]
        
        if not final_line_data.empty:
            fig = px.line(final_line_data, x='커리큘럼', y='회원 수', color='연령', markers=True, color_discrete_map=age_color_map)
            st.plotly_chart(fig, use_container_width=True)

# [Tab 3] 시즌성 분석
with tab3:
    st.subheader("과정별 월간 추이")
    trend_data = df_total.groupby(['월', '과정 그룹'])['회원 수'].sum().reset_index()
    fig = px.line(trend_data, x='월', y='회원 수', color='과정 그룹', markers=True, color_discrete_map=process_color_map)
    fig.update_xaxes(tickvals=list(range(1, 13)), range=[0.5, 12.5], title_text="월 (Month)")
    st.plotly_chart(fig, use_container_width=True)

# [Tab 4] 인구 변화 분석
with tab4:
    st.subheader("월별 회원 구성비 변화")
    bar_data = df_total.groupby(['월', '연령'])['회원 수'].sum().reset_index()
    fig = px.bar(bar_data, x='월', y='회원 수', color='연령', text_auto=True, color_discrete_map=age_color_map)
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, use_container_width=True)