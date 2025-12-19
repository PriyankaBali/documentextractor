import streamlit as st
import asyncio
from pathlib import Path
import sys
import os

# Add project root to path to ensure imports work
# distinct from where the script is run
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.processor import DocumentProcessor
from src.output.schemas import DocumentTypeEnum

st.set_page_config(
    page_title="Document Extractor",
    page_icon="📄",
    layout="wide"
)

# Custom CSS for better look
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_processor():
    return DocumentProcessor()

def main():
    st.title("📄 Document Extractor")
    st.markdown("Upload a document to extract structured data.")

    # Sidebar configuration
    st.sidebar.header("Configuration")
    doc_type = st.sidebar.selectbox(
        "Document Type Hint (Optional)",
        options=["Auto-detect"] + [t.value for t in DocumentTypeEnum],
        index=0
    )

    document_type_hint = None
    if doc_type != "Auto-detect":
        document_type_hint = DocumentTypeEnum(doc_type)

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file", 
        type=["pdf", "jpg", "jpeg", "png", "docx"]
    )

    if uploaded_file:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Document Preview")
            if uploaded_file.type.startswith('image'):
                st.image(uploaded_file, use_container_width=True)
            elif uploaded_file.type == 'application/pdf':
                st.info("PDF Preview not supported natively in this view, but file is loaded.")
            else:
                st.info(f"Preview not available for {uploaded_file.type}")

        with col2:
            st.subheader("Extraction")
            if st.button("Extract Data", type="primary", use_container_width=True):
                with st.spinner("Processing document..."):
                    try:
                        processor = get_processor()
                        
                        # Process file
                        content = uploaded_file.getvalue()
                        result = processor.process_file(
                            content=content,
                            filename=uploaded_file.name,
                            document_type_hint=document_type_hint
                        )
                        
                        if result.success:
                            # Display Overall Confidence
                            confidence = result.response.overall_confidence
                            metric_color = "normal"
                            if confidence > 0.8:
                                metric_color = "normal" 
                            elif confidence > 0.5:
                                metric_color = "off"
                            else:
                                metric_color = "inverse"
                                
                            st.metric(
                                label="Overall Confidence", 
                                value=f"{confidence:.2%}",
                                delta=None
                            )
                            
                            # Display Fields
                            st.markdown("### Extracted Fields")
                            data = result.response.extracted_data
                            confidences = result.response.field_confidences
                            
                            for field, value in data.items():
                                field_conf = confidences.get(field, 0.0)
                                color = "green" if field_conf > 0.8 else "orange" if field_conf > 0.5 else "red"
                                
                                st.markdown(
                                    f"**{field.replace('_', ' ').title()}**: {value} "
                                    f"<span style='color:{color}; font-size:0.8em'>({field_conf:.0%})</span>",
                                    unsafe_allow_html=True
                                )
                                
                            # JSON Response expander
                            with st.expander("View Raw JSON Response"):
                                st.json(result.response.model_dump())
                                
                        else:
                            st.error("Processing failed")
                            if result.response.errors:
                                for error in result.response.errors:
                                    st.error(f"{error.code}: {error.message}")
                                    
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
