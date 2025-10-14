import streamlit as st
import psycopg2

# Connect to the PostgreSQL database (container name = db)
conn = psycopg2.connect(
    host="db",
    database="postgres",
    user="postgres",
    password="postgres"
)

cur = conn.cursor()
cur.execute("SELECT content FROM messages LIMIT 1;")
message = cur.fetchone()[0]

# Streamlit page setup
st.set_page_config(page_title="Dummy App", layout="centered")

# Display text on white background, black text
st.markdown(f"<h2 style='color:black;text-align:center;'>{message}</h2>", unsafe_allow_html=True)

cur.close()
conn.close()