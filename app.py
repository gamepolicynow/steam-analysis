import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict

# import 경로 수정
from scraper.discussion_scraper import SteamDiscussionScraper
from scraper.review_scraper import SteamReviewScraper

def check_password():
    """비밀번호 확인 함수"""
    def password_entered():
        """비밀번호 검증"""
        if st.session_state["password"] == "1125":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 비밀번호 삭제
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 첫 화면: 비밀번호 입력 요청
        st.text_input(
            "비밀번호를 입력하세요", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    
    elif not st.session_state["password_correct"]:
        # 비밀번호가 틀린 경우
        st.text_input(
            "비밀번호가 틀렸습니다. 다시 입력하세요", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    
    return True

def create_directories():
    """필요한 디렉토리 생성"""
    directories = [
        'data/raw',
        'src/scraper',
        'src/ui'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def display_media_info(media_info):
    """미디어 정보 표시 함수"""
    if media_info['image_count'] > 0 or media_info['video_count'] > 0:
        st.write("**📎 첨부 파일:**")
        if media_info['image_count'] > 0:
            st.write(f"- 이미지 {media_info['image_count']}개")
        if media_info['video_count'] > 0:
            st.write(f"- 동영상 {media_info['video_count']}개")
        
        with st.expander("미디어 링크 보기"):
            for link in media_info['media_links']:
                st.write(f"- [{link['type']}]({link['url']})")

def create_daily_review_chart(df):
    """일별 리뷰 카운트 차트 생성"""
    daily_counts = df.groupby(df['timestamp'].dt.date).size().reset_index()
    daily_counts.columns = ['date', 'count']
    
    fig = px.line(daily_counts, 
                  x='date', 
                  y='count',
                  title='일별 리뷰 등록 추이',
                  labels={'date': '날짜', 'count': '리뷰 수'})
    
    fig.update_layout(showlegend=True, 
                     xaxis_title="날짜",
                     yaxis_title="리뷰 수")
    
    return fig

def create_daily_sentiment_chart(df):
    """일별 긍정/부정 비율 차트 생성"""
    daily_sentiment = df.groupby(df['timestamp'].dt.date)['recommended'].agg(['sum', 'size']).reset_index()
    daily_sentiment['positive_ratio'] = (daily_sentiment['sum'] / daily_sentiment['size'] * 100).round(1)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_sentiment['timestamp'],
        y=daily_sentiment['positive_ratio'],
        mode='lines+markers',
        name='긍정 리뷰 비율',
        hovertemplate='날짜: %{x}<br>긍정 비율: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='일별 긍정/부정 리뷰 비율 추이',
        xaxis_title='날짜',
        yaxis_title='긍정 리뷰 비율 (%)',
        yaxis=dict(range=[0, 100])
    )
    
    return fig

def create_language_sentiment_chart(df):
    """언어별 긍정/부정 비율 차트 생성"""
    lang_sentiment = df.groupby('language').agg({
        'recommended': ['count', 'sum']
    }).reset_index()
    
    lang_sentiment.columns = ['language', 'total', 'positive']
    lang_sentiment['negative'] = lang_sentiment['total'] - lang_sentiment['positive']
    lang_sentiment['positive_ratio'] = (lang_sentiment['positive'] / lang_sentiment['total'] * 100).round(1)
    
    # 리뷰 수가 많은 상위 10개 언어만 선택
    lang_sentiment = lang_sentiment.nlargest(10, 'total')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='긍정 리뷰',
        x=lang_sentiment['language'],
        y=lang_sentiment['positive'],
        marker_color='#1e88e5'
    ))
    
    fig.add_trace(go.Bar(
        name='부정 리뷰',
        x=lang_sentiment['language'],
        y=lang_sentiment['negative'],
        marker_color='red'
    ))
    
    fig.update_layout(
        title='언어별 긍정/부정 리뷰 분포 (상위 10개 언어)',
        barmode='stack',
        xaxis_title='언어',
        yaxis_title='리뷰 수',
        hovermode='x'
    )
    
    return fig

def create_daily_review_tables(df):
    """일별 리뷰 데이터 테이블 생성"""
    
    # 1. 일별 리뷰 카운트 테이블
    daily_counts = df.groupby(df['timestamp'].dt.date).size().reset_index()
    daily_counts.columns = ['날짜', '리뷰 수']
    
    # 2. 일별 긍정/부정 비율 테이블
    daily_sentiment = df.groupby(df['timestamp'].dt.date).agg({
        'recommended': ['count', 'sum']
    }).reset_index()
    daily_sentiment.columns = ['날짜', '전체 리뷰 수', '긍정 리뷰 수']
    daily_sentiment['부정 리뷰 수'] = daily_sentiment['전체 리뷰 수'] - daily_sentiment['긍정 리뷰 수']
    daily_sentiment['긍정 비율'] = (daily_sentiment['긍정 리뷰 수'] / daily_sentiment['전체 리뷰 수'] * 100).round(1)
    daily_sentiment['긍정 비율'] = daily_sentiment['긍정 비율'].astype(str) + '%'
    
    # 3. 언어별 리뷰 분포 테이블
    lang_sentiment = df.groupby('language').agg({
        'recommended': ['count', 'sum']
    }).reset_index()
    lang_sentiment.columns = ['언어', '전체 리뷰 수', '긍정 리뷰 수']
    lang_sentiment['부정 리뷰 수'] = lang_sentiment['전체 리뷰 수'] - lang_sentiment['긍정 리뷰 수']
    lang_sentiment['긍정 비율'] = (lang_sentiment['긍정 리뷰 수'] / lang_sentiment['전체 리뷰 수'] * 100).round(1)
    lang_sentiment['긍정 비율'] = lang_sentiment['긍정 비율'].astype(str) + '%'
    lang_sentiment = lang_sentiment.sort_values('전체 리뷰 수', ascending=False)
    
    return daily_counts, daily_sentiment, lang_sentiment

def main():
    if not check_password():
        st.stop()  # 비밀번호가 맞지 않으면 여기서 실행 중단
        
    # 페이지 설정
    st.set_page_config(
        page_title="Steam 데이터 분석기",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS 스타일 적용
    st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1e88e5;
            text-align: center;
            margin-bottom: 2rem;
        }
        .sub-header {
            font-size: 1.8rem;
            color: #424242;
            margin-top: 2rem;
        }
        .section-header {
            font-size: 1.3rem;
            color: #2196f3;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
        }
        .metric-container {
            background-color: #f5f5f5;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }
        .chart-container {
            background-color: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        .stButton>button {
            width: 100%;
            background-color: #1e88e5;
            color: white;
        }
        .stButton>button:hover {
            background-color: #1565c0;
        }
        .sidebar-info {
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # 헤더
    st.markdown('<h1 class="main-header">🎮 Steam 데이터 분석기</h1>', unsafe_allow_html=True)

    # 사이드바 설정
    with st.sidebar:
        st.markdown('<h2 class="sub-header">설정</h2>', unsafe_allow_html=True)
        
        # 게임 ID 입력
        app_id = st.text_input(
            "Steam 게임 ID",
            value="413150",
            help="Steam 스토어 URL의 app/[숫자] 부분을 입력하세요"
        )
        
        st.markdown('<div class="sidebar-info">💡 예시: store.steampowered.com/app/413150</div>', 
                   unsafe_allow_html=True)
        
        st.markdown('<h3 class="section-header">데이터 수집 옵션</h3>', 
                   unsafe_allow_html=True)
        
        collect_discussions = st.checkbox("토론 데이터 수집", value=True)
        collect_reviews = st.checkbox("리뷰 데이터 수집", value=False)
        
        if collect_reviews:
            st.markdown("##### 리뷰 검색 조건")
            min_playtime = st.number_input(
                "최소 플레이 시간 (시간)",
                min_value=0,
                value=2,
                help="지정한 시간 이상 플레이한 유저의 리뷰만 수집합니다"
            )
            
            date_option = st.radio(
                "검색 기간 설정",
                options=["기간 선택", "직접 입력"]
            )
            
            # 날짜 계산 로직
            today = datetime.now()
            
            if date_option == "기간 선택":
                date_range = st.selectbox(
                    "기간",
                    options=["최근 1일", "최근 1주일", "최근 1개월", "최근 3개월", "최근 6개월", "최근 1년"]
                )
                
                # 선택된 기간에 따라 날짜 계산
                if date_range == "최근 1일":
                    days_ago = 1
                elif date_range == "최근 1주일":
                    days_ago = 7
                elif date_range == "최근 1개월":
                    days_ago = 30
                elif date_range == "최근 3개월":
                    days_ago = 90
                elif date_range == "최근 6개월":
                    days_ago = 180
                else:  # 최근 1년
                    days_ago = 365
                    
                start_date = today - timedelta(days=days_ago)
                end_date = today
                
            else:  # 직접 입력
                col1, col2 = st.columns(2)
                with col1:
                    start_date = datetime.combine(
                        st.date_input("시작일"), 
                        datetime.min.time()
                    )
                with col2:
                    end_date = datetime.combine(
                        st.date_input("종료일"), 
                        datetime.max.time()
                    )

            # 날짜 정보 표시
            st.markdown(
                f'<div class="sidebar-info">📅 검색 기간: {start_date.strftime("%Y-%m-%d")} ~ {end_date.strftime("%Y-%m-%d")}</div>', 
                unsafe_allow_html=True
            )

    # 메인 컨텐츠
    if st.button("데이터 수집 및 분석 시작", type="primary"):
        with st.spinner("데이터 수집 및 분석 중..."):
            try:
                # 토론 데이터 수집
                if collect_discussions:
                    discussion_scraper = SteamDiscussionScraper(app_id)
                    discussions_df = discussion_scraper.scrape_discussions(
                        max_pages=max_pages_discussions)
                    discussion_analysis = discussion_scraper.analyze_keywords(discussions_df)
                
                # 리뷰 데이터 수집
                if collect_reviews:
                    review_scraper = SteamReviewScraper(app_id)
                    reviews_df = review_scraper.get_reviews(
                        min_playtime=min_playtime,
                        start_date=start_date,
                        end_date=end_date,
                        max_pages=10
                    )
                    review_analysis = review_scraper.analyze_reviews(reviews_df)
                    
                    # 수집 결과 요약 표시
                    period_text = f"{date_range}" if date_option == "기간 선택" else "직접 입력 기간"
                    st.info(f"""
                    📊 리뷰 수집 결과:
                    - 검색 기간: {period_text} ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})
                    - 최소 플레이 시간: {min_playtime}시간 이상
                    - 수집된 리뷰 수: {len(reviews_df)}개
                    """)
                
                # 결과 표시
                st.markdown('<h2 class="sub-header">분석 결과</h2>', unsafe_allow_html=True)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    if collect_discussions:
                        st.subheader("수집된 토론 목록")
                        for idx, row in discussions_df.iterrows():
                            with st.expander(f"📝 {row['title']} (댓글 {len(row['comments'])}개)"):
                                st.write("**작성자:** " + row['author'])
                                st.write("**작성일:** " + row['date'])
                                st.write("\n**📌 본문 내용:**")
                                st.write(row['content'] if row['content'] else "본문 내용 없음")
                                
                                if row['comments']:
                                    st.write("\n**💬 댓글:**")
                                    for comment in row['comments']:
                                        st.write(f"- **{comment['author']}** ({comment['date']})")
                                        st.write(f"  {comment['content']}")
                                
                                st.write("\n**🔗 URL:**")
                                st.write(row['url'])
                    
                    if collect_reviews:
                        st.subheader("수집된 리뷰 목록")
                        for idx, row in reviews_df.iterrows():
                            with st.expander(f"💭 리뷰 (작성자: {row['author']})"):
                                st.write(f"**작성일:** {row['timestamp']}")
                                st.write(f"**플레이 시간:** {row['playtime']/60:.1f}시간")
                                st.write(f"**언어:** {row['language']}")
                                st.write("\n**리뷰 내용:**")
                                st.write(row['content'])
                                st.write(f"👍 {row['votes_up']} | 😄 {row['votes_funny']}")
                
                with col2:
                    st.subheader("분석 결과")
                    
                    if collect_discussions:
                        st.write("### 토론 분석")
                        # 언어 분포
                        st.write("### 언어 분포")
                        languages = discussion_analysis['languages']
                        for lang, count in languages.items():
                            st.write(f"- {lang}: {count}개 게시글")
                        
                        # 주요 키워드
                        st.write("\n### 주요 키워드")
                        keywords = discussion_analysis['keywords']
                        for word, count in keywords:
                            st.write(f"- {word}: {count}회 등장")
                    
                    if collect_reviews:
                        st.write("### 리뷰 분석")
                        
                        # 추천 현황을 시각���으로 표시
                        rec_data = review_analysis['recommendations']
                        st.write("#### 추천 현황")
                        
                        # 추천 비율을 프로그레스 바로 표시
                        st.progress(rec_data['recommend_percent'] / 100)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("긍정적 리뷰", f"{rec_data['recommended']}개")
                        with col2:
                            st.metric("부정적 리뷰", f"{rec_data['not_recommended']}개")
                        with col3:
                            st.metric("긍정적 리뷰 비율", f"{rec_data['recommend_percent']}%")
                        
                        # 차트 표시
                        st.write("#### 리뷰 추이 분석")
                        
                        # 데이터 테이블 생성
                        daily_counts_table, daily_sentiment_table, lang_sentiment_table = create_daily_review_tables(reviews_df)
                        
                        # 1. 일별 리뷰 등록 추이
                        st.write("##### 일별 리뷰 등록 추이")
                        st.plotly_chart(create_daily_review_chart(reviews_df), use_container_width=True)
                        with st.expander("일별 리뷰 수 상세 데이터"):
                            st.dataframe(
                                daily_counts_table.style.format({'날짜': lambda x: x.strftime('%Y-%m-%d')}),
                                hide_index=True
                            )
                        
                        # 2. 일별 긍정/부정 비율 추이
                        st.write("##### 일별 긍정/부정 리뷰 비율 추이")
                        st.plotly_chart(create_daily_sentiment_chart(reviews_df), use_container_width=True)
                        with st.expander("일별 긍정/부정 비율 상세 데이터"):
                            st.dataframe(
                                daily_sentiment_table.style.format({'날짜': lambda x: x.strftime('%Y-%m-%d')}),
                                hide_index=True
                            )
                        
                        # 3. 언어별 리뷰 분석
                        st.write("##### 언어별 긍정/부정 리뷰 분포")
                        st.plotly_chart(create_language_sentiment_chart(reviews_df), use_container_width=True)
                        with st.expander("언어별 리뷰 분포 상세 데이터"):
                            st.dataframe(
                                lang_sentiment_table,
                                hide_index=True
                            )
                        
                        # 기존 분석 결과도 표시
                        st.write(f"총 리뷰 수: {review_analysis['total_reviews']}개")
                        st.write(f"평균 플레이 시간: {review_analysis['avg_playtime']:.1f}시간")
                        st.write(f"평균 추천 수: {review_analysis['avg_votes']:.1f}")
                        
                        st.write("\n**언어별 리뷰 수:**")
                        for lang, count in review_analysis['languages'].items():
                            st.write(f"- {lang}: {count}개")
                
                # CSV 다운로드 버튼들
                if collect_discussions:
                    st.download_button(
                        label="토론 데이터 CSV 다운로드",
                        data=discussions_df.to_csv(index=False).encode('utf-8-sig'),
                        file_name=f'steam_discussions_{app_id}_{datetime.now().strftime("%Y%m%d")}.csv',
                        mime='text/csv'
                    )
                
                if collect_reviews:
                    st.download_button(
                        label="리뷰 데이터 CSV 다운로드",
                        data=reviews_df.to_csv(index=False).encode('utf-8-sig'),
                        file_name=f'steam_reviews_{app_id}_{datetime.now().strftime("%Y%m%d")}.csv',
                        mime='text/csv'
                    )
            
            except Exception as e:
                st.error(f"오류 발생: {e}")

if __name__ == "__main__":
    main() 