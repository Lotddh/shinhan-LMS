import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import re

# 페이지 기본 설정 (initial_sidebar_state="expanded"로 시작)
st.set_page_config(page_title="신한대 LMS 대시보드", page_icon="🎓", layout="centered", initial_sidebar_state="expanded")

st.title("🎓 신한대학교 LMS 주차별 출석 요약")
st.caption("주차별 최종 출석 현황만 깔끔하게 확인하세요.")

# 세션 상태에 사이드바 상태 저장 변수 초기화
if 'sidebar_state' not in st.session_state:
    st.session_state['sidebar_state'] = 'expanded'

# 사이드바 로그인 폼
with st.sidebar:
    st.header("🔑 로그인 정보")
    user_id = st.text_input("Username (학번)", placeholder="20250000")
    user_pw = st.text_input("Password (비밀번호)", type="password", autocomplete="current-password")
    
    st.divider()
    # 온라인 출석 기록이 없는 과목 숨기기 옵션 (기본값: 체크됨)
    hide_all_upcoming = st.checkbox("온라인 출석 기록이 없는 과목 숨기기", value=True)
    
    submit_btn = st.button("수강 현황 불러오기", type="primary")

if submit_btn:
    if not user_id or not user_pw:
        st.warning("학번과 비밀번호를 모두 입력해주세요!")
    else:
        with st.spinner("신한대 사이버강의실 로그인 및 데이터 분석 중..."):
            try:
                session = requests.Session()
                login_url = "https://cyber.shinhan.ac.kr/login/index.php"
                payload = {'username': user_id, 'password': user_pw}
                
                # 1. 로그인 시도
                res = session.post(login_url, data=payload)
                
                # 2. 전체 수강 과목 목록 조회
                course_page_url = "https://cyber.shinhan.ac.kr/local/ubion/user/index.php"
                res = session.get(course_page_url)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                all_courses = []
                for a in soup.find_all('a'):
                    href = a.get('href', '')
                    text = a.get_text(strip=True)
                    if 'course/view.php?id=' in href and text:
                        if (text, href) not in all_courses and len(text) > 1:
                            all_courses.append((text, href))
                
                if not all_courses:
                    st.error("❌ 과목을 찾지 못했거나 로그인 정보가 올바르지 않습니다.")
                else:
                    st.session_state['session'] = session
                    st.session_state['all_courses'] = all_courses
                    st.success(f"총 {len(all_courses)}개 과목을 불러왔습니다.")
                    
                    # 로그인 및 데이터 조회가 성공하면 사이드바를 자동으로 접기 위해 새로고침 유도
                    st.rerun()

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# 데이터 조회가 끝난 상태라면 사이드바를 자동으로 닫기 상태로 전환
if 'all_courses' in st.session_state:
    # Streamlit 최신 버전에서 사이드바를 접는 UI Trick (st.markdown을 이용한 JS 주입 또는 상태 유지)
    # 모바일에서 로그인이 완료되면 사이드바가 거슬리지 않도록 안내 문구 추가
    pass