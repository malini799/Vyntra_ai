import streamlit as st
from document_processor import extract_text
from chatbot import find_answer
from database import (
    create_table,
    record_question,
    get_question_stats,
    get_frequent_questions
)

# Create the database table
create_table()

# Page configuration
st.set_page_config(
    page_title="Vyntra AI",
    page_icon="🤖",
    layout="wide"
)

# App heading
st.title("🤖 Vyntra AI")
st.subheader("Your Business Knowledge. One Intelligent Assistant.")

st.write(
    "An AI-powered customer support assistant "
    "that answers questions using business documents."
)

st.divider()

# Upload business documents
st.header("📄 Upload Business Documents")

uploaded_files = st.file_uploader(
    "Upload business FAQs or policies",
    type=["txt", "pdf"],
    accept_multiple_files=True
)

# Extract text from uploaded documents
document_context = ""

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            text = extract_text(uploaded_file)

            if text and text.strip():
                document_context += (
                    f"\nDocument: {uploaded_file.name}\n"
                    f"{text}\n"
                )

                st.success(
                    f"Successfully processed: {uploaded_file.name}"
                )
            else:
                st.warning(
                    f"No readable text found in {uploaded_file.name}"
                )

        except Exception as error:
            st.error(
                f"Could not process {uploaded_file.name}: {error}"
            )
else:
    st.info("Upload a business document to get started.")

st.divider()

# Customer chatbot
st.header("💬 Customer Chatbot")

question = st.text_input(
    "Ask a question about the business",
    placeholder="Example: What is your return policy?"
)

if st.button("Ask Vyntra AI"):

    if not question.strip():
        st.warning("Please enter a question.")

    elif not document_context.strip():
        st.warning(
            "Please upload a readable business document first."
        )

    else:
        with st.spinner("Vyntra AI is finding your answer..."):
            answer = find_answer(
                question,
                document_context
            )

        # Identify whether the question was unanswered
        is_unanswered = (
            answer.strip().startswith("[UNANSWERED]")
            or answer.lower().strip().startswith(
                "i couldn't find this information in the available business documents"
            )
        )

        # Record every question
        record_question(
            question,
            answered=not is_unanswered
        )

        # Clean up the answer for display
        answer = answer.replace(
            "[UNANSWERED]", "", 1
        ).strip()

        if is_unanswered:
            st.warning(
                "⚠️ This information is missing from the business documents."
            )

        st.markdown("### 🤖 Vyntra AI's Answer")
        st.write(answer)

# Business Insights dashboard
st.divider()

st.header("📊 Business Insights")
st.write("Understand what your customers are asking.")

total, answered, unanswered = get_question_stats()

total = total or 0
answered = answered or 0
unanswered = unanswered or 0

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Questions", total)

with col2:
    st.metric("✅ Answered", answered)

with col3:
    st.metric("⚠️ Unanswered", unanswered)

if total > 0:

    # Answer rate
    st.subheader("📈 Answer Rate")

    answer_rate = (answered / total) * 100

    st.progress(answer_rate / 100)

    st.write(
        f"Vyntra AI answered {answer_rate:.1f}% "
        "of recorded questions."
    )

    st.divider()

    # Answered questions
    st.subheader("✅ Frequently Asked Questions")

    answered_questions = get_frequent_questions(1)

    if answered_questions:
        for customer_question, frequency in answered_questions:
            st.write(
                f"**{customer_question}** — "
                f"Asked {frequency} time(s)"
            )
    else:
        st.info("No answered questions recorded yet.")

    st.divider()

    # Unanswered questions
    st.subheader("⚠️ Questions Needing Business Attention")

    unanswered_questions = get_frequent_questions(0)

    if unanswered_questions:
        for customer_question, frequency in unanswered_questions:
            st.write(
                f"**{customer_question}** — "
                f"Asked {frequency} time(s)"
            )
    else:
        st.success("No unanswered questions recorded yet.")

else:
    st.info(
        "Ask Vyntra AI some questions to start generating insights."
    )