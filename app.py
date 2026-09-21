import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pandas as pd
import re

# 페이지 기본 설정
st.set_page_config(page_title="신한대 LMS 대시보드", page_icon="🎓", layout="centered")

st.title("🎓 신한대학교 LMS 주차별 출석 요약")
st.caption("주차별 최종 출석 현황만 깔끔하게 확인하세요.")

# 사이드바 로그인 폼
with st.sidebar:
    st.header("🔑 로그인 정보")
    user_id = st.text_input("Username (학번)", placeholder="20250000")
    user_pw = st.text_input("Password (비밀번호)", type="password", autocomplete="current-password")
    
    st.divider()
    # 예정/미열람만 있는 과목 숨기기 옵션 (기본값: 체크됨)
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

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

# 데이터 조회가 끝난 상태라면 과목 선택 멀티셀렉트와 요약표 출력
if 'all_courses' in st.session_state:
    session = st.session_state['session']
    all_courses = st.session_state['all_courses']
    
    course_titles = [title for title, _ in all_courses]
    
    st.divider()
    
    selected_titles = st.multiselect(
        "📌 조회할 과목을 선택/제거하세요 (기본값: 전체 선택)",
        options=course_titles,
        default=course_titles
    )
    
    if not selected_titles:
        st.info("선택된 과목이 없습니다. 위 선택창에서 확인하고 싶은 과목을 클릭해 주세요.")
    else:
        for title, course_url in all_courses:
            if title in selected_titles:
                c_res = session.get(course_url)
                c_soup = BeautifulSoup(c_res.text, 'html.parser')
                
                att_link = None
                for a_tag in c_soup.find_all('a'):
                    btn_text = a_tag.get_text(strip=True)
                    btn_href = a_tag.get('href', '')
                    if ("온라인출석부" in btn_text or "출석/수강현황" in btn_text or "ubattendance" in btn_href) and btn_href:
                        att_link = urljoin(course_url, btn_href)
                        break
                
                if att_link:
                    att_res = session.get(att_link)
                    att_soup = BeautifulSoup(att_res.text, 'html.parser')
                    tables = att_soup.find_all('table')
                    
                    summary_dict = {}
                    
                    if tables:
                        for table in tables:
                            table_str = str(table)
                            # 프로필/접속로그 표 스킵
                            if "휴대 전화" in table_str or "IP 주소" in table_str or "시작 시간" in table_str:
                                continue
                            
                            rows = table.find_all('tr')
                            current_week_num = None
                            
                            for row in rows:
                                cells = row.find_all(['td', 'th'])
                                if not cells or len(cells) < 2:
                                    continue
                                
                                cell_texts = [c.get_text(strip=True) for c in cells]
                                first_cell = cell_texts[0]
                                
                                # 헤더 행 스킵 (예: '주차', '강의자료', '출석' 등)
                                if "주차" in first_cell and not first_cell.isdigit():
                                    continue
                                    
                                # 1. 첫 번째 셀이 숫자(주차 번호)인 경우
                                if first_cell.isdigit():
                                    current_week_num = int(first_cell)
                                    if current_week_num not in summary_dict:
                                        # 주차별 상세 데이터를 저장할 구조 (강의자료 유무, 학습시간, 상태 문자열들)
                                        summary_dict[current_week_num] = {"material": "", "time": "", "texts": []}
                                
                                # 2. 첫 번째 셀에 숫자가 없지만 두 번째 셀에서 주차 감지
                                elif current_week_num is None:
                                    second_cell = cell_texts[1] if len(cell_texts) > 1 else ""
                                    w_match = re.search(r'(\d+)\s*주차', second_cell) or re.search(r'제(\d+)주차', second_cell)
                                    if w_match:
                                        current_week_num = int(w_match.group(1))
                                        if current_week_num not in summary_dict:
                                            summary_dict[current_week_num] = {"material": "", "time": "", "texts": []}
                                            
                                # 해당 행의 정보 수집 (강의 자료, 학습 시간, 출석 마크 등)
                                if current_week_num is not None:
                                    full_row_text = " ".join(cell_texts)
                                    
                                    # 강의 자료 이름 감지 (동영상이나 링크가 있으면 채워짐)
                                    has_material_tag = len(row.find_all('a')) > 0 or "강의" in full_row_text or "동영상" in full_row_text
                                    if has_material_tag:
                                        summary_dict[current_week_num]["material"] = "exists"
                                        
                                    # 학습 시간란에 '-'가 포함되어 있는지 체크
                                    if "-" in full_row_text and "총 학습시간" not in full_row_text:
                                        summary_dict[current_week_num]["time"] = "-"
                                        
                                    status_cells = cell_texts[-2:] if len(cell_texts) >= 2 else cell_texts
                                    img_attrs = [img.get('alt', '') + img.get('title', '') for img in row.find_all('img')]
                                    
                                    combined_status = " ".join(status_cells + img_attrs)
                                    summary_dict[current_week_num]["texts"].append(combined_status)
                    
                    # 최종 주차별 상태 결정 및 미진행 주차(업로드 전/기간 전) 필터링
                    final_summary = []
                    has_active_attendance = False  # 실제 출석 기록(출석/결석/지각 등)이 하나라도 있는지 체크
                    
                    for week_num in sorted(summary_dict.keys()):
                        data = summary_dict[week_num]
                        joined_str = " ".join(data["texts"]).strip()
                        material_exists = data["material"] == "exists"
                        time_is_hyphen = data["time"] == "-"
                        
                        # 1. 강의 자료 자체가 아예 없는 경우 (업로드 전) -> 표에서 제외
                        if not material_exists and not joined_str:
                            continue
                            
                        # 2. 강의 자료는 있으나 학습시간이 '-' 이고 출석 기록이 빈칸인 경우 (수강 기간 전) -> 표에서 제외
                        elif time_is_hyphen and (not joined_str or joined_str == "-" or joined_str == "- -"):
                            continue
                            
                        # 3. 지각 체크
                        if any(k in joined_str for k in ['▲', '△', '지각', 'L', 'late']):
                            final_st = "⚠️ 지각"
                            has_active_attendance = True
                        # 4. 결석/미출석 체크
                        elif 'X' in joined_str or 'x' in joined_str or '결석' in joined_str or '미출석' in joined_str:
                            final_st = "❌ 미출석"
                            has_active_attendance = True
                        # 5. 출석 체크
                        elif 'O' in joined_str or 'o' in joined_str or '출석' in joined_str:
                            final_st = "✅ 출석"
                            has_active_attendance = True
                        # 6. 그 외 기본 상태
                        else:
                            final_st = "➖ 예정/미열람"
                            has_active_attendance = True
                            
                        final_summary.append({"주차": f"{week_num}주차", "최종 출석 현황": final_st})
                    
                    # 옵션에 따라 모든 주차가 미진행인 과목 처리
                    if hide_all_upcoming and not has_active_attendance:
                        continue
                    
                    with st.expander(f"📖 {title}", expanded=True):
                        if final_summary:
                            df_summary = pd.DataFrame(final_summary)
                            st.table(df_summary)
                        else:
                            st.info("ℹ️ 현재 진행 중인 주차의 출석 기록이 없습니다.")
                else:
                    if not hide_all_upcoming:
                        with st.expander(f"📖 {title}", expanded=False):
                            st.info("온라인 출석부 메뉴를 찾을 수 없습니다.")