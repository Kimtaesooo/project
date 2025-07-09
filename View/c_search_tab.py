import streamlit as st
import requests

# Azure Search 설정
search_service_name = None
search_api_key = None
index_name = "basic"

def init_serach_c(service_name, api_key):
    global search_service_name, search_api_key
    search_service_name = service_name
    search_api_key = api_key

# UI 구성 함수
def search_tab():
    st.subheader("🔎 Azure Search 기반 문서 검색")

    # 검색 키워드 입력
    keyword = st.text_input("검색할 키워드를 입력하세요")

    # 전체 필드 목록
    all_fields = ["content", "title", "author", "file_type"]

    # 사용자 필드 선택
    selected_fields = st.multiselect(
        "검색할 필드를 선택하세요",
        options=all_fields,
        default=["content"]
    )

    # 인덱스 정의 기준으로 검색 가능한 필드만 리스트로 구성
    searchable_fields = ["content"]  # 필드 중 searchable: true 인 것만
    valid_search_fields = [field for field in selected_fields if field in searchable_fields]

    # 검색 URL 구성
    search_url = f"{search_service_name}/indexes/{index_name}/docs/search?api-version=2023-10-01-Preview"

    if st.button("조회", key="search_basic_button"):
        if keyword:
            if not valid_search_fields:
                st.warning("⚠️ 선택한 필드 중 검색 가능한 항목이 없습니다.")
                return

            headers = {
                "Content-Type": "application/json",
                "api-key": search_api_key
            }

            data = {
                "search": keyword,
                "searchFields": ",".join(valid_search_fields),
                "top": 5
            }

            response = requests.post(search_url, headers=headers, json=data)

            if response.status_code == 200:
                results = response.json()
                for doc in results.get("value", []):
                    st.markdown(f"### 📄 제목: {doc.get('title', '(제목 없음)')}")
                    st.write(doc.get("content", "(본문 없음)"))
                    st.caption(f"🕒 작성일: {doc.get('created', 'N/A')} | 작성자: {doc.get('author', 'N/A')}")
                    st.divider()
            else:
                st.error(f"❌ 검색 실패: {response.status_code} - {response.text}")
        else:
            st.warning("🔎 검색 키워드를 입력해 주세요.")
