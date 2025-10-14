import streamlit as st
import psycopg2
import time


# --- DATABASE CONNECTION ---
DB_NAME = "coursehelper"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_HOST = "db"  # "db" is the service name in docker-compose.yml
DB_PORT = "5432"


@st.cache_resource
def init_connection():
    """Create and cache a database connection."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )


def get_flashcards(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM flashcards;")
        return cur.fetchall()


def get_fallback_message(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT fallback_message FROM fallbacks LIMIT 1;")
        result = cur.fetchone()
        return result[0] if result else "No fallback message found."


# --- STREAMLIT UI ---
st.title("🤖 Simple Chatbot UI")
st.caption("A clean interface for your chatbot application with PostgreSQL backend.")


# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- CONNECT TO DATABASE ---
try:
    conn = init_connection()
    fallback_message = get_fallback_message(conn)
except Exception as e:
    fallback_message = "⚠️ Could not connect to the database."
    st.error(f"Database error: {e}")
    conn = None


# --- DISPLAY CHAT HISTORY ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- USER INPUT ---
if prompt := st.chat_input("Ask me anything..."):
    # 1️⃣ Add user's message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2️⃣ Generate assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Simple logic:
        # - If the user message includes "flashcard", show data from DB
        # - Otherwise, show fallback message
        if conn and "flashcard" in prompt.lower():
            flashcards = get_flashcards(conn)
            assistant_response = f"Found {len(flashcards)} flashcards in database."
        else:
            assistant_response = fallback_message

        # Simulate typing
        for chunk in assistant_response.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)

    # 3️⃣ Save assistant message
    st.session_state.messages.append({"role": "assistant", "content": full_response})


# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Controls")

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown(
        "This is a simple chatbot UI built with Streamlit and PostgreSQL. "
        "It uses a real database for flashcards and fallback messages."
    )
