import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
import time
import re
import docx, tempfile, os

language_client = None
blob_service_client = None
gpt_client = None
deployment_name = None

CONTAINER_NAME = "word-data"


# 초기화 함수들
def init_language_client(endpoint, key):
    global language_client
    language_client = TextAnalyticsClient(endpoint=endpoint, credential=AzureKeyCredential(key))

def init_blob_service_b(client: BlobServiceClient):
    global blob_service_client
    blob_service_client = client

def init_gpt_b(endpoint, key, deployment):
    global gpt_client, deployment_name
    # gpt_client = AzureOpenAI(api_key=key, api_version="2024-07-18-preview", azure_endpoint=endpoint)
    # gpt_client = AzureOpenAI(api_key=key, api_version="2024-07-18", azure_endpoint=endpoint)
    gpt_client = AzureOpenAI(api_key=key, api_version="2024-04-01-preview", azure_endpoint=endpoint)
    deployment_name = deployment

def clean_text(text: str) -> str:
    # 특수문자 제거 + 공백 정리 + 숫자 제거
    text = re.sub(r"[^\w\s가-힣]", " ", text)       # 특수문자 제거
    text = re.sub(r"\d+", " ", text)               # 숫자 제거
    text = re.sub(r"\s+", " ", text)               # 공백 정리
    return text.strip()

# UI 구성 함수
def summary_tab():
    # Language Service 입력 문서 분할 처리: 최대 5120 텍스트 요소 초과 시 오류 → 단락별로 나눠서 처리

    st.header("🧪 RFP 문서 요약 & Chat")

    if not blob_service_client or not language_client or not gpt_client:
        st.error("클라이언트 초기화 오류")
        return

    # 📄 문서 목록 불러오기
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    docx_files = [blob.name for blob in container_client.list_blobs() if blob.name.endswith(".docx")]

    if not docx_files:
        st.info("📂 업로드된 문서가 없습니다.")
        return

    selected_file = st.selectbox("요약할 문서를 선택하세요", docx_files)

    st.markdown("""
            <div style="font-size:10pt;">
            <b>현재 적용 된 프롬프트</b><br>
            1. 전체 내용을 간결한 한 단락으로 요약하세요.<br>
            2. 문서에 언급된 핵심 주제 또는 도메인을 도출하고 정리하세요.<br>
            3. 제안요청의 목적과 배경을 간단명료하게 설명하세요.<br>
            4. 업무적 요구사항을 종합적으로 분석하여 자체적으로 항목을 만들어 구분된 조견표 형태로 출력하세요.<br>
            5. 기술적 요구사항을 기능/비기능/운영/보안와 자체적으로 항목을 만들어 항목별로 구분된 조견표 형태로 출력하세요.<br>
            6. 이 문서의 흐름에 맞춰 예상되는 목차 구조를 제안하세요 (예: 개요 → 요구사항 → 제안서 구성).<br>
            7. 적합한 IT 기술 또는 유관 솔루션 중 본 문서의 요구사항과 연관된 추천 기술을 제시해주세요.<br>

            주의사항:<br>
            - 형식은 Markdown 또는 표를 활용해 시각적으로 구성해 주세요.<br>
            </div>
            """, unsafe_allow_html=True)
        
    # 사용자 입력 프롬프트
    default_instruction = """
        요청 작업:
        1. 전체 내용을 간결한 한 단락으로 요약하세요.
        2. 문서에 언급된 핵심 주제 또는 도메인을 도출하고 정리하세요.
        3. 제안요청의 목적과 배경을 간단명료하게 설명하세요.
        4. 업무적 요구사항을 종합적으로 분석하여 자체적으로 항목을 만들어 구분된 조견표 형태로 출력하세요.
        5. 기술적 요구사항을 기능/비기능/운영/보안와 자체적으로 항목을 만들어 항목별로 구분된 조견표 형태로 출력하세요.
        6. 이 문서의 흐름에 맞춰 예상되는 목차 구조를 제안하세요 (예: 개요 → 요구사항 → 제안서 구성).
        7. 적합한 IT 기술 또는 유관 솔루션 중 본 문서의 요구사항과 연관된 추천 기술을 제시해주세요.

        주의사항:
        - 형식은 Markdown 또는 표를 활용해 시각적으로 구성해 주세요.
        """
    user_instruction = st.text_area(
        label="GPT 프롬프트 분석 항목을 입력하세요",
        value=default_instruction,
        height=180
    )

    if st.button("🚀 요약 시작", key="summary_button"):
        try:
            # 📥 파일 다운로드 및 텍스트 추출
            blob = blob_service_client.get_blob_client(CONTAINER_NAME, selected_file)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(blob.download_blob().readall())
                tmp_path = tmp.name
            
            doc = docx.Document(tmp_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            full_text = "\n".join(paragraphs)
            os.remove(tmp_path)
            st.write("문서 길이:", len(full_text))

            st.success("✅ 문서 추출 완료")

            # 📏 텍스트 분할 (5120 요소 제한 고려)
            max_chars = 4000
            chunks = []
            current = ""

            for para in paragraphs:
                if len(current) + len(para) < max_chars:
                    current += para + "\n"
                else:
                    chunks.append(current)
                    current = para + "\n"
            if current:
                chunks.append(current)

            # ✂️ [1] 문서 요약 (SDK 5.3용 사용불가)
            # st.subheader("✂️ Language 요약 결과")
            # for idx, chunk in enumerate(chunks):
            #     try:
            #         task = AnalyzeTextOptions(
            #             input_documents=[TextDocumentInput(id="1", text=chunk)],
            #             tasks=[{
            #                 "kind": TasksKind.SUMMARIZATION,
            #                 "parameters": {
            #                     "sentence_count": 5,
            #                     "sort_by": "Rank"
            #                 }
            #             }]
            #         )
            #         poller = language_client.analyze_text(task)
            #         results = poller.result()
            #         for doc_result in results:
            #             for task_result in doc_result.results:
            #                 if task_result.kind.name == "summarization":
            #                     st.markdown(f"📄 요약 블록 {idx+1}")
            #                     for sentence in task_result.sentences:
            #                         st.markdown(f"- {sentence.text}")
            #     except Exception as e:
            #         st.error(f"요약 블록 {idx+1} 오류: {e}")

            for idx, chunk in enumerate(chunks):
                try:
                    cleaned_text = clean_text(chunk)

                    with st.expander(f"🧩 Chunk {idx+1} 결과 ({len(chunk)}자)", expanded=False):
                        st.markdown("### 🔑 핵심 키워드")
                        phrase_result = language_client.extract_key_phrases([cleaned_text])
                        for doc in phrase_result:
                            if not doc.is_error:
                                # ✨ 🔍 키워드 후처리 필터링 적용
                                filtered_keywords = [
                                    kw for kw in doc.key_phrases
                                    if len(kw.strip()) > 2 and not re.search(r"\b의\b|\b년\b|\bSPI의\b", kw)
                                ]
                                unique_keywords = list(set(filtered_keywords))  # 중복 제거
                                for kw in unique_keywords:
                                    st.markdown(f"• {kw}")
                            else:
                                st.error(f"키워드 추출 실패 {e}")

                        st.markdown("### 📑 문서 요약 문장")
                        poller = language_client.begin_extract_summary([cleaned_text], max_sentence_count=8)
                        summary_results = poller.result()
                        for doc in summary_results:
                            if not doc.is_error:
                                for sentence in doc.sentences:
                                    st.markdown(f"• {sentence.text}")
                            else:
                                st.error(f"요약 실패 {e}")
                except Exception as e:
                    st.error(f"❌ Chunk {idx+1} 처리 중 오류 발생: {e}")
        
            # # 🔸 감정 분석
            # st.subheader("❤️ [2] 감정 분석")
            # sentiment_result = language_client.analyze_sentiment([full_text])[0]
            # if not sentiment_result.is_error:
            #     st.write(f"전반적인 감정: `{sentiment_result.sentiment}`")
            #     st.write("감정 점수:", sentiment_result.confidence_scores._asdict())
        
        except Exception as e:
            st.error(f"문서 분석 오류: {e}")
            # return

        # 🧠 GPT 분석
        st.subheader("🤖 GPT 요약 및 기술 분석")

        gpt_input = full_text
        prompt = f"""다음은 RFP 문서 원문입니다. 문서를 바탕으로 아래 항목을 전체적으로 스캔 후 step by step으로 자료 분석 및 작성해주세요. :
                \"\"\"{gpt_input}\"\"\"
                \"\"\"{user_instruction}\"\"\"
                문서 내용:"""

        st.write("문서 길이:", len(full_text))
        st.write("전달 된 문서 길이:", len(gpt_input))
        st.write("GPT에 보낸 prompt 길이:", len(prompt))

        # time
        max_retries = 1
        retry_count = 0
        gpt_response = None

        developer = """
                너는 금융권 RFP 문서를 참고하여 제안서를 작성하는 전문가다.  
                - 금융 IT 시스템, 최신 기술 트렌드, 규제 환경에 정통하다.  
                - RFP 요구사항을 정확히 분석해, 실현 가능한 솔루션과 명확한 근거를 제시한다.  
                - 제안서는 논리적 구조(요구사항, 솔루션, 일정, 예산, 리스크 등)로 작성하며, 근거와 데이터, 표를 활용해 신뢰도를 높인다.  
                - 복잡한 용어는 쉽게 풀어 설명하고, 허위·과장·비현실적 내용은 배제한다.  
                - 법적·윤리적 기준과 금융 규제를 최대한 준수한다.  
                - 가능하다면 실제 금융권 RFP 사례를 참고해 설득력 있는 제안서를 작성하라.
            """
        progress_bar = st.progress(0)
        status_text = st.empty()

        while retry_count < max_retries:
            try:
                for i in range(101):  # 예: 진행률을 10단계로 나누어 대기 시간 동안 보여줌
                    progress_value = min(max(i, 0), 100)
                    progress_bar.progress(progress_value)
                    status_text.text(f"OpenAI 응답 기다리는 중... ({i + 1}/30)")

                gpt_response = gpt_client.chat.completions.create(
                    model=deployment_name,
                    messages=[
                        {"role": "system", "content": developer},
                        {"role": "user", "content": prompt}]
                )
                status_text.text("✅ 응답 수신 완료!")
                progress_bar.empty()
                break  # 정상적으로 응답 받으면 반복 종료
            except Exception as e:
                status_text.text("❌ 오류 발생!")
                progress_bar.empty()
                if "429" in str(e):
                    retry_count += 1
                    st.warning(f"🚦 GPT 호출이 제한되었어요. {30}초 대기 후 다시 시도합니다... (시도 {retry_count}/{max_retries})")
                    time.sleep(20)
                else:
                    st.error(f"GPT 호출 오류: {e}")
                    break

        # ✅ 토큰 사용량 분석
        if gpt_response and hasattr(gpt_response, "usage"):
            token_info = gpt_response.usage
            st.write("🔢 GPT 토큰 사용량")
            st.write(f"- 입력 tokens: {token_info.prompt_tokens}")
            st.write(f"- 출력 tokens: {token_info.completion_tokens}")
            st.write(f"- 전체 tokens: {token_info.total_tokens}")

            # 📌 토큰 수 기준 자동 경고
            total_used = token_info.total_tokens
            if total_used > 80000:
                st.warning("⚠️ 현재 프롬프트와 출력 토큰 수가 80,000을 초과했어요. GPT의 입력 한도(128,000)에 근접하고 있어요.")
                st.markdown("✅ 문서 내용 슬라이싱을 더 줄이거나, chunk 방식으로 분할 요약하는 게 안전해요.")
            elif total_used > 100000:
                st.error("🚨 거의 한계치에 도달했어요. 문서 길이를 줄이는 것이 꼭 필요합니다.")

        with st.expander(f"분석 결과", expanded=False):        
            # 결과 처리
            if gpt_response:
                content = gpt_response.choices[0].message.content.strip()
                if content:
                    st.markdown(content)
                else:
                    st.warning("GPT 응답이 비어 있어요.")
            else:
                st.error("GPT 호출에 반복 실패했습니다. 나중에 다시 시도해 주세요.")