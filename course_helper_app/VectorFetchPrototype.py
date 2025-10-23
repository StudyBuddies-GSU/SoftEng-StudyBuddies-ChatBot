# rag_cli.py
# ---------------------------------------
# 🔑 Replace YOUR_API_KEY_HERE below with your actual OpenAI API key
#OPENAI_API_KEY = ""
# rag_cli.py
# ---------------------------------------

from openai import OpenAI
from pathlib import Path

MODEL = "gpt-4o-mini"
VECTOR_STORE_NAME = "vector1"  # use only this store

# initialize client
client = OpenAI(api_key=OPENAI_API_KEY)

def get_vector_store_by_name(name: str):
    """Find a vector store by name (does NOT create new ones)."""
    cursor = None
    while True:
        page = client.vector_stores.list(after=cursor) if cursor else client.vector_stores.list()
        for vs in page.data:
            if vs.name == name:
                return vs
        if not page.has_more:
            break
        cursor = page.last_id
    return None

store = get_vector_store_by_name(VECTOR_STORE_NAME)
if not store:
    print(f"❌ Vector store '{VECTOR_STORE_NAME}' not found. Exiting.")
    raise SystemExit

def list_files_in_store(store_id: str):
    """List all files in the given store."""
    out = []
    cursor = None
    while True:
        page = client.vector_stores.files.list(vector_store_id=store_id, after=cursor) if cursor \
               else client.vector_stores.files.list(vector_store_id=store_id)
        out.extend(page.data)
        if not page.has_more:
            break
        cursor = page.last_id
    return out

def attach_local_file(store_id: str, path: str):
    """Attach a local file to the store."""
    p = Path(path)
    if not p.exists():
        print(f"❌ File not found: {path}")
        return
    f = client.files.create(file=open(p, "rb"), purpose="assistants")
    client.vector_stores.files.create(vector_store_id=store_id, file_id=f.id)
    print(f"✅ Attached {p.name} to '{VECTOR_STORE_NAME}'.")

def ask(store_id: str, question: str, chapter: str | None):
    """Send a retrieval-augmented query."""
    prefix = f"Only use content from Chapter {chapter}. " if chapter else ""
    prompt = prefix + question
    resp = client.responses.create(
        model=MODEL,
        input=prompt,
        tools=[{"type": "file_search", "vector_store_ids": [store_id]}],
    )
    print("\n--- Answer ---")
    print(resp.output_text.strip())
    print("--------------\n")

def help_text():
    print(
"""Commands:
/chapter <num|name>   – Set a chapter scope (use /chapter off to clear)
/list                 – List files in the vector store
/add <path>           – Upload and attach a local file
/help                 – Show help
/quit                 – Exit program
Just type your question to ask the model.
"""
    )

def main():
    chapter = None
    print(f"\n✅ Connected to vector store '{VECTOR_STORE_NAME}' ({store.id})")
    print("💬 Type /help for available commands.\n")

    while True:
        try:
            line = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not line:
            continue

        if line.startswith("/"):
            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd == "/help":
                help_text()
            elif cmd == "/quit":
                print("Bye!")
                break
            elif cmd == "/chapter":
                if arg.lower() in ("", "off", "none"):
                    chapter = None
                    print("🔹 Chapter scope cleared.")
                else:
                    chapter = arg
                    print(f"🔹 Chapter scope set to: {chapter}")
            elif cmd == "/list":
                files = list_files_in_store(store.id)
                if not files:
                    print("No files in store.")
                else:
                    for f in files:
                        print(f"- {f.id}  name={getattr(f,'file','?')}")
            elif cmd == "/add":
                if not arg:
                    print("Usage: /add <path-to-file>")
                else:
                    attach_local_file(store.id, arg)
            else:
                print("Unknown command. Try /help.")
            continue

        ask(store.id, line, chapter)

if __name__ == "__main__":
    main()
