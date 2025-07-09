import streamlit as st
import os
from azure.storage.blob import BlobServiceClient

# 외부에서 주입받을 blob 클라이언트
blob_service_client = None
CONTAINER_NAME = "word-data"

def init_blob_service_a(client: BlobServiceClient):
    global blob_service_client
    blob_service_client = client

def upload_tab():
    st.header("📁 Word 파일 업로드 / 파일명 특수문자 제외")
    uploaded_file = st.file_uploader("Word (.docx) 파일을 업로드하세요", type="docx")
    if uploaded_file:
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=uploaded_file.name)
        blob_client.upload_blob(uploaded_file, overwrite=True)
        st.success(f"{uploaded_file.name} 파일이 Azure에 업로드되었습니다.")
        st.session_state["refresh_list"] = True  # 목록 갱신 플래그 설정

    st.divider()
    st.subheader("🗂️ Word 파일 조회 및 삭제")

    try:
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blobs = container_client.list_blobs()
        docx_files = [blob.name for blob in blobs if blob.name.endswith(".docx")]

        if docx_files:
            for file_name in docx_files:
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.markdown(f"• **{file_name}**")
                with col2:
                    delete_button = st.button("❌", key=file_name)
                    if delete_button:
                        blob_client = container_client.get_blob_client(file_name)
                        blob_client.delete_blob()
                        st.session_state["refresh_list"] = True  # 삭제 후 플래그 설정
                        st.rerun()  # 즉시 리렌더링
        else:
            st.info("현재 저장된 Word 파일이 없습니다.")
    except Exception as e:
        st.error(f"파일 목록을 가져오거나 삭제 중 오류가 발생했어요: {e}")