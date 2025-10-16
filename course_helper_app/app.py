import streamlit as st
import psycopg2
import time

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
        return result[0] if result else "No fallback message found."


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

            if conn and "flashcard" in prompt.lower():
                flashcards = get_flashcards(conn)
                assistant_response = f"Found {len(flashcards)} flashcards in database."
            else:
                assistant_response = fallback_message

            for chunk in assistant_response.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})


# --- FLASHCARDS & QUIZ SCREEN ---
else:
    # Title + Mode Switch
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

    # Load flashcards
    flashcards = get_flashcards(conn, st.session_state.chapter) if (conn and st.session_state.chapter) else []

    # Show card
    if not st.session_state.chapter:
        st.markdown("### Choose a chapter from the sidebar to begin.")
    elif not flashcards:
        st.warning("No flashcards found for this chapter.")
    else:
        question, answer = flashcards[st.session_state.card_index]

        # Flip logic
        card_content = answer if st.session_state.show_answer else question

        # Card styling
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
                cursor: pointer;
            ">
            {card_content}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Detect card click
        if st.button("Flip Card"):
            st.session_state.show_answer = not st.session_state.show_answer
            st.session_state.last_result = None
            st.rerun()

        # Quiz input (only in quiz mode)
        if st.session_state.screen == "quiz":
            user_answer = st.text_input("Your Answer:")
            if st.button("Submit Answer"):
                if user_answer.strip().lower() == answer.strip().lower():
                    st.session_state.last_result = "correct"
                else:
                    st.session_state.last_result = "incorrect"
                st.session_state.show_answer = True
                st.rerun()

        # Navigation buttons
        col1, col2, col3 = st.columns([1, 0.5, 1])
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.card_index = (st.session_state.card_index - 1) % len(flashcards)
                st.session_state.show_answer = False
                st.session_state.last_result = None
                st.rerun()
        with col2:
            if st.session_state.last_result == "correct":
                st.markdown("✅", unsafe_allow_html=True)
            elif st.session_state.last_result == "incorrect":
                st.markdown("❌", unsafe_allow_html=True)
            else:
                st.markdown("&nbsp;", unsafe_allow_html=True)
        with col3:
            if st.button("Next ➡️"):
                st.session_state.card_index = (st.session_state.card_index + 1) % len(flashcards)
                st.session_state.show_answer = False
                st.session_state.last_result = None
                st.rerun()