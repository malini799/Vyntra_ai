import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors


# ==================================================
# CONFIGURATION
# ==================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.8-flash"

client = genai.Client(api_key=API_KEY) if API_KEY else None


# ==================================================
# TEXT PROCESSING
# ==================================================

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were",
    "do", "does", "did", "can", "could", "would",
    "will", "what", "when", "where", "who", "why",
    "how", "which", "i", "we", "you", "they", "it",
    "my", "your", "our", "their", "me", "us", "to",
    "for", "of", "in", "on", "at", "by", "with",
    "and", "or", "if", "about", "please", "tell",
    "explain", "give", "have", "has", "be", "this",
    "that", "from", "there", "any", "much", "many",
    "accept", "provide", "offer", "available"
}


def normalize_word(word):
    word = word.lower()

    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"

    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word


def get_keywords(text):
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())

    return {
        normalize_word(word)
        for word in words
        if word not in STOP_WORDS and len(word) > 1
    }


def normalize_text(text):
    return re.sub(
        r"[^a-z0-9\s]",
        " ",
        text.lower()
    ).strip()


# ==================================================
# QUESTION TOPIC DETECTION
# ==================================================

TOPIC_KEYWORDS = {
    "delivery": {
        "delivery", "deliver", "shipping", "ship",
        "dispatch", "arrive", "arrival", "tracking",
        "track", "courier", "order"
    },

    "payment": {
        "payment", "pay", "paid", "method", "methods",
        "card", "upi", "cash", "cod", "transaction"
    },

    "refund": {
        "refund", "refunded", "reimbursement"
    },

    "return": {
        "return", "returns", "returning", "exchange",
        "replace", "replacement", "unused", "packaging"
    },

    "warranty": {
        "warranty", "guarantee", "repair", "defect",
        "damaged", "broken"
    },

    "contact": {
        "contact", "support", "help", "email",
        "phone", "reach", "response", "representative"
    }
}


def detect_topic(text):
    text = normalize_text(text)
    words = set(text.split())

    # Specific question patterns
    if any(phrase in text for phrase in [
        "payment method",
        "payment methods",
        "how can i pay",
        "how do i pay",
        "methods of payment"
    ]):
        return "payment"

    if any(phrase in text for phrase in [
        "delivery time",
        "how long for delivery",
        "how long does delivery take",
        "when will my order arrive",
        "shipping time"
    ]):
        return "delivery"

    if any(phrase in text for phrase in [
        "return policy",
        "return an item",
        "return a product",
        "exchange an item"
    ]):
        return "return"

    if any(phrase in text for phrase in [
        "refund status",
        "when will i get my refund",
        "how long does a refund take"
    ]):
        return "refund"

    # Detect the main topic from its keywords.
    scores = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        scores[topic] = len(words.intersection(keywords))

    best_topic = max(scores, key=scores.get)

    if scores[best_topic] == 0:
        return None

    # A refund question must not be treated as a payment-method question.
    if words.intersection({
        "refund", "refunded", "reimbursement"
    }):
        return "refund"

    if words.intersection({
        "payment", "pay", "paid", "card", "upi", "cod"
    }):
        return "payment"

    return best_topic


# ==================================================
# LOCAL DOCUMENT SEARCH
# ==================================================

def split_into_sections(context):
    """
    Split a document into searchable sections while
    retaining headings such as 'Payment Methods'.
    """

    sections = []
    current_heading = ""

    for line in context.splitlines():

        line = line.strip()

        if not line:
            continue

        # Example: 4. Payment Methods
        if re.match(r"^\d+[\.\)]\s+", line):
            current_heading = line
            continue

        sections.append((current_heading, line))

    # Handle documents without line breaks.
    if not sections:
        for sentence in re.split(
            r"(?<=[.!?])\s+",
            context
        ):
            sentence = sentence.strip()

            if sentence:
                sections.append(("", sentence))

    return sections


def local_document_answer(question, context):
    """
    Search the uploaded document without using the Gemini API.
    """

    if not context or not context.strip():
        return {
            "answer": (
                "[UNANSWERED] Please upload a readable "
                "business document first."
            ),
            "source": "Local Fallback",
            "unanswered": True
        }

    question_topic = detect_topic(question)
    question_keywords = get_keywords(question)

    sections = split_into_sections(context)
    scored_results = []

    for heading, text in sections:

        combined_text = f"{heading} {text}".strip()

        heading_topic = detect_topic(heading)
        text_topic = detect_topic(combined_text)

        # Reject sections clearly belonging to another topic.
        if (
            question_topic
            and heading_topic
            and question_topic != heading_topic
        ):
            continue

        if (
            question_topic
            and text_topic
            and question_topic != text_topic
        ):
            continue

        section_keywords = get_keywords(combined_text)
        matched = question_keywords.intersection(
            section_keywords
        )

        if not matched:
            continue

        score = (
            len(matched) /
            max(len(question_keywords), 1)
        )

        # Give a strong preference to the correct section heading.
        if question_topic and heading_topic == question_topic:
            score += 1.0

        scored_results.append(
            (score, len(matched), combined_text)
        )

    if not scored_results:
        return {
            "answer": (
                "[UNANSWERED] I couldn't find this information "
                "in the available business documents."
            ),
            "source": "Local Fallback",
            "unanswered": True
        }

    scored_results.sort(
        key=lambda item: (item[0], item[1]),
        reverse=True
    )

    best_score, match_count, best_text = scored_results[0]

    # For unknown topics, require more than a weak keyword match.
    if question_topic is None and match_count < 2:
        return {
            "answer": (
                "[UNANSWERED] I couldn't find this information "
                "in the available business documents."
            ),
            "source": "Local Fallback",
            "unanswered": True
        }

    answer = (
        "I searched your business document directly because "
        "Gemini was unavailable.\n\n"
        f"**Relevant document information:**\n\n{best_text}"
    )

    return {
        "answer": answer,
        "source": "Local Fallback",
        "unanswered": False
    }


# ==================================================
# MAIN CHATBOT
# ==================================================

def find_answer(question, context, demo_mode=False):
    """
    Use Gemini when available.
    Use local document search if Gemini fails or Demo Mode is on.
    """

    if not context or not context.strip():
        return {
            "answer": (
                "[UNANSWERED] Please upload a readable "
                "business document first."
            ),
            "source": "Local Fallback",
            "unanswered": True
        }

    # --------------------------------------------------
    # CONTROLLED FALLBACK DEMONSTRATION
    # --------------------------------------------------

    if demo_mode:

        result = local_document_answer(
            question,
            context
        )

        result["source"] = "Demo Mode — Local Fallback"

        # Clearly distinguish the simulation from a real outage.
        result["answer"] = (
            "**DEMO MODE: Simulated Gemini unavailability**\n\n"
            + result["answer"]
        )

        return result

    # --------------------------------------------------
    # CHECK GEMINI AVAILABILITY
    # --------------------------------------------------

    if not client:

        result = local_document_answer(
            question,
            context
        )

        result["answer"] = (
            "**Gemini API key unavailable.** "
            "Using local document search instead.\n\n"
            + result["answer"]
        )

        return result

    prompt = f"""
You are Vyntra AI, a business customer-support assistant.

RULES:
1. Use only the supplied business document.
2. Never invent facts, prices, or policies.
3. If the answer is unavailable, begin with [UNANSWERED].
4. Keep your answer concise and accurate.
5. Answer the specific question asked.

BUSINESS DOCUMENT:
{context}

CUSTOMER QUESTION:
{question}

ANSWER:
"""

    # Make a real Gemini request.
    # Do not retry a daily quota error.
    for attempt in range(2):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if response.text and response.text.strip():

                answer = response.text.strip()

                return {
                    "answer": answer,
                    "source": "Gemini AI",
                    "unanswered": answer.startswith(
                        "[UNANSWERED]"
                    )
                }

            break

        except errors.APIError as error:

            error_code = getattr(error, "code", None)

            print(
                f"Gemini API error {error_code}: {error}"
            )

            # Daily quota exceeded: stop immediately.
            if error_code == 429:
                break

            # Retry temporary server errors only once.
            if error_code in (500, 502, 503, 504):

                if attempt == 0:
                    time.sleep(2)
                    continue

            break

        except Exception as error:

            print(
                f"Gemini connection error: "
                f"{type(error).__name__}: {error}"
            )

            break

    # --------------------------------------------------
    # AUTOMATIC LOCAL FALLBACK
    # --------------------------------------------------

    result = local_document_answer(
        question,
        context
    )

    result["answer"] = (
        "**Gemini is unavailable. Local fallback activated.**\n\n"
        + result["answer"]
    )

    return result