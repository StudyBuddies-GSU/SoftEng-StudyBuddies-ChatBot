import streamlit as st
import psycopg2
import time
import os
from dotenv import load_dotenv
from openai import OpenAI

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- DATABASE CONNECTION ---
DB_NAME = "coursehelper"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_HOST = "db"
DB_PORT = "5432"

@st.cache_resource
def init_connection():
    """Create and cache a database connection."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )

# --- FETCH FUNCTIONS ---
def get_flashcards(conn, chapter=None):
    with conn.cursor() as cur:
        if chapter:
            cur.execute("SELECT question, answer FROM flashcards WHERE chapter = %s;", (chapter,))
        else:
            cur.execute("SELECT question, answer FROM flashcards;")
        return cur.fetchall()

def get_fallback_message(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT fallback_message FROM fallbacks LIMIT 1;")
        result = cur.fetchone()
        return result[0] if result else "I’m sorry, I cannot help you with that. That question falls out of scope with the course material and syllabus. I’m here to help with questions more relevant to your Software Engineering course."

# --- INITIALIZE STATE ---
if "screen" not in st.session_state:
    st.session_state.screen = "chatbot"  # chatbot, flashcards, quiz
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chapter" not in st.session_state:
    st.session_state.chapter = None
if "card_index" not in st.session_state:
    st.session_state.card_index = 0
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False
if "last_result" not in st.session_state:
    st.session_state.last_result = None
# New state for quiz feedback
if "feedback" not in st.session_state:
    st.session_state.feedback = None


# --- CONNECT TO DATABASE ---
try:
    conn = init_connection()
    fallback_message = get_fallback_message(conn)
except Exception as e:
    fallback_message = "⚠️ Could not connect to the database."
    st.error(f"Database error: {e}")
    conn = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("Controls")

    # Switch screen button
    if st.session_state.screen == "chatbot":
        if st.button("Flashcards Mode"):
            st.session_state.screen = "flashcards"
            st.rerun()
    else:
        if st.button("Chatbot Mode"):
            st.session_state.screen = "chatbot"
            st.rerun()

    st.markdown("---")

    # Sidebar content below divider
    if st.session_state.screen == "chatbot":
        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    else:
        st.markdown("### Chapters")
        for i in [1, 2, 3, 4, 5, 6, 8, 9, 12, 23]:
            if st.button(f"Chapter {i}"):
                st.session_state.chapter = i
                st.session_state.card_index = 0
                st.session_state.show_answer = False
                st.session_state.last_result = None
                st.session_state.feedback = None # Reset feedback
                st.rerun()

# --- CHATBOT SCREEN ---
if st.session_state.screen == "chatbot":
    st.title("🤓💻 SWE Chatbot")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if prompt := st.chat_input("Ask me anything about the course, material, or syllabus..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                response = client.chat.completions.create(
                    model="gpt-5-nano",
                    messages=[
                        {"role": "system", "content": "You are a helpful course assistant for a Software Engineering class."},
                        {"role": "user", "content": prompt},
                    ],
                )
                assistant_response = response.choices[0].message.content
            except Exception as e:
                assistant_response = f"⚠️ API error: {e}"

            # Simulate typing animation
            for chunk in assistant_response.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- FLASHCARDS & QUIZ SCREEN ---
else:
    if st.session_state.screen == "flashcards":
        st.title("📖 Flashcards Mode")
        if st.button("Switch to Quiz Mode", key="quiz_switch_top"):
            st.session_state.screen = "quiz"
            st.rerun()
    elif st.session_state.screen == "quiz":
        st.title("📝 Quiz Mode")
        if st.button("Switch to Flashcards Mode", key="flashcard_switch_top"):
            st.session_state.screen = "flashcards"
            st.rerun()

    flashcards = get_flashcards(conn, st.session_state.chapter) if (conn and st.session_state.chapter) else []

    if not st.session_state.chapter:
        st.markdown("### Choose a chapter from the sidebar to begin.")
    elif not flashcards:
        st.warning("No flashcards found for this chapter.")
    else:
        question, answer = flashcards[st.session_state.card_index]
        card_content = answer if st.session_state.show_answer else question

        # Display the flashcard
        st.markdown(
            f"""
            <div style="
                width: 500px;
                height: 300px;
                margin: auto;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 12px;
                border: 2px solid #ccc;
                background-color: #f9f9f9;
                font-size: 22px;
                font-weight: 500;
                text-align: center;
                padding: 20px;
            ">
            {card_content}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Flip Card"):
            st.session_state.show_answer = not st.session_state.show_answer
            st.session_state.last_result = None
            st.session_state.feedback = None # Reset feedback
            st.rerun()

        # --- QUIZ MODE SPECIFIC UI ---
        if st.session_state.screen == "quiz":
            user_answer = st.text_input("Your Answer:")
            if st.button("Submit Answer"):

                # Generate feedback using the chatbot
                try:
                    feedback_prompt = f"""
                    A student is being quizzed on Software Engineering.
                    The question was: "{question}"
                    The correct answer is: "{answer}"
                    The student's answer was: "{user_answer}"

                    Begin your response with "Correct." if the student's answer sufficiently conveys all the same ideas as the correct answer.
                    Otherwise, begin your response with "Incorrect."

                    Provide brief, constructive feedback in 2-3 sentences.
                    - If the answer is correct, offer encouragement.
                    - If the answer is incorrect, gently explain the misunderstanding and guide them toward the correct concept without simply giving the answer away.
                    """
                    response = client.chat.completions.create(
                        model="gpt-5-nano",
                        messages=[
                            {"role": "system", "content": "You are a helpful and encouraging teaching assistant."},
                            {"role": "user", "content": feedback_prompt}
                        ]
                    )
                    st.session_state.feedback = response.choices[0].message.content
                    if "incorrect" in st.session_state.feedback.lower():
                        st.session_state.last_result = "incorrect"
                    else:
                        st.session_state.last_result = "correct"
                except Exception as e:
                    st.session_state.feedback = f"⚠️ Could not generate feedback: {e}"

                st.session_state.show_answer = True
                st.rerun()
            
            # --- NEW: Display Feedback Field ---
            if st.session_state.feedback:
                with st.expander("🤖 Show AI Feedback", expanded=True):
                    st.info(st.session_state.feedback)


        # --- NAVIGATION BUTTONS ---
        col1, col2, col3 = st.columns([1, 0.5, 1])
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.card_index = (st.session_state.card_index - 1) % len(flashcards)
                st.session_state.show_answer = False
                st.session_state.last_result = None
                st.session_state.feedback = None # Reset feedback
                st.rerun()
        with col2:
            if st.session_state.last_result == "correct":
                st.markdown("<h3>✅</h3>", unsafe_allow_html=True)
            elif st.session_state.last_result == "incorrect":
                st.markdown("<h3>❌</h3>", unsafe_allow_html=True)
            else:
                st.markdown("&nbsp;", unsafe_allow_html=True)
        with col3:
            if st.button("Next ➡️"):
                st.session_state.card_index = (st.session_state.card_index + 1) % len(flashcards)
                st.session_state.show_answer = False
                st.session_state.last_result = None
                st.session_state.feedback = None # Reset feedback
                st.rerun()