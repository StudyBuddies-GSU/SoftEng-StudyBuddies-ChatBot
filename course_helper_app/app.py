import base64
import os
import time
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psycopg2
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - macOS/Windows fallbacks
    ZoneInfo = None

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TZ_NAME = "America/New_York"

def get_tz():
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(TZ_NAME)
    except Exception:
        return None

APP_TZ = get_tz()

BASE_DIR = Path(__file__).resolve().parent
FLASHCARD_DIR = BASE_DIR / "questions_answers_txts"

VECTOR_STORE_NAME = os.getenv("OPENAI_VECTOR_STORE_NAME", "vector1")
VECTOR_STORE_ID_ENV = os.getenv("OPENAI_VECTOR_STORE_ID")
CHATBOT_VECTOR_MODEL = os.getenv("CHATBOT_VECTOR_MODEL", "gpt-4o-mini")
CHATBOT_FALLBACK_MODEL = os.getenv("CHATBOT_FALLBACK_MODEL", "gpt-5-nano")
CHATBOT_SYSTEM_PROMPT = (
    "You are a helpful course assistant for a Software Engineering class. "
    "Do not exceed 8 sentences for your answer. "
    "Use the syllabus file to answer the syllabus. "
    "Use the chapter material (files may start with CH) to answer content about the course and its material. "
    "If you're listing, use bullet points with newlines or a numbered list with newlines."
    "If the question isn't about the course material, the course, or the syllabus (as in, it it's outside the scope of our course entirely), then return a fallback message stating you cannot help with that."
)
DEFAULT_CHATBOT_FALLBACK = (
    "I’m sorry, I cannot help you with that. "
    "That question falls out of scope with the course material and syllabus. "
    "I’m here to help with questions more relevant to your Software Engineering course."
)

def now_in_app_tz() -> datetime:
    if APP_TZ:
        return datetime.now(APP_TZ)
    return datetime.now()

def format_ts(dt: datetime) -> str:
    """Format datetime to 'H:MM AM/PM' cross-platform."""
    try:
        return dt.strftime("%-I:%M %p")
    except Exception:
        return dt.strftime("%#I:%M %p")

def set_custom_theme():
    primary_color = "#4A4A4A"
    background_color = "#FCF7E6"
    secondary_background_color = "#E0DAC9"
    text_color = "#4A4A4A"

    st.markdown(
        f"""
        <style>
        :root {{
            --primary-color: {primary_color};
            --background-color: {background_color};
            --secondary-background-color: {secondary_background_color};
            --text-color: {text_color};
            --font-family: 'Georgia', serif;
        }}

        [data-testid="stAppViewContainer"] > .main {{
            color: var(--text-color);
        }}

        h1 {{
            color: #3e2723;
            font-family: 'Times New Roman', serif;
        }}

        [data-testid="stSidebar"] {{
            background-color: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(4px);
            border-right: 3px solid #795548;
            color: #3e2723;
        }}

        [data-testid="stTextInput"] > div > div {{
            background-color: #FFFFFF;
            border-radius: 8px;
        }}

        .stButton>button {{
            border: 2px solid #795548;
            border-radius: 6px;
            background-color: #E0DAC9;
            color: #3e2723;
            font-weight: 600;
        }}
        .stButton>button:hover {{
            background-color: #C5B9A4;
            color: #000000;
        }}

        .flashcard-custom {{
            background-color: #FEFBF0 !important;
            border: 3px solid #795548 !important;
            box-shadow: 4px 4px 10px rgba(0,0,0,0.2) !important;
            color: #3e2723;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def add_background(image_file: str):
    try:
        with open(image_file, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.error(f"Error: Background image file not found at {image_file}")
        return

    page_bg = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url('data:image/png;base64,{encoded}');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
    [data-testid="stToolbar"] {{ right: 2rem; }}
    </style>
    """
    st.markdown(page_bg, unsafe_allow_html=True)

def add_textbook_frame(image_file: str):
    try:
        with open(image_file, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        st.warning(f"Textbook frame image not found at {image_file}")
        return

    frame_html = f"""
    <style>
    .textbook-frame {{
        position: fixed;
        top: 70%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 80vw;
        z-index: 0;
        opacity: 1;
        pointer-events: none;
    }}
    [data-testid="stAppViewContainer"] > div:first-child {{
        position: relative;
        z-index: 1;
    }}
    </style>
    <img class="textbook-frame" src="data:image/png;base64,{encoded}" />
    """
    st.markdown(frame_html, unsafe_allow_html=True)

def inject_chat_styles():
    st.markdown(
        """
        <style>
        .chat-row {
            display: flex;
            margin: 8px 0 0 0;
            position: relative;
            z-index: 2;
        }
        [data-testid="stAppViewContainer"] > div:first-child {
            position: relative;
            z-index: 2;
        }
        .bubble {
            max-width: min(680px, 78vw);
            padding: 10px 14px;
            line-height: 1.4;
            font-size: 16px;
            border-radius: 18px;
            box-shadow: 0 1px 0 rgba(0,0,0,0.04);
            word-wrap: break-word;
            white-space: pre-wrap;
        }
        .user-row { justify-content: flex-start; align-items: flex-end; }
        .user-bubble {
            background: #34C759;
            color: #ffffff;
            border-radius: 18px 18px 18px 4px;
        }
        .assistant-row { justify-content: flex-end; align-items: flex-end; }
        .assistant-bubble {
            background: #E9E9EB;
            color: #111;
            border-radius: 18px 18px 4px 18px;
        }
        .center-row { justify-content: center; align-items: flex-end; }
        .welcome-bubble {
            text-align: center;
            padding: 14px 18px;
            margin-top: 6px;
        }
        .welcome-bubble strong { color: #000; }
        .avatar-emoji {
            font-size: 18px;
            line-height: 28px;
            margin: 0 6px;
            user-select: none;
        }
        .chat-meta {
            font-size: 12px;
            color: #666;
            margin: 4px 6px 12px;
        }
        .user-meta { text-align: left; }
        .assistant-meta { text-align: right; }
        </style>
        """,
        unsafe_allow_html=True,
    )

set_custom_theme()
add_background("assets/wood_background.png")
add_textbook_frame("assets/textbook_frame.png")
inject_chat_styles()

DB_NAME = "coursehelper"
DB_USER = "postgres"
DB_PASS = "postgres"
DB_HOST = "db"
DB_PORT = "5432"

@st.cache_resource(show_spinner=False)
def init_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )


@lru_cache(maxsize=1)
def get_vector_store_id() -> Optional[str]:
    """Resolve the OpenAI vector store ID from env or by name."""
    if VECTOR_STORE_ID_ENV:
        return VECTOR_STORE_ID_ENV

    target = VECTOR_STORE_NAME
    if not target:
        return None
    if target.startswith("vs_"):
        return target

    try:
        cursor = None
        while True:
            page = client.vector_stores.list(after=cursor) if cursor else client.vector_stores.list()
            for store in getattr(page, "data", []):
                if getattr(store, "name", None) == target or getattr(store, "id", None) == target:
                    return store.id
            if not getattr(page, "has_more", False):
                break
            cursor = getattr(page, "last_id", None)
            if not cursor:
                break
    except Exception:
        return None
    return None


def _vector_store_response(prompt: str) -> Optional[str]:
    """Query the configured vector store using the Responses API."""
    store_id = get_vector_store_id()
    if not store_id:
        return None
    try:
        resp = client.responses.create(
            model=CHATBOT_VECTOR_MODEL,
            input=prompt,
            tools=[{"type": "file_search", "vector_store_ids": [store_id]}],
        )
    except Exception:
        return None

    text = getattr(resp, "output_text", None)
    if text:
        return text.strip()
    return None


def _generate_chatbot_answer(prompt: str, chapter_scope: Optional[int] = None, fallback: Optional[str] = None) -> str:
    """Return an answer grounded in the vector store content with graceful fallback."""
    fallback_text = fallback or DEFAULT_CHATBOT_FALLBACK
    if not prompt:
        return fallback_text

    scoped_prompt = prompt.strip()
    if chapter_scope:
        scoped_prompt = (
            f"Stay within the scope of Chapter {chapter_scope} unless the user explicitly asks otherwise.\n\n{scoped_prompt}"
        )

    final_prompt = f"{CHATBOT_SYSTEM_PROMPT}\n\n{scoped_prompt}"

    vector_answer = _vector_store_response(final_prompt)
    if vector_answer:
        return vector_answer

    try:
        response = client.chat.completions.create(
            model=CHATBOT_FALLBACK_MODEL,
            messages=[
                {"role": "system", "content": CHATBOT_SYSTEM_PROMPT},
                {"role": "user", "content": scoped_prompt},
            ],
        )
        content = response.choices[0].message.content if response.choices else None
        return (content or fallback_text).strip()
    except Exception:
        return fallback_text


def get_chatbot_response(
    prompt: str, chapter_scope: Optional[int] = None, fallback: Optional[str] = None
) -> Tuple[str, ...]:
    """Public helper retained for compatibility with existing tests."""
    answer = _generate_chatbot_answer(prompt, chapter_scope, fallback)
    return (answer,) if answer else ()


def _parse_flashcard_line(line: str) -> Optional[Tuple[str, str]]:
    if " - " not in line:
        return None
    question, answer = line.split(" - ", 1)
    question = question.strip()
    answer = answer.strip()
    if not question or not answer:
        return None
    return question, answer


def _load_chapter_from_file(path: Path) -> List[Tuple[str, str]]:
    cards: List[Tuple[str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return cards

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if "question" in line.lower() and "answer" in line.lower():
            # Skip header rows.
            continue
        parsed = _parse_flashcard_line(line)
        if parsed:
            cards.append(parsed)
    return cards


@lru_cache(maxsize=1)
def load_flashcard_bank() -> Dict[int, List[Tuple[str, str]]]:
    bank: Dict[int, List[Tuple[str, str]]] = {}
    if not FLASHCARD_DIR.exists():
        return bank

    for path in sorted(FLASHCARD_DIR.glob("Ch_*.txt")):
        chapter_token = path.stem.split("_", 1)[-1]
        try:
            chapter_id = int(chapter_token)
        except ValueError:
            continue
        if chapter_id <= 0:
            continue
        cards = _load_chapter_from_file(path)
        if cards:
            bank[chapter_id] = cards
    return bank


def get_flashcards(conn, chapter=None):
    bank = load_flashcard_bank()
    if bank:
        if chapter is None:
            merged: List[Tuple[str, str]] = []
            for cards in bank.values():
                merged.extend(cards)
            return merged
        return bank.get(chapter, [])

    if not conn:
        return []

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
        return result[0] if result else DEFAULT_CHATBOT_FALLBACK

def get_chapter_ids(conn) -> List[int]:
    bank_chapters = [chapter for chapter in sorted(load_flashcard_bank().keys()) if chapter > 0]
    if bank_chapters:
        return bank_chapters

    default_chapters = [1, 2, 3, 4, 5, 6, 8, 9, 12, 23]
    if not conn:
        return default_chapters
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT chapter FROM flashcards WHERE chapter IS NOT NULL ORDER BY chapter;")
            rows = [row[0] for row in cur.fetchall()]
        cleaned_rows = [row for row in rows if isinstance(row, int) and row > 0]
        return cleaned_rows or default_chapters
    except Exception:
        return default_chapters

if "screen" not in st.session_state:
    st.session_state.screen = "chatbot"
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
if "feedback" not in st.session_state:
   st.session_state.feedback = None

def reset_learning_state():
    st.session_state.card_index = 0
    st.session_state.show_answer = False
    st.session_state.last_result = None
    st.session_state.feedback = None

try:
   conn = init_connection()
   fallback_message = get_fallback_message(conn)
except Exception as e:
   fallback_message = "⚠️ Could not connect to the database."
   st.error(f"Database error: {e}")
   conn = None

def render_bubble(role: str, text: str, ts_iso: Optional[str] = None):
    """Render a chat bubble with timestamp below."""
    if ts_iso:
        try:
            dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
            if dt.tzinfo is None and APP_TZ:
                dt = dt.replace(tzinfo=APP_TZ)
        except Exception:
            dt = now_in_app_tz()
    else:
        dt = now_in_app_tz()

    time_str = format_ts(dt)
    safe_text = escape(text)

    if role == "user":
        row_class = "user-row"
        bubble_class = "user-bubble"
        meta_class = "user-meta"
        content_html = f'<span class="avatar-emoji">🧑</span><div class="bubble {bubble_class}">{safe_text}</div>'
    else:
        row_class = "assistant-row"
        bubble_class = "assistant-bubble"
        meta_class = "assistant-meta"
        content_html = f'<div class="bubble {bubble_class}">{safe_text}</div><span class="avatar-emoji">🤖</span>'

    st.markdown(
        f"""
        <div class='chat-row {row_class}'>
          {content_html}
        </div>
        <div class='chat-meta {meta_class}'>{time_str}</div>
        """,
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.header("StudyBuddies")

    col_chat, col_cards, col_quiz = st.columns(3)
    with col_chat:
        if st.button("💬", help="Chatbot", use_container_width=True):
            st.session_state.screen = "chatbot"
            st.rerun()
    with col_cards:
        if st.button("📖", help="Flashcards", use_container_width=True):
            st.session_state.screen = "flashcards"
            st.rerun()
    with col_quiz:
        if st.button("📝", help="Quiz", use_container_width=True):
            st.session_state.screen = "quiz"
            st.rerun()


   st.markdown("---")

    if st.session_state.screen == "chatbot":
        if st.button("Clear Chat History 🗑️", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    else:
        st.markdown("### Chapters")
        for chapter_id in get_chapter_ids(conn):
            if st.button(
                f"Chapter {chapter_id}",
                key=f"chapter_{chapter_id}",
                use_container_width=True,
            ):
                st.session_state.chapter = chapter_id
                reset_learning_state()
                st.rerun()

if st.session_state.screen == "chatbot":
   st.title("🤓💻 SWE Chatbot")

    if not st.session_state.messages:
        st.markdown(
            """
            <div class="chat-row center-row">
              <div class="bubble assistant-bubble welcome-bubble">
                Hi! How can I help with <strong>Software Engineering</strong> today?<br/>
                Ask about concepts, exam prep, or anything in the syllabus and I'll assist.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    for message in st.session_state.messages:
        render_bubble(message.get("role", "assistant"), message.get("content", ""), message.get("ts"))

    prompt = st.chat_input("Ask me anything about the course material or syllabus…")
    if prompt is not None and prompt.strip() == "":
        st.warning("Please provide input")
    elif prompt:
        user_dt = now_in_app_tz()
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "ts": user_dt.isoformat(),
        })
        render_bubble("user", prompt, user_dt.isoformat())

        message_placeholder = st.empty()
        full_response = ""

        assistant_response = _generate_chatbot_answer(prompt, fallback=fallback_message)
        if not assistant_response:
            assistant_response = fallback_message

        for chunk in assistant_response.split():
            full_response += chunk + " "
            safe_partial = escape(full_response) + "▌"
            message_placeholder.markdown(
                f"""
                <div class=\"chat-row assistant-row\">
                  <div class=\"bubble assistant-bubble\">{safe_partial}</div>
                  <span class=\"avatar-emoji\">🤖</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            time.sleep(0.05)

        asst_dt = now_in_app_tz()
        safe_final = escape(full_response.strip())
        message_placeholder.markdown(
            f"""
            <div class=\"chat-row assistant-row\">
              <div class=\"bubble assistant-bubble\">{safe_final}</div>
            <span class=\"avatar-emoji\">🤖</span>
            </div>
            <div class=\"chat-meta assistant-meta\">{format_ts(asst_dt)}</div>
            """,
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response.strip(),
            "ts": asst_dt.isoformat(),
        })

else:
    is_flashcards = st.session_state.screen == "flashcards"

    if is_flashcards:
        top_cols = st.columns([1, 1])
        with top_cols[0]:
            st.title("📖 Flashcards Mode")
        with top_cols[1]:
            if st.button("Switch to Quiz Mode 📝", key="quiz_switch_top"):
                st.session_state.screen = "quiz"
                st.rerun()
    else:
        top_cols = st.columns([1, 1])
        with top_cols[0]:
            st.title("📝 Quiz Mode")
        with top_cols[1]:
            if st.button("Switch to Flashcards Mode 📖", key="flashcard_switch_top"):
                st.session_state.screen = "flashcards"
                st.rerun()

    try:
        flashcards = (
            get_flashcards(conn, st.session_state.chapter)
            if st.session_state.chapter
            else []
        )
    except Exception:
        flashcards = []

    if not st.session_state.chapter:
        st.markdown("### Choose a chapter from the sidebar to begin.")
    elif not flashcards:
        st.warning("No flashcards found for this chapter.")
    else:
        total_cards = len(flashcards)
        st.session_state.card_index %= total_cards
        question, answer = flashcards[st.session_state.card_index]
        card_content = answer if st.session_state.show_answer else question

        st.markdown(
            f"""
            <div class=\"flashcard-custom\" style="
                width: 500px;
                height: 300px;
                margin: 20px auto;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 12px;
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

        if is_flashcards:
            col_flip, _, _ = st.columns([1, 1, 1])
            with col_flip:
                if st.button("Flip Card 🔄"):
                    st.session_state.show_answer = not st.session_state.show_answer
                    st.session_state.last_result = None
                    st.session_state.feedback = None
                    st.rerun()
        else:
            st.markdown(
                """
                <style>
                div[data-testid="stTextInput"] input {
                    text-align: center;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            user_answer = st.text_input("Your Answer:")
            if st.button("Submit Answer"):
                if user_answer.strip() == "":
                    st.warning("Please provide input")
                    st.stop()
                try:
                    feedback_prompt = f"""
                    A student is being quizzed on Software Engineering.
                    The question was: \"{question}\"
                    The correct answer is: \"{answer}\".
                    The student's answer was: \"{user_answer}\".

                    Provide brief, constructive feedback in 2-3 sentences.
                    Begin your response with \"Correct.\" if the student's answer sufficiently conveys the same ideas.
                    Otherwise, begin with \"Incorrect.\", and explain the disconnect without giving the answer away.
                    """
                    response = client.chat.completions.create(
                        model="gpt-5-nano",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful and encouraging teaching assistant.",
                            },
                            {"role": "user", "content": feedback_prompt},
                        ],
                    )
                    st.session_state.feedback = response.choices[0].message.content
                    if "incorrect" in (st.session_state.feedback or "").lower():
                        st.session_state.last_result = "incorrect"
                    else:
                        st.session_state.last_result = "correct"
                except Exception as e:
                    st.session_state.feedback = f"⚠️ Could not generate feedback: {e}"
                    st.session_state.last_result = "incorrect"

                st.session_state.show_answer = True
                st.rerun()

            if st.session_state.feedback:
               with st.expander("🤖 Show AI Feedback", expanded=True):
                   st.info(st.session_state.feedback)

        st.markdown("---")
        nav_left, nav_center, nav_right = st.columns([1, 0.5, 1])
        with nav_left:
            if st.button("⬅️ Back"):
                st.session_state.card_index = (st.session_state.card_index - 1) % total_cards
                st.session_state.show_answer = False
                st.session_state.last_result = None
                st.session_state.feedback = None
                st.rerun()
        with nav_center:
            if st.session_state.last_result == "correct":
                st.markdown("<h3 style='text-align:center;'>✅</h3>", unsafe_allow_html=True)
            elif st.session_state.last_result == "incorrect":
                st.markdown("<h3 style='text-align:center;'>❌</h3>", unsafe_allow_html=True)
            else:
                st.markdown("&nbsp;", unsafe_allow_html=True)
        with nav_right:
            if st.button("Next ➡️"):
                st.session_state.card_index = (st.session_state.card_index + 1) % total_cards
                st.session_state.show_answer = False
                st.session_state.last_result = None
                st.session_state.feedback = None
                st.rerun()
