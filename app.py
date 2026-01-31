import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os
import platform

# ---------------------------------------------------------
# 1. 한글 폰트 및 그래프 설정
# ---------------------------------------------------------
if platform.system() == 'Darwin': # Mac
    plt.rc('font', family='AppleGothic')
elif platform.system() == 'Windows': # Windows
    plt.rc('font', family='Malgun Gothic')
else:
    plt.rc('font', family='NanumGothic')

plt.rcParams['axes.unicode_minus'] = False # 마이너스 깨짐 방지
sns.set_style("whitegrid") # 배경 스타일 설정

# ---------------------------------------------------------
# 2. 데이터 불러오기 및 전처리 (ETL)
# ---------------------------------------------------------
folder_path = './dummy_excel_files'
all_data = []

# 연령대 정렬 순서 정의 (그래프 정렬용)
age_order = ['미취학'] + list(range(8, 20)) + ['성인']
# 커리큘럼 정렬 순서 정의
curriculum_order = [f"{p}과정 {s}단계" for p in ['A', 'B', 'C', 'D'] for s in range(1, 5)]

print("📂 데이터를 불러오고 통합하는 중입니다...")

for month in range(1, 13):
    file_name = f"2025년_{month}월_회원수.xlsx"
    file_path = os.path.join(folder_path, file_name)
    
    if os.path.exists(file_path):
        # 엑셀 읽기 (첫 번째 컬럼을 인덱스로)
        df_temp = pd.read_excel(file_path, index_col='커리큘럼')
        
        # Wide Format -> Long Format 변환 (Melt)
        # (행: 커리큘럼, 열: 연령대) 구조를 (행: 커리큘럼, 연령대, 값) 구조로 변경
        df_melted = df_temp.reset_index().melt(id_vars='커리큘럼', var_name='연령', value_name='회원수')
        
        # 월 정보 추가
        df_melted['월'] = month
        
        # '과정' 컬럼 추출 (A과정 1단계 -> A) - 그룹 분석용
        df_melted['과정그룹'] = df_melted['커리큘럼'].str.split('과정').str[0]
        
        all_data.append(df_melted)

# 전체 데이터 하나로 합치기
df_total = pd.concat(all_data, ignore_index=True)

# 범주형 데이터 순서 지정 (그래프가 뒤죽박죽되지 않도록)
df_total['연령'] = df_total['연령'].astype(str) # 정렬을 위해 문자열로 통일
str_age_order = [str(x) for x in age_order] # 정렬 기준도 문자열로
df_total['연령'] = pd.Categorical(df_total['연령'], categories=str_age_order, ordered=True)
df_total['커리큘럼'] = pd.Categorical(df_total['커리큘럼'], categories=curriculum_order, ordered=True)

print(f"✅ 총 {len(df_total)}개의 데이터 행이 준비되었습니다.\n")


# =========================================================
# 분석 1. 연령대별 과정 선호도 (Heatmap)
#  - 전체 기간(1~12월) 합계 기준, 어떤 연령이 어떤 과정(A~D)에 많은가?
# =========================================================
plt.figure(figsize=(12, 8))

# 피벗 테이블: 인덱스=연령, 컬럼=과정그룹(A,B,C,D), 값=회원수 합계
pivot_heat = df_total.pivot_table(index='연령', columns='과정그룹', values='회원수', aggfunc='sum')

sns.heatmap(pivot_heat, annot=True, fmt='d', cmap='YlGnBu', linewidths=0.5)
plt.title('분석 1. 연령대별 과정 선호도 (연간 누적 합계)')
plt.ylabel('연령대')
plt.xlabel('과정 그룹')
plt.show()


# =========================================================
# 분석 2. 전체 커리큘럼 생존/이탈 분석 (Line Plot)
#  - A-1단계부터 D-4단계까지 회원 수가 어떻게 변하는가?
# =========================================================
plt.figure(figsize=(14, 6))

# 시각화 복잡도를 줄이기 위해 연령대를 그룹화 (선택 사항)
# 여기서는 원본 그대로 출력하되, 너무 많으므로 주요 연령만 보거나 전체를 흐리게 표현
sns.lineplot(data=df_total, x='커리큘럼', y='회원수', hue='연령', estimator='sum', errorbar=None, marker='o')

plt.title('분석 2. 상세 커리큘럼별 회원 유지 현황 (이탈 구간 확인)')
plt.xticks(rotation=45)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='연령')
plt.tight_layout()
plt.show()


# =========================================================
# 분석 3. 월별/과정별 시즌성 분석 (Time Series)
#  - A, B, C, D 과정별로 월별 회원수 추이 확인
# =========================================================
plt.figure(figsize=(12, 6))

# 월별, 과정그룹별 합계
monthly_trend = df_total.groupby(['월', '과정그룹'])['회원수'].sum().reset_index()

sns.lineplot(data=monthly_trend, x='월', y='회원수', hue='과정그룹', marker='s', linewidth=2)

plt.title('분석 3. 과정별 월간 회원수 추이 (시즌성 파악)')
plt.xticks(range(1, 13))
plt.grid(True, linestyle='--', alpha=0.6)
plt.show()


# =========================================================
# 분석 4. 월별 연령 구성비 변화 (Stacked Bar)
#  - 우리 학원은 고령화되고 있는가, 젊어지고 있는가?
# =========================================================
# 월별, 연령별 합계 계산
pivot_demography = df_total.pivot_table(index='월', columns='연령', values='회원수', aggfunc='sum')

# 비율(%)로 변환
pivot_demography_pct = pivot_demography.div(pivot_demography.sum(axis=1), axis=0) * 100

# 그래프 그리기
ax = pivot_demography_pct.plot(kind='bar', stacked=True, figsize=(12, 7), colormap='Spectral')

plt.title('분석 4. 월별 회원 연령 구성비 변화 (Demographic Shift)')
plt.xlabel('월')
plt.ylabel('구성비 (%)')
plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', title='연령')
plt.xticks(rotation=0)

# 막대 안에 % 글자 넣기 (가독성을 위해 3% 이상만 표시)
for c in ax.containers:
    labels = [f'{v.get_height():.1f}%' if v.get_height() > 3 else '' for v in c]
    ax.bar_label(c, labels=labels, label_type='center', fontsize=8)

plt.tight_layout()
plt.show()