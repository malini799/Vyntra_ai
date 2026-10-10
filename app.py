import streamlit as st

from document_processor import extract_text
from chatbot import find_answer
from database import record_question, get_question_stats, get_frequent_questions


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Vyntra AI",
    page_icon="🤖",
    layout="wide",
)


# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b1120;
        color: #f1f5f9;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
    }

    div[data-testid="stMetric"] {
        background-color: #172033;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #263449;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 12px;
    }

    .hero-box {
        background: linear-gradient(120deg, #172554, #115e59);
        padding: 28px;
        border-radius: 16px;
        border: 1px solid #2dd4bf;
        margin-bottom: 20px;
    }

    .hero-label {
        color: #5eead4;
        font-size: 13px;
        font-weight: bold;
        letter-spacing: 2px;
    }

    .hero-title {
        color: white;
        font-size: 36px;
        font-weight: 800;
        margin-top: 8px;
    }

    .hero-description {
        color: #e2e8f0;
        font-size: 16px;
        margin-top: 8px;
    }

    .status-box {
        background-color: #172033;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #263449;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div class="hero-box">
        <div class="hero-label">AI-POWERED BUSINESS PLATFORM</div>
        <div class="hero-title">Vyntra AI</div>
        <div class="hero-description">
            Intelligent customer support with document-based answers
            and knowledge-gap detection.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write(
    "Upload a business document and ask questions about its content. "
    "Gemini AI answers when available, while local document search "
    "provides a fallback."
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("⚙️ Control Panel")

    st.subheader("Knowledge Base")

    uploaded_file = st.file_uploader(
        "Upload a business document",
        type=["txt", "pdf"],
        help="Upload a TXT or PDF file containing business information.",
    )

    if uploaded_file is not None:
        if (
            st.session_state.get("uploaded_filename")
            != uploaded_file.name
        ):
            try:
                extracted_text = extract_text(uploaded_file)

                st.session_state.document_context = extracted_text
                st.session_state.document_name = uploaded_file.name
                st.session_state.uploaded_filename = uploaded_file.name
                st.session_state.chat_history = []

                st.success("Document loaded successfully!")

            except Exception as error:
                st.error(f"Could not read document: {error}")

    if st.session_state.get("document_context"):
        st.success(
            f"Knowledge base ready: "
            f"{st.session_state.get('document_name', 'Document')}"
        )

        with st.expander("Preview document text"):
            st.write(
                st.session_state.document_context[:2000]
            )
    else:
        st.warning("No business document loaded.")

    st.divider()

    st.subheader("AI Settings")

    demo_mode = st.toggle(
        "Demo Mode — Simulate Gemini outage",
        value=False,
        help=(
            "Uses the local document fallback without calling Gemini. "
            "This is a demonstration mode, not a live Gemini response."
        ),
    )

    if demo_mode:
        st.info("Demo Mode is ON. Local fallback is being used.")
    else:
        st.caption(
            "Live mode: Gemini is attempted when a question is submitted."
        )

    st.divider()

    st.subheader("About Vyntra AI")

    st.write(
        "Vyntra AI helps businesses answer customer questions "
        "from their documents and identify questions that need "
        "additional information."
    )


# --------------------------------------------------
# INITIALIZE SESSION STATE
# --------------------------------------------------

if "document_context" not in st.session_state:
    st.session_state.document_context = ""

if "document_name" not in st.session_state:
    st.session_state.document_name = ""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --------------------------------------------------
# MAIN LAYOUT
# --------------------------------------------------

chat_column, info_column = st.columns([2, 1])


# --------------------------------------------------
# CHAT SECTION
# --------------------------------------------------

with chat_column:
    st.subheader("💬 Customer Support Chat")

    if not st.session_state.document_context:
        st.info(
            "Upload your business FAQ or another TXT/PDF document "
            "using the sidebar to start asking questions."
        )

    # Display previous messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant":
                source = message.get("source", "")

                if source:
                    st.caption(f"Answer source: {source}")

                if message.get("unanswered", False):
                    st.warning(
                        "Knowledge gap detected. "
                        "The document may not contain the answer."
                    )

    # Question form
    with st.form("question_form", clear_on_submit=True):
        customer_question = st.text_input(
            "Your question",
            placeholder="Example: What payment methods do you accept?",
        )

        submit_question = st.form_submit_button(
            "Ask Vyntra AI",
            use_container_width=True,
        )

    if submit_question:
        if not customer_question.strip():
            st.warning("Please enter a question.")
        elif not st.session_state.document_context:
            st.warning(
                "Please upload a business document before asking questions."
            )
        else:
            # Save the user's question
            st.session_state.chat_history.append(
                {
                    "role": "user",
                    "content": customer_question,
                }
            )

            try:
                result = find_answer(
                    customer_question,
                    st.session_state.document_context,
                    demo_mode=demo_mode,
                )

                answer = result["answer"]
                source = result["source"]
                unanswered = result["unanswered"]

            except Exception as error:
                answer = (
                    "Sorry, I could not process that question. "
                    "Please try again."
                )
                source = "Error"
                unanswered = True

                print(f"Chatbot error: {error}")

            # Record the question in the database
            try:
                record_question(
                    customer_question,
                    0 if unanswered else 1,
                )
            except Exception as error:
                print(f"Database error: {error}")

            # Save the assistant's response
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "source": source,
                    "unanswered": unanswered,
                }
            )

            st.rerun()


# --------------------------------------------------
# DASHBOARD SECTION
# --------------------------------------------------

with info_column:
    st.subheader("📊 Knowledge Dashboard")

    try:
        stats = get_question_stats()

        # Support the expected dictionary result from database.py
        if isinstance(stats, dict):
            total_questions = stats.get("total", 0)
            answered_questions = stats.get("answered", 0)
            unanswered_questions = stats.get("unanswered", 0)

        # Also support a tuple/list result
        elif isinstance(stats, (tuple, list)) and len(stats) >= 3:
            total_questions = stats[0]
            answered_questions = stats[1]
            unanswered_questions = stats[2]

        else:
            total_questions = 0
            answered_questions = 0
            unanswered_questions = 0

        if total_questions:
            answer_rate = (
                answered_questions / total_questions
            ) * 100
        else:
            answer_rate = 0

        metric1, metric2 = st.columns(2)

        metric1.metric(
            "Total Questions",
            total_questions,
        )

        metric2.metric(
            "Answered",
            answered_questions,
        )

        metric3, metric4 = st.columns(2)

        metric3.metric(
            "Knowledge Gaps",
            unanswered_questions,
        )

        metric4.metric(
            "Answer Rate",
            f"{answer_rate:.1f}%",
        )

        st.divider()

        st.markdown("#### ⚠️ Unanswered Questions")

        unanswered_list = get_frequent_questions(0)

        if unanswered_list:
            for item in unanswered_list:
                if isinstance(item, (tuple, list)):
                    question = item[0]
                    count = item[1] if len(item) > 1 else 1
                elif isinstance(item, dict):
                    question = item.get("question", str(item))
                    count = item.get("count", 1)
                else:
                    question = str(item)
                    count = 1

                st.write(f"• {question} — **{count} time(s)**")
        else:
            st.caption("No knowledge gaps recorded yet.")

        st.divider()

        st.markdown("#### ✅ Frequently Answered Questions")

        answered_list = get_frequent_questions(1)

        if answered_list:
            for item in answered_list:
                if isinstance(item, (tuple, list)):
                    question = item[0]
                    count = item[1] if len(item) > 1 else 1
                elif isinstance(item, dict):
                    question = item.get("question", str(item))
                    count = item.get("count", 1)
                else:
                    question = str(item)
                    count = 1

                st.write(f"• {question} — **{count} time(s)**")
        else:
            st.caption("No answered questions recorded yet.")

    except Exception as error:
        st.error(
            "The dashboard could not load its statistics. "
            "Please check database.py."
        )
        print(f"Dashboard error: {error}")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Vyntra AI | Document-Based Customer Support | "
    "Knowledge-Gap Detection"
)