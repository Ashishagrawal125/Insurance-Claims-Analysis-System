import streamlit as st
import os
import json
import tempfile
import traceback

try:
    from utils.pdf_processor import extract_structured_sections, is_valid_pdf
    from utils.vector_search import create_vector_index, get_top_similar_clauses
    from utils.ai_analyzer import analyze_claim_with_ai
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error(f"Traceback: {traceback.format_exc()}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Insurance Claims Analysis System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'processed_document' not in st.session_state:
    st.session_state.processed_document = None
if 'vector_index' not in st.session_state:
    st.session_state.vector_index = None
if 'structured_clauses' not in st.session_state:
    st.session_state.structured_clauses = None
if 'model' not in st.session_state:
    st.session_state.model = None

def main():
    # Health check for deployment debugging
    if st.sidebar.button("Health Check"):
        st.sidebar.success("✅ App is running successfully!")
        st.sidebar.info(f"Python version: {os.sys.version}")
        st.sidebar.info(f"Streamlit version: {st.__version__}")
        
        # Show PDF library info
        try:
            from utils.pdf_processor import PDF_LIBRARY
            st.sidebar.info(f"PDF Library: {PDF_LIBRARY}")
        except:
            st.sidebar.warning("PDF Library: Unknown")
    
    st.title("🏥 Insurance Claims Analysis System")
    st.markdown("---")
    
    # API Key check
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        st.error("⚠️ PERPLEXITY_API_KEY environment variable not found. Please set your API key.")
        st.stop()
    
    # Sidebar for document upload
    with st.sidebar:
        st.header("📄 Document Upload")
        uploaded_file = st.file_uploader(
            "Upload Insurance Policy PDF",
            type=['pdf'],
            help="Upload a PDF file containing insurance policy documents"
        )
        
        if uploaded_file is not None:
            if st.button("🔄 Process Document", type="primary"):
                process_document(uploaded_file)
    
    # Main content area
    if st.session_state.processed_document is None:
        st.info("👆 Please upload an insurance policy PDF document to get started.")
        st.markdown("""
        ### How to use this system:
        1. **Upload** your insurance policy PDF using the sidebar
        2. **Process** the document to extract policy clauses
        3. **Enter** your claim query in natural language
        4. **Get** AI-powered coverage analysis with justification
        """)
    else:
        display_analysis_interface()

def process_document(uploaded_file):
    """Process the uploaded PDF document"""
    with st.spinner("🔄 Processing document..."):
        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Validate PDF
            if not is_valid_pdf(tmp_file_path):
                st.error("❌ Invalid PDF file. Please upload a valid PDF document.")
                os.unlink(tmp_file_path)
                return
            
            # Extract structured sections
            progress_bar = st.progress(0, "Extracting document sections...")
            structured_clauses = extract_structured_sections(tmp_file_path)
            progress_bar.progress(50, "Processing clauses...")
            
            # Filter out short clauses
            structured_clauses = [clause for clause in structured_clauses if len(clause['text']) > 50]
            
            if not structured_clauses:
                st.error("❌ No valid clauses found in the document. Please check the PDF content.")
                os.unlink(tmp_file_path)
                return
            
            progress_bar.progress(75, "Creating vector index...")
            
            # Create vector index
            vector_index, model = create_vector_index(structured_clauses)
            
            progress_bar.progress(100, "Document processed successfully!")
            
            # Store in session state
            st.session_state.processed_document = uploaded_file.name
            st.session_state.vector_index = vector_index
            st.session_state.structured_clauses = structured_clauses
            st.session_state.model = model
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
            st.success(f"✅ Successfully processed {len(structured_clauses)} policy clauses from '{uploaded_file.name}'")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error processing document: {str(e)}")
            # Clean up temporary file if it exists
            try:
                if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
            except:
                pass

def display_analysis_interface():
    """Display the main analysis interface"""
    st.header("🔍 Claims Analysis")
    
    # Document info
    st.success(f"📄 Document loaded: {st.session_state.processed_document}")
    st.info(f"📊 {len(st.session_state.structured_clauses)} policy clauses indexed")
    
    # Query input section
    st.subheader("Enter Your Claim Queries")
    
    # Initialize query list in session state
    if 'query_list' not in st.session_state:
        st.session_state.query_list = [""]
    
    # Multiple query input
    st.markdown("**Add multiple queries (one per line):**")
    queries_text = st.text_area(
        "Describe your insurance claims:",
        value="\n".join(st.session_state.query_list) if st.session_state.query_list[0] else "",
        placeholder="Example:\n50M, used air ambulance, distance traveled 300 km, seeking 100% reimbursement\n35F, pre-existing diabetes, hospitalization for 5 days\n28M, outpatient surgery, day care procedure claim",
        height=150,
        help="Enter one claim per line. You can analyze multiple claims at once."
    )
    
    # Parse queries
    if queries_text.strip():
        query_list = [q.strip() for q in queries_text.split('\n') if q.strip()]
        st.session_state.query_list = query_list
    else:
        st.session_state.query_list = [""]
    
    # Quick examples section
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### Quick Examples")
        example_queries = [
            "50M, used air ambulance, distance traveled 300 km, seeking 100% reimbursement",
            "35F, pre-existing diabetes, hospitalization for 5 days", 
            "28M, outpatient surgery, day care procedure claim",
            "45F, maternity expenses, normal delivery claim"
        ]
        
        if st.button("Load All Examples", key="load_examples"):
            st.session_state.query_list = example_queries
            st.rerun()
        
        for i, example in enumerate(example_queries):
            if st.button(f"Add Example {i+1}", key=f"example_{i}", help=example):
                if st.session_state.query_list == [""]:
                    st.session_state.query_list = [example]
                else:
                    st.session_state.query_list.append(example)
                st.rerun()
    
    with col1:
        # Analysis button
        valid_queries = [q for q in st.session_state.query_list if q.strip()]
        if st.button("🔍 Analyze Claims", type="primary", disabled=not valid_queries):
            analyze_multiple_claims(valid_queries)

def analyze_claim(query):
    """Analyze a single insurance claim"""
    with st.spinner("🔍 Analyzing your claim..."):
        try:
            # Get relevant clauses
            progress_bar = st.progress(0, "Finding relevant clauses...")
            relevant_clauses = get_top_similar_clauses(
                query=query,
                indexed_data=st.session_state.structured_clauses,
                index=st.session_state.vector_index,
                model=st.session_state.model,
                k=5
            )
            
            progress_bar.progress(50, "Getting AI analysis...")
            
            # Get AI analysis
            analysis_result = analyze_claim_with_ai(query, relevant_clauses)
            
            progress_bar.progress(100, "Analysis complete!")
            
            # Display results
            display_analysis_results(query, relevant_clauses, analysis_result)
            
        except Exception as e:
            st.error(f"❌ Error analyzing claim: {str(e)}")

def analyze_multiple_claims(queries):
    """Analyze multiple insurance claims"""
    results = []
    
    with st.spinner(f"🔍 Analyzing {len(queries)} claims..."):
        try:
            for i, query in enumerate(queries):
                # Update progress
                progress = (i + 1) / len(queries)
                st.progress(progress, f"Analyzing claim {i+1} of {len(queries)}")
                
                # Get relevant clauses
                relevant_clauses = get_top_similar_clauses(
                    query=query,
                    indexed_data=st.session_state.structured_clauses,
                    index=st.session_state.vector_index,
                    model=st.session_state.model,
                    k=5
                )
                
                # Get AI analysis
                analysis_result = analyze_claim_with_ai(query, relevant_clauses)
                
                # Store result
                results.append({
                    "query": query,
                    "relevant_clauses": relevant_clauses,
                    "analysis": analysis_result
                })
            
            # Display results in JSON format
            display_json_results(results)
                
        except Exception as e:
            st.error(f"❌ Error analyzing claims: {str(e)}")

def display_analysis_results(query, relevant_clauses, analysis_result):
    """Display the analysis results"""
    st.markdown("---")
    st.header("📋 Analysis Results")
    
    # Query recap
    st.subheader("🔍 Your Query")
    st.info(query)
    
    # AI Analysis
    st.subheader("🤖 AI Coverage Analysis")
    
    if analysis_result:
        try:
            # Try to parse JSON response
            if isinstance(analysis_result, str):
                # Try to extract JSON from the response
                json_start = analysis_result.find('{')
                json_end = analysis_result.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = analysis_result[json_start:json_end]
                    result = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            else:
                result = analysis_result
            
            # Display decision
            decision = result.get('decision', 'Unknown')
            amount = result.get('amount', 'Not specified')
            justification = result.get('justification', 'No justification provided')
            
            # Decision display
            if decision.lower() == 'yes':
                st.success(f"✅ **Coverage Decision:** {decision}")
            elif decision.lower() == 'no':
                st.error(f"❌ **Coverage Decision:** {decision}")
            else:
                st.warning(f"⚠️ **Coverage Decision:** {decision}")
            
            # Amount display
            if amount and amount != 'Not specified':
                st.info(f"💰 **Amount:** {amount}")
            
            # Justification
            st.markdown("**📝 Justification:**")
            st.write(justification)
            
        except (json.JSONDecodeError, ValueError):
            # Fallback to raw response
            st.write("**AI Response:**")
            st.write(analysis_result)
    else:
        st.error("❌ No analysis result received")
    
    # Relevant clauses
    st.subheader("📄 Relevant Policy Clauses")
    
    for i, clause in enumerate(relevant_clauses, 1):
        with st.expander(f"Clause {i}: {clause['title']} (Page {clause['page_number']})"):
            st.write(clause['text'])
    
    # Reset button
    if st.button("🔄 New Analysis"):
        st.rerun()

def display_json_results(results):
    """Display results in JSON format"""
    st.markdown("---")
    st.header("📋 Claims Analysis Results (JSON Format)")
    
    # Prepare JSON output
    json_results = []
    for i, result in enumerate(results, 1):
        try:
            # Try to parse the AI response as JSON
            analysis_text = result.get("analysis", "")
            if isinstance(analysis_text, str):
                json_start = analysis_text.find('{')
                json_end = analysis_text.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    analysis_json = json.loads(analysis_text[json_start:json_end])
                else:
                    analysis_json = {"raw_response": analysis_text}
            else:
                analysis_json = analysis_text
            
            claim_result = {
                "claim_id": i,
                "query": result["query"],
                "analysis_result": analysis_json,
                "relevant_clauses": [
                    {
                        "title": clause["title"],
                        "page_number": clause["page_number"],
                        "text": clause["text"][:200] + "..." if len(clause["text"]) > 200 else clause["text"]
                    }
                    for clause in result["relevant_clauses"]
                ]
            }
            json_results.append(claim_result)
            
        except json.JSONDecodeError:
            # Fallback for non-JSON responses
            claim_result = {
                "claim_id": i,
                "query": result["query"],
                "analysis_result": {"raw_response": result.get("analysis", "")},
                "relevant_clauses": [
                    {
                        "title": clause["title"],
                        "page_number": clause["page_number"],
                        "text": clause["text"][:200] + "..." if len(clause["text"]) > 200 else clause["text"]
                    }
                    for clause in result["relevant_clauses"]
                ]
            }
            json_results.append(claim_result)
    
    # Display JSON
    st.json(json_results)
    
    # Download button
    json_str = json.dumps(json_results, indent=2)
    st.download_button(
        label="📥 Download Results as JSON",
        data=json_str,
        file_name=f"insurance_claims_analysis_{len(results)}_claims.json",
        mime="application/json"
    )
    
    # Reset button
    if st.button("🔄 New Analysis", key="new_json_analysis"):
        st.rerun()

def display_single_result(result, claim_number):
    """Display a single claim result"""
    query = result["query"]
    relevant_clauses = result["relevant_clauses"]
    analysis_result = result["analysis"]
    
    # Query recap
    st.markdown(f"**Query {claim_number}:**")
    st.info(query)
    
    # AI Analysis
    st.markdown("**AI Coverage Analysis:**")
    
    if analysis_result:
        try:
            # Try to parse JSON response
            if isinstance(analysis_result, str):
                json_start = analysis_result.find('{')
                json_end = analysis_result.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    json_str = analysis_result[json_start:json_end]
                    parsed_result = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            else:
                parsed_result = analysis_result
            
            # Display decision
            decision = parsed_result.get('decision', 'Unknown')
            amount = parsed_result.get('amount', 'Not specified')
            justification = parsed_result.get('justification', 'No justification provided')
            
            # Decision display with colors
            if decision.lower() == 'yes':
                st.success(f"✅ **Coverage Decision:** {decision}")
            elif decision.lower() == 'no':
                st.error(f"❌ **Coverage Decision:** {decision}")
            else:
                st.warning(f"⚠️ **Coverage Decision:** {decision}")
            
            # Amount display
            if amount and amount != 'Not specified':
                st.info(f"💰 **Amount:** {amount}")
            
            # Justification
            st.markdown("**📝 Justification:**")
            st.write(justification)
            
        except (json.JSONDecodeError, ValueError):
            # Fallback to raw response
            st.write("**AI Response:**")
            st.write(analysis_result)
    else:
        st.error("❌ No analysis result received")
    
    # Relevant clauses (collapsed)
    with st.expander(f"📄 Relevant Policy Clauses ({len(relevant_clauses)} found)"):
        for j, clause in enumerate(relevant_clauses, 1):
            st.markdown(f"**Clause {j}: {clause['title']} (Page {clause['page_number']})**")
            st.write(clause['text'])
            if j < len(relevant_clauses):
                st.markdown("---")

if __name__ == "__main__":
    main()
