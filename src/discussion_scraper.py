import os
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
from dotenv import load_dotenv
from collections import Counter
import re
from langdetect import detect
from textblob import TextBlob

# .env 파일 로드
load_dotenv()

class SteamDiscussionScraper:
    def __init__(self, app_id):
        self.app_id = app_id
        self.api_key = os.getenv('STEAM_API_KEY')
        self.base_url = f"https://steamcommunity.com/app/{app_id}/discussions/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    def get_discussion_page(self, page=1):
        try:
            url = f"{self.base_url}?l=korean&fp={page}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"페이지 요청 중 오류: {e}")
            return None

    def parse_discussion_topics(self, soup):
        discussions = []
        if not soup:
            return discussions

        topics = soup.find_all('div', class_='forum_topic')
        print(f"찾은 토픽 수: {len(topics)}")

        for topic in topics:
            try:
                # 제목 찾기
                title_div = topic.find('div', class_='forum_topic_name')
                title = title_div.text.strip() if title_div else ""

                # URL 찾기
                link = topic.find('a', class_='forum_topic_overlay')
                url = link.get('href', '') if link else ""

                # 댓글 수 찾기
                reply_count = 0
                reply_div = topic.find('div', class_='forum_topic_reply_count')
                if reply_div:
                    reply_text = reply_div.text.strip()
                    numbers = re.findall(r'\d+', reply_text)
                    if numbers:
                        reply_count = int(numbers[0])

                # 작성자 찾기
                author_div = topic.find('div', class_='forum_topic_op')
                author = author_div.text.strip() if author_div else ""

                # 날짜 찾기
                date = ""
                lastpost_div = topic.find('div', class_='forum_topic_lastpost')
                if lastpost_div:
                    date = lastpost_div.get('title', '')

                discussions.append({
                    'title': title,
                    'url': url,
                    'reply_count': reply_count,
                    'author': author,
                    'date': date,
                    'content': '',  # 본문은 나중에 채워질 예정
                    'comments': []  # 댓글은 나중에 채워질 예정
                })

            except Exception as e:
                print(f"토픽 파싱 중 오류 발생: {e}")
                continue

        return discussions

    def get_discussion_content(self, url):
        """토론 게시글의 본문 내용과 미디어 정보 가져오기"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 본문 내용 찾기
            content = ""
            media_info = {
                'image_count': 0,
                'video_count': 0,
                'media_links': []
            }
            
            forum_op = soup.find('div', class_='forum_op')
            if forum_op:
                # 텍스트 내용
                content_div = forum_op.find('div', class_='content')
                if content_div:
                    content = content_div.get_text(strip=True)
                
                # 이미지 수 카운트
                images = forum_op.find_all('img')
                media_info['image_count'] = len([img for img in images 
                                               if img.get('src', '').endswith(('.gif', '.png', '.jpg', '.jpeg'))])
                
                # 동영상 수 카운트
                videos = forum_op.find_all(['video', 'iframe'])
                media_info['video_count'] = len(videos)
                
                # 미디어 링크 수집
                for media in images + videos:
                    src = media.get('src', '')
                    if src:
                        media_type = 'video' if media.name in ['video', 'iframe'] else 'image'
                        media_info['media_links'].append({
                            'type': media_type,
                            'url': src
                        })
            
            # 댓글 찾기
            comments = []
            comment_divs = soup.find_all('div', class_='commentthread_comment responsive_body_text')
            
            for comment in comment_divs:
                try:
                    author_div = comment.find('div', class_='commentthread_comment_author')
                    author = author_div.find('a', class_='commentthread_author_link').text.strip() if author_div else "Unknown"
                    
                    content_div = comment.find('div', class_='commentthread_comment_text')
                    comment_content = content_div.get_text(strip=True) if content_div else ""
                    
                    date_div = comment.find('span', class_='commentthread_comment_timestamp')
                    date = date_div.text.strip() if date_div else ""
                    
                    # 댓글의 미디어 수 카운트
                    comment_media = {
                        'image_count': 0,
                        'video_count': 0,
                        'media_links': []
                    }
                    
                    if content_div:
                        comment_images = content_div.find_all('img')
                        comment_videos = content_div.find_all(['video', 'iframe'])
                        
                        comment_media['image_count'] = len([img for img in comment_images 
                                                          if img.get('src', '').endswith(('.gif', '.png', '.jpg', '.jpeg'))])
                        comment_media['video_count'] = len(comment_videos)
                        
                        # 미디어 링크 수집
                        for media in comment_images + comment_videos:
                            src = media.get('src', '')
                            if src:
                                media_type = 'video' if media.name in ['video', 'iframe'] else 'image'
                                comment_media['media_links'].append({
                                    'type': media_type,
                                    'url': src
                                })
                    
                    comments.append({
                        'author': author,
                        'content': comment_content,
                        'date': date,
                        'media': comment_media
                    })
                    
                except Exception as e:
                    print(f"댓글 파싱 중 오류: {e}")
                    continue
            
            return {
                'content': content,
                'media': media_info,
                'comments': comments
            }
            
        except Exception as e:
            print(f"본문/댓글 조회 중 오류: {e}")
            return {'content': "", 'media': {'image_count': 0, 'video_count': 0, 'media_links': []}, 'comments': []}

    def analyze_keywords(self, df):
        """기본 키워드 분석 함수"""
        # 언어별 불용어 정의
        stop_words = {
            'en': set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                      'is', 'are', 'was', 'were', 'will', 'be', 'has', 'have', 'had']),
            'ko': set(['은', '는', '이', '가', '을', '를', '의', '에', '에서', '으로']),
            'zh': set(['的', '了', '和', '是', '就', '都', '而', '及', '與', '或']),
            'ru': set(['и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со'])
        }

        keywords = []
        language_stats = Counter()

        for _, row in df.iterrows():
            try:
                # 제목과 본문 결합
                text = f"{row['title']} {row['content']}"
                if not text.strip():
                    continue

                # 언어 감지
                try:
                    lang = detect(text)
                except:
                    lang = 'en'  # 기본값
                language_stats[lang] += 1

                # 단어 분리
                words = text.lower().split()
                
                # 불용어 제거 및 길이 필터링
                filtered_words = [w for w in words 
                                if len(w) > 2 and w not in stop_words.get(lang, set())]
                keywords.extend(filtered_words)

            except Exception as e:
                print(f"텍스트 처리 중 오류: {e}")
                continue

        # 키워드 빈도 계산
        keyword_freq = Counter(keywords).most_common(20)
        
        return {
            'keywords': keyword_freq,
            'languages': dict(language_stats)
        }

    def scrape_discussions(self, max_pages=5):
        all_discussions = []
        
        for page in range(1, max_pages + 1):
            print(f"\n=== 페이지 {page} 스크래핑 시작 ===")
            soup = self.get_discussion_page(page)
            discussions = self.parse_discussion_topics(soup)
            
            # 각 토론의 본문과 댓글 가져오기
            for discussion in discussions:
                try:
                    details = self.get_discussion_content(discussion['url'])
                    discussion['content'] = details['content']
                    discussion['comments'] = details['comments']
                    print(f"토론 '{discussion['title']}' 처리 완료")
                    time.sleep(1)  # 요청 간격 조절
                except Exception as e:
                    print(f"토론 상세 정보 가져오기 실패: {e}")
                    discussion['content'] = ""
                    discussion['comments'] = []
            
            all_discussions.extend(discussions)
            print(f"현재까지 수집된 토론 수: {len(all_discussions)}")
            time.sleep(2)

        return pd.DataFrame(all_discussions) 