import streamlit as st
import requests
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
import tempfile, os, docx

# Azure 설정 변수
search_service_name = None
search_api_key = None
index_name = "basic"
blob_service_client = None
gpt_client = None
deployment_name = None
lang_search_key = None

def init_blob_service_d(client: BlobServiceClient):
    global blob_service_client
    blob_service_client = client

def init_serach_d(service_name, api_key):
    global search_service_name, search_api_key
    search_service_name = service_name
    search_api_key = api_key

def init_gpt_d(endpoint, key, deployment):
    global gpt_client, deployment_name
    # gpt_client = AzureOpenAI(api_key=key, api_version="2024-07-18-preview", azure_endpoint=endpoint)
    # gpt_client = AzureOpenAI(api_key=key, api_version="2024-07-18", azure_endpoint=endpoint)
    gpt_client = AzureOpenAI(api_key=key, api_version="2024-04-01-preview", azure_endpoint=endpoint)
    deployment_name = deployment

def init_get_key(lang_key):
    global lang_search_key
    lang_search_key = lang_key

def ai_tab():
    st.header("🌐 LangSearch + 문서 기반 GPT 분석 (RAG 구조)")

    # 클라이언트 체크
    if not blob_service_client or not gpt_client:
        st.error("클라이언트 초기화 오류")
        return

    # RFP 문서 선택
    container_client = blob_service_client.get_container_client("word-data")
    docx_files = [blob.name for blob in container_client.list_blobs() if blob.name.endswith(".docx")]

    if not docx_files:
        st.warning("📁 업로드된 RFP 문서가 없습니다.")
        return

    selected_file = st.selectbox("📄 요약할 문서를 선택하세요", docx_files)
    
    user_prompt = st.text_area("GPT에게 요청할 작업 내용을 입력하세요", 
        value="1. 전체 내용을 간결한 한 단락으로 요약하세요.\n" \
            "2. 문서에 언급된 핵심 주제 또는 도메인을 도출하고 정리하세요.\n" \
            "3. 제안요청의 목적과 배경을 간단명료하게 설명하세요.\n" \
            "4. 업무적 요구사항을 종합적으로 분석하여 자체적으로 항목을 만들어 구분된 조견표 형태로 출력하세요.\n" \
            "5. 기술적 요구사항을 기능/비기능/운영/보안와 자체적으로 항목을 만들어 항목별로 구분된 조견표 형태로 출력하세요.\n" \
            "6. 이 문서의 흐름에 맞춰 예상되는 목차 구조를 제안하세요 (예: 개요 → 요구사항 → 제안서 구성).\n" \
            "7. 적합한 IT 기술 또는 유관 솔루션 중 본 문서의 요구사항과 연관된 추천 기술을 제시해주세요.\n" \
            "8. 외부 검색 결과를 활용해 문서의 이해도를 높여주세요.",
        height=150
    )
    keyword = st.text_input("🌐 외부 정보 검색 키워드를 입력하세요", value="금융")
    # langsearch_api_key = st.text_input("🔑 LangSearch API 키 입력", type="password")
    langsearch_api_key = lang_search_key

    # 프롬프트 입력 & 외부 검색어
    if st.button("🚀 분석 시작", key="rag_analysis_button"):        
        try:
            # 🔽 문서 다운로드 및 텍스트 추출
            blob = blob_service_client.get_blob_client("word-data", selected_file)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(blob.download_blob().readall())
                tmp_path = tmp.name

            doc = docx.Document(tmp_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            document_text = "\n".join(paragraphs)
            os.remove(tmp_path)

            st.success("✅ 문서 텍스트 추출 완료")
            st.write(f"📏 문서 길이: {len(document_text)}자")

            # 🌐 LangSearch 검색 (POST 방식)
            external_info = ""
            try:
                headers = {
                    "Authorization": f"Bearer {langsearch_api_key}",
                    "Content-Type": "application/json"
                }
                body = {
                    "query": keyword,
                    "freshness": "noLimit",
                    "summary": True,
                    "count": 5
                }
                resp = requests.post("https://api.langsearch.com/v1/web-search", headers=headers, json=body)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    external_info = "\n".join([r.get("summary", "") for r in results])
                    st.info(f"🌐 외부 정보 {len(results)}건 수집 완료")
                else:
                    st.warning(f"LangSearch 실패: 상태코드 {resp.status_code}")
            except Exception as e:
                st.error(f"LangSearch 호출 오류: {e}")

            # 🤖 GPT 프롬프트 구성
            gpt_prompt = f"""
                당신은 금융 RFP를 분석하는 전문가입니다.
                아래는 실제 문서 내용입니다:
                \"\"\"{document_text}\"\"\"
                아래는 외부 검색으로 수집된 배경 정보입니다:
                \"\"\"{external_info}\"\"\"
                사용자 요청:
                {user_prompt}
                전체 문서와 외부 배경을 반영하여 step-by-step으로 분석하고 응답하세요.
                """

            with st.expander("📨 GPT 프롬프트 확인", expanded=False):
                st.code(gpt_prompt[:1200] + "..." if len(gpt_prompt) > 1200 else gpt_prompt)

            developer = """
                너는 금융권 RFP 문서를 참고하여 제안서를 작성하는 전문가다.  
                - 금융 IT 시스템, 최신 기술 트렌드, 규제 환경에 정통하다.  
                - RFP 요구사항을 정확히 분석해, 실현 가능한 솔루션과 명확한 근거를 제시한다.  
                - 제안서는 논리적 구조(요구사항, 솔루션, 일정, 예산, 리스크 등)로 작성하며, 근거와 데이터, 표를 활용해 신뢰도를 높인다.  
                - 복잡한 용어는 쉽게 풀어 설명하고, 허위·과장·비현실적 내용은 배제한다.  
                - 법적·윤리적 기준과 금융 규제를 최대한 준수한다.  
                - 가능하다면 실제 금융권 RFP 사례를 참고해 설득력 있는 제안서를 작성하라.
            """

            # 🧠 GPT 호출
            gpt_response = gpt_client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": developer},
                    {"role": "user", "content": gpt_prompt}
                ]
            )            

            if gpt_response:
                with st.expander("📌 GPT 분석 결과", expanded=False):
                    if gpt_response:
                        content = gpt_response.choices[0].message.content.strip()
                        st.markdown(content if content else "응답이 비어 있어요.")
                    else:
                        st.error("GPT 응답 실패")
            else:
                st.error("GPT 호출 실패")

            st.session_state.document_text = document_text
            st.session_state.external_info = external_info

        except Exception as e:
            st.error(f"오류 발생: {e}")

    # 초기 설정        
    # if "chat_input" not in st.session_state:
    #     st.session_state.chat_input = ""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "document_text" in st.session_state and "external_info" in st.session_state:
        st.subheader("💬 ChatBot 대화")     

        # 질문 입력 UI
        chat_input = st.text_input("질문을 입력하세요", key="chat_input")

        if st.button("💬 질문하기", key="chat_langsearch_button"):
            question = st.session_state["chat_input"].strip()
            if question:
                chat_prompt = f"문서: {st.session_state.document_text}\n외부정보: {st.session_state.external_info}\n질문: {question}"
                chat_response = gpt_client.chat.completions.create(
                    model=deployment_name,
                    messages=[
                        {"role": "system", "content": "너는 금융 RFP 분석 전문가이며, 문서와 외부 정보를 함께 활용해 답변해요."},
                        {"role": "user", "content": chat_prompt}
                    ]
                )
                if chat_response:
                    response_text = chat_response.choices[0].message.content.strip()
                    # 히스토리 저장
                    st.session_state.chat_history.append({
                        "question": question,
                        "answer": response_text
                    })
                else:
                    st.warning("Chat 응답이 비어 있어요.")

    # 이전 대화 기록 출력
    #   대화 기록 출력
    st.markdown("---")
    st.markdown("### 🗨️ 대화 기록")
    for idx, qa in enumerate(st.session_state.chat_history[::-1]):  # 최신 순
        st.markdown(f"**🟢 질문 {len(st.session_state.chat_history) - idx}:** {qa['question']}")
        st.markdown(f"**🧠 답변:** {qa['answer']}")
        st.markdown("---")  # 구분선으로 메시지 정리

    
