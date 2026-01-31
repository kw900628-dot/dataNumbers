import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 함수
# -----------------------------------------------------------------------------
st.set_page_config(page_title="중국어 학습 통합 분석", layout="wide")

def validate_columns(df):
    required_columns = ['User_ID', 'Event_Name', 'Timestamp', 'Course_Type']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"❌ 데이터 구조 오류: {', '.join(missing)} 컬럼이 없습니다.")
        st.stop()
    return True

@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file)
        validate_columns(df)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        return df
    except Exception as e:
        st.error(f"파일 로드 오류: {e}")
        st.stop()

# -----------------------------------------------------------------------------
# 2. 사이드바 (파일 업로드 & 필터)
# -----------------------------------------------------------------------------
st.sidebar.title("📂 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("CSV 파일 업로드", type=['csv'])

if uploaded_file is not None:
    df_raw = load_data(uploaded_file)
    st.sidebar.success("✅ 파일 적용됨")
else:
    try:
        df_raw = load_data('learning_log_retention.csv') # 기본 파일명
        st.sidebar.info("📌 기본 예시 데이터 사용 중")
    except:
        st.warning("⚠️ CSV 파일을 업로드해주세요.")
        st.stop()

st.sidebar.markdown("---")
st.sidebar.header("🔍 날짜 필터")
min_date = df_raw['Timestamp'].min().date()
max_date = df_raw['Timestamp'].max().date()
start_date = st.sidebar.date_input("시작일", min_date)
end_date = st.sidebar.date_input("종료일", max_date)

mask = (df_raw['Timestamp'].dt.date >= start_date) & (df_raw['Timestamp'].dt.date <= end_date)
df = df_raw.loc[mask]
st.sidebar.write(f"분석 대상: {len(df)}건")

# -----------------------------------------------------------------------------
# 3. 메인 대시보드
# -----------------------------------------------------------------------------
st.title("🇨🇳 유아 중국어 학습 행동 분석 리포트")
st.markdown(f"**분석 기간:** {start_date} ~ {end_date}")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔻 퍼널(이탈)", "⏱️ 학습시간", "🚀 진입속도", "🔥 골든타임", "📅 재방문율"
])

# =============================================================================
# [TAB 1] 퍼널 분석 + 인사이트
# =============================================================================
with tab1:
    st.subheader("단계별 이탈률 분석")
    
    # 지표 계산
    cnt_a_start = df[df['Event_Name'] == 'aCourse_start']['User_ID'].nunique()
    cnt_a_end = df[df['Event_Name'] == 'aCourse_complete']['User_ID'].nunique()
    cnt_b_start = df[df['Event_Name'] == 'bCourse_start']['User_ID'].nunique()
    
    # 그래프
    metrics = {
        '1_A시작': cnt_a_start, '2_A완료': cnt_a_end, 
        '3_B시작': cnt_b_start, 
        '4_B완료': df[df['Event_Name'] == 'bCourse_complete']['User_ID'].nunique(),
        '5_C시작': df[df['Event_Name'] == 'cCourse_start']['User_ID'].nunique(),
        '6_C완료': df[df['Event_Name'] == 'cCourse_complete']['User_ID'].nunique(),
    }
    
    fig = go.Figure(go.Funnel(
        y = list(metrics.keys()), x = list(metrics.values()),
        textinfo = "value+percent initial",
        marker = {"color": ["#6366f1", "#4f46e5", "#10b981", "#059669", "#f59e0b", "#d97706"]}
    ))
    st.plotly_chart(fig, use_container_width=True)
    
    # 🤖 [인사이트 자동 분석]
    st.markdown("### 🤖 AI 분석 코멘트")
    col1, col2 = st.columns(2)
    
    # A->B 전환율 분석
    rate_ab = 0
    if cnt_a_end > 0:
        rate_ab = (cnt_b_start / cnt_a_end) * 100
        
    with col1:
        st.metric("A완료 ➔ B진입 전환율", f"{rate_ab:.1f}%")
    with col2:
        if rate_ab < 50:
            st.error("⚠️ **위험:** A코스를 끝낸 아이들의 절반 이상이 B코스로 넘어가지 않습니다. '다음 학습 유도 버튼'이 잘 보이는지 확인하세요.")
        elif rate_ab < 80:
            st.warning("⚠️ **주의:** B코스 진입률이 다소 낮습니다(80% 미만). B코스의 흥미 요소를 강조해 보세요.")
        else:
            st.success("✅ **양호:** 대부분의 아이들이 자연스럽게 다음 코스로 넘어가고 있습니다.")

# =============================================================================
# [TAB 2] 학습 시간 + 인사이트
# =============================================================================
with tab2:
    st.subheader("코스별 학습 소요 시간 분포")
    
    df_start = df[df['Event_Name'].str.contains('start')].copy()
    df_end = df[df['Event_Name'].str.contains('complete')].copy()
    merged = pd.merge(df_start, df_end, on=['User_ID', 'Course_Type'], suffixes=('_start', '_end'))
    
    if not merged.empty:
        merged['duration_min'] = (merged['Timestamp_end'] - merged['Timestamp_start']).dt.total_seconds() / 60
        
        # 그래프
        fig = px.histogram(merged, x="duration_min", color="Course_Type", barmode="overlay", nbins=20)
        st.plotly_chart(fig, use_container_width=True)
        
        # 🤖 [인사이트 자동 분석]
        st.markdown("### 🤖 AI 분석 코멘트")
        
        # 평균 시간 계산
        avg_time = merged.groupby('Course_Type')['duration_min'].mean().round(1)
        
        # 과도하게 짧은 학습(1분 미만) 비율 계산
        short_learning = merged[merged['duration_min'] < 1].groupby('Course_Type').size()
        total_learning = merged.groupby('Course_Type').size()
        
        c1, c2, c3 = st.columns(3)
        for i, (course, col) in enumerate(zip(['a', 'b', 'c'], [c1, c2, c3])):
            if course in avg_time:
                with col:
                    st.metric(f"{course.upper()} 코스 평균 시간", f"{avg_time[course]}분")
                    
                    # 광클족 비율 확인
                    ratio_short = 0
                    if course in short_learning:
                        ratio_short = (short_learning[course] / total_learning[course]) * 100
                    
                    if ratio_short > 10:
                        st.caption(f"🚨 **광클 경고:** {ratio_short:.1f}%가 1분 미만으로 넘겼습니다.")
                    else:
                        st.caption("✅ 학습 시간이 정상적입니다.")
    else:
        st.info("데이터 부족")

# =============================================================================
# [TAB 3] 진입 속도
# =============================================================================
with tab3:
    st.subheader("다음 코스로 넘어가는 데 걸린 시간 (속도 비교)")
    
    # 1. 데이터 준비 (A->B)
    a_end = df[df['Event_Name'] == 'aCourse_complete'][['User_ID', 'Timestamp']]
    b_start = df[df['Event_Name'] == 'bCourse_start'][['User_ID', 'Timestamp']]
    ab_merge = pd.merge(a_end, b_start, on='User_ID', suffixes=('_end', '_start'))
    ab_merge['gap_sec'] = (ab_merge['Timestamp_start'] - ab_merge['Timestamp_end']).dt.total_seconds()
    ab_merge['Type'] = 'A ➔ B 구간'
    
    # 2. 데이터 준비 (B->C) - 여기가 추가된 부분입니다!
    b_end = df[df['Event_Name'] == 'bCourse_complete'][['User_ID', 'Timestamp']]
    c_start = df[df['Event_Name'] == 'cCourse_start'][['User_ID', 'Timestamp']]
    bc_merge = pd.merge(b_end, c_start, on='User_ID', suffixes=('_end', '_start'))
    bc_merge['gap_sec'] = (bc_merge['Timestamp_start'] - bc_merge['Timestamp_end']).dt.total_seconds()
    bc_merge['Type'] = 'B ➔ C 구간'
    
    # 3. 데이터 합치기
    combined_df = pd.concat([ab_merge, bc_merge])
    
    if not combined_df.empty:
        # 4. 시각화 (박스 플롯으로 비교)
        fig = px.box(
            combined_df, x="Type", y="gap_sec", 
            color="Type",
            points="outliers", 
            title="코스 간 진입 대기 시간 비교 (초 단위)",
            labels={'gap_sec': '대기 시간(초)', 'Type': '구간'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 5. 🤖 [인사이트 자동 분석]
        st.markdown("### 🤖 AI 분석 코멘트")
        
        # 구간별 중위값(Median) 계산
        median_ab = ab_merge['gap_sec'].median() if not ab_merge.empty else 0
        median_bc = bc_merge['gap_sec'].median() if not bc_merge.empty else 0
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("A ➔ B 평균 대기", f"{median_ab:.0f}초")
        with col2:
            st.metric("B ➔ C 평균 대기", f"{median_bc:.0f}초")
            
        # 가속도 분석 (B->C가 더 빨라졌는지?)
        if not ab_merge.empty and not bc_merge.empty:
            if median_bc < median_ab:
                st.success("🚀 **가속 효과:** 학습이 진행될수록 다음 코스로 넘어가는 속도가 빨라지고 있습니다! 아이들이 재미를 느꼈다는 신호입니다.")
            elif median_bc > median_ab * 1.5:
                st.warning("🐢 **피로 누적:** B코스를 끝내고 C코스로 넘어갈 때 시간이 훨씬 오래 걸립니다. B코스 내용이 너무 어렵거나 길지 않은지 점검해 보세요.")
            else:
                st.info("⚖️ **일정한 페이스:** 아이들이 꾸준한 속도로 학습을 이어나가고 있습니다.")
    else:
        st.info("다음 코스로 진입한 데이터가 충분하지 않습니다.")

# =============================================================================
# [TAB 4] 골든타임 (히트맵)
# =============================================================================
with tab4:
    st.subheader("요일 및 시간대별 접속 집중도")
    df['Day'] = df['Timestamp'].dt.day_name()
    df['Hour'] = df['Timestamp'].dt.hour
    
    # 요일 정렬
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['Day'] = pd.Categorical(df['Day'], categories=days, ordered=True)
    
    heat_data = df.groupby(['Day', 'Hour']).size().reset_index(name='Count')
    
    if not heat_data.empty:
        pivot = heat_data.pivot(index='Day', columns='Hour', values='Count').fillna(0)
        fig = px.imshow(pivot, color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True)
        
        # 🤖 [인사이트] 가장 핫한 시간 찾기
        st.markdown("### 🤖 AI 분석 코멘트")
        max_row = heat_data.loc[heat_data['Count'].idxmax()]
        st.info(f"💡 **골든 타임 발견:** 우리 아이들은 **{max_row['Day']} {max_row['Hour']}시**에 가장 많이 접속합니다. 이때 푸시 알림을 보내보세요!")

# =============================================================================
# [TAB 5] 재방문율
# =============================================================================
with tab5:
    st.subheader("가입 후 N일차 재방문율 (Retention)")
    
    first_login = df.groupby('User_ID')['Timestamp'].min().dt.floor('D').reset_index()
    first_login.columns = ['User_ID', 'First_Date']
    df['Date'] = df['Timestamp'].dt.floor('D')
    
    retention = pd.merge(df, first_login, on='User_ID')
    retention['Day_Diff'] = (retention['Date'] - retention['First_Date']).dt.days
    
    cohort = retention.groupby('Day_Diff')['User_ID'].nunique().reset_index()
    
    if not cohort.empty and (cohort['Day_Diff'] == 0).any():
        total = cohort[cohort['Day_Diff'] == 0]['User_ID'].values[0]
        cohort['Rate'] = (cohort['User_ID'] / total) * 100
        
        fig = px.line(cohort, x='Day_Diff', y='Rate', markers=True)
        fig.update_yaxes(range=[0, 110])
        fig.update_xaxes(range=[-0.5, max(cohort['Day_Diff'].max(), 7)])
        st.plotly_chart(fig, use_container_width=True)
        
        # 🤖 [인사이트]
        st.markdown("### 🤖 AI 분석 코멘트")
        col1, col2, col3 = st.columns(3)
        
        # Day 1, 3, 7 리텐션 찾기 함수
        def get_rate(day):
            row = cohort[cohort['Day_Diff'] == day]
            return f"{row['Rate'].values[0]:.1f}%" if not row.empty else "-"
            
        col1.metric("Day 1 (익일) 생존율", get_rate(1))
        col2.metric("Day 3 생존율", get_rate(3))
        col3.metric("Day 7 생존율", get_rate(7))
        
        st.caption("※ Day 1 생존율이 40% 이상이면 매우 건전한 교육 앱입니다.")
    else:
        st.warning("데이터 부족")