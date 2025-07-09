import streamlit as st
from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

# streamlit run .\main.py
# 환경 변수에서 OpenAI API 키를 가져옵니다.
load_dotenv()

os.system('cls' if os.name == 'nt' else 'clear') # nt는 윈도우 옛날 버전 이름

azure_connection_string = os.getenv("AZURE_CONNECTION_STRING")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_endpoint = os.getenv("OPENAI_ENDPOINT")
chat_deployment_name = os.getenv("CHAT_DEPLOYMENT_NAME")
language_endpoint = os.getenv("LANGUAGE_ENDPOINT")
language_api_key = os.getenv("LANGUAGE_API_KEY")
search_service_name = os.getenv("SEARCH_SERVICE_NAME")
serach_api_key = os.getenv("SEARCH_API_KEY")
lang_search_key = os.getenv("LANG_SEARCH_KEY")

# Blob 클라이언트 생성
blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)

# 각 탭에 클라이언트 전달
from View.a_upload_tab import init_blob_service_a, upload_tab
from View.b_summary_tab import init_language_client, init_blob_service_b, init_gpt_b, summary_tab
from View.c_search_tab import init_serach_c, search_tab
from View.d_ai_tab import init_gpt_d, init_get_key, init_blob_service_d, init_serach_d, ai_tab

init_blob_service_a(blob_service_client)
init_blob_service_b(blob_service_client)
init_blob_service_d(blob_service_client)
init_serach_c(service_name=search_service_name,api_key=serach_api_key)
init_serach_d(service_name=search_service_name,api_key=serach_api_key)
init_language_client(endpoint=language_endpoint, key=language_api_key)
init_gpt_b(endpoint=openai_endpoint, key=openai_api_key, deployment=chat_deployment_name)
init_gpt_d(endpoint=openai_endpoint, key=openai_api_key, deployment=chat_deployment_name)
init_get_key(lang_key=lang_search_key)


# 🧭 Streamlit UI 구성
st.title("📘 RFP 기반 제안 작성 자료 정리 및 문서 Q&A 지원 시스템")

tabs = st.tabs(["파일업로드", "요약+openAI", "문서 내 검색", "AI Chat 검색"])

with tabs[0]:
    upload_tab()
with tabs[1]:
    summary_tab()
with tabs[2]:
    search_tab()
with tabs[3]:
    ai_tab()