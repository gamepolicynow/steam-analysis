import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

class SteamReviewScraper:
    def __init__(self, app_id):
        self.app_id = app_id
        self.base_url = f"https://store.steampowered.com/appreviews/{app_id}"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def get_reviews(self, min_playtime=0, start_date=None, end_date=None, max_pages=5):
        reviews = []
        cursor = "*"
        min_playtime_minutes = min_playtime * 60
        
        print(f"검색 시작 - 게임 ID: {self.app_id}")
        print(f"검색 기간: {start_date} ~ {end_date}")
        print(f"최소 플레이타임: {min_playtime}시간")
        
        for page in range(max_pages):
            try:
                params = {
                    'json': 1,
                    'cursor': cursor,
                    'num_per_page': 100,
                    'filter': 'all',
                    'language': 'all',
                    'review_type': 'all',
                    'purchase_type': 'all',
                    'day_range': (end_date - start_date).days
                }
                
                response = requests.get(self.base_url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('success') or not data.get('reviews'):
                    print(f"페이지 {page+1}: 데이터 없음 또는 API 응답 실패")
                    break
                
                print(f"페이지 {page+1}: {len(data['reviews'])}개 리뷰 발견")
                
                for review in data['reviews']:
                    try:
                        timestamp = review.get('timestamp_created')
                        if not timestamp:
                            continue
                            
                        review_date = datetime.fromtimestamp(timestamp)
                        playtime = review['author'].get('playtime_forever', 0)
                        
                        if (start_date <= review_date <= end_date and 
                            playtime >= min_playtime_minutes):
                            
                            reviews.append({
                                'author': review['author'].get('steamid', 'Unknown'),
                                'playtime': playtime,
                                'content': review.get('review', ''),
                                'language': review.get('language', 'unknown'),
                                'timestamp': review_date,
                                'votes_up': review.get('votes_up', 0),
                                'votes_funny': review.get('votes_funny', 0),
                                'recommended': review.get('voted_up', False),
                                'comment_count': review.get('comment_count', 0)
                            })
                            
                    except Exception as e:
                        print(f"리뷰 처리 중 오류: {e}")
                        continue
                
                cursor = data.get('cursor', '')
                if not cursor:
                    print("더 이상 페이지가 없음")
                    break
                    
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                print(f"API 요청 중 오류: {e}")
                break
            except Exception as e:
                print(f"처리 중 오류: {e}")
                break
        
        df = pd.DataFrame(reviews)
        
        if df.empty:
            print("수집된 리뷰가 없습니다.")
            return pd.DataFrame(columns=[
                'author', 'playtime', 'content', 'language', 
                'timestamp', 'votes_up', 'votes_funny', 
                'recommended', 'comment_count'
            ])
        
        # 날짜 범위로 한 번 더 필터링
        df = df[
            (df['timestamp'] >= start_date) & 
            (df['timestamp'] <= end_date)
        ]
        
        print(f"\n최종 수집 결과:")
        print(f"- 총 리뷰 수: {len(df)}개")
        print(f"- 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"- 언어: {df['language'].unique().tolist()}")
        
        return df

    def analyze_reviews(self, df):
        """리뷰 분석 결과 반환"""
        if df.empty:
            return {
                'total_reviews': 0,
                'languages': {},
                'avg_playtime': 0,
                'avg_votes': 0,
                'total_comments': 0,
                'recommendations': {
                    'recommended': 0,
                    'not_recommended': 0,
                    'recommend_percent': 0
                }
            }
            
        # 추천 분석
        recommended_count = df['recommended'].sum()
        total_reviews = len(df)
        not_recommended_count = total_reviews - recommended_count
        recommend_percent = (recommended_count / total_reviews * 100) if total_reviews > 0 else 0
            
        analysis = {
            'total_reviews': total_reviews,
            'languages': df['language'].value_counts().to_dict(),
            'avg_playtime': df['playtime'].mean() / 60,  # 시간 단위로 변환
            'avg_votes': df['votes_up'].mean(),
            'total_comments': df['comment_count'].sum(),
            'recommendations': {
                'recommended': int(recommended_count),
                'not_recommended': int(not_recommended_count),
                'recommend_percent': round(recommend_percent, 1)
            }
        }
        return analysis 