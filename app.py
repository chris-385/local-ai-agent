import streamlit as st

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain.agents import create_agent


DB_DIR = "chroma_db"


# --------------------------------------------------
# Streamlit Seite
# --------------------------------------------------

st.set_page_config(
    page_title="Local AI Agent",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Local AI Agent")
st.caption("Lokal mit Ollama, LangChain, ChromaDB und eigenen Dokumenten")


# --------------------------------------------------
# ChromaDB + Embeddings laden
# --------------------------------------------------

@st.cache_resource
def load_vectorstore():

    embeddings = OllamaEmbeddings(
        model="nomic-embed-text"
    )

    vectorstore = Chroma(
        collection_name="local_knowledge",
        embedding_function=embeddings,
        persist_directory=DB_DIR
    )

    return vectorstore


vectorstore = load_vectorstore()


# --------------------------------------------------
# TOOL 1: Rechner
# --------------------------------------------------

@tool
def calculator(expression: str) -> str:
    """
    Berechnet mathematische Ausdrücke.
    Nutze dieses Tool für Berechnungen.
    Beispiel: 25 * 4 + 10
    """

    try:
        allowed_chars = "0123456789+-*/(). "

        if not all(char in allowed_chars for char in expression):
            return "Ungültiger mathematischer Ausdruck."

        result = eval(
            expression,
            {"__builtins__": {}}
        )

        return str(result)

    except Exception as error:
        return f"Fehler bei der Berechnung: {error}"


# --------------------------------------------------
# TOOL 2: Dokumentensuche
# --------------------------------------------------

@tool
def search_documents(query: str) -> str:
    """
    Durchsucht die lokalen Dokumente in der ChromaDB.

    Nutze dieses Tool, wenn eine Frage Informationen
    aus den lokalen Dokumenten benötigt.
    """

    results = vectorstore.similarity_search(
        query,
        k=4
    )

    if not results:
        return "Keine passenden Informationen gefunden."

    context_parts = []

    for doc in results:

        source = doc.metadata.get(
            "source",
            "Unbekannte Quelle"
        )

        page = doc.metadata.get("page")

        if page:
            source_info = f"{source}, Seite {page}"
        else:
            source_info = source

        context_parts.append(
            f"Quelle: {source_info}\n"
            f"Inhalt: {doc.page_content}"
        )

    return "\n\n".join(context_parts)


# --------------------------------------------------
# Agent laden
# --------------------------------------------------

@st.cache_resource
def load_agent():

    llm = ChatOllama(
        model="llama3.2:3b",
        temperature=0
    )

    agent = create_agent(
        model=llm,

        tools=[
            calculator,
            search_documents
        ],

        system_prompt="""
You are a helpful local AI assistant.

You have access to tools.

Rules:

1. If the user asks about information that may be
   contained in local documents, use the
   search_documents tool.

2. If the user asks for a mathematical calculation,
   use the calculator tool.

3. Do not invent information from local documents.

4. If the document search does not contain the answer,
   clearly say that you could not find it.

5. Answer clearly and concisely.

6. Reply in the same language as the user.
"""
    )

    return agent


agent = load_agent()


# --------------------------------------------------
# Chat-Verlauf
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


# Vorherige Nachrichten anzeigen
for message in st.session_state.messages:

    role = message["role"]
    content = message["content"]

    if role == "user":

        with st.chat_message("user"):
            st.markdown(content)

    elif role == "assistant":

        with st.chat_message("assistant"):
            st.markdown(content)


# --------------------------------------------------
# Eingabefeld
# --------------------------------------------------

user_input = st.chat_input(
    "Schreibe eine Nachricht..."
)


if user_input:

    # User-Nachricht speichern
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    # User-Nachricht anzeigen
    with st.chat_message("user"):
        st.markdown(user_input)


    # Agent ausführen
    with st.chat_message("assistant"):

        with st.spinner("Denke nach..."):

            result = agent.invoke(
                {
                    "messages": st.session_state.messages
                }
            )

            final_message = result["messages"][-1]

            answer = final_message.content

        st.markdown(answer)


    # Antwort speichern
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )