from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain.agents import create_agent


DB_DIR = "chroma_db"


# --------------------------------------------------
# Embedding-Modell und bestehende ChromaDB laden
# --------------------------------------------------

embeddings = OllamaEmbeddings(
    model="nomic-embed-text"
)

vectorstore = Chroma(
    collection_name="local_knowledge",
    embedding_function=embeddings,
    persist_directory=DB_DIR
)


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

    print(f"\n[TOOL] Calculator benutzt: {expression}")

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
# TOOL 2: Lokale Dokumente durchsuchen
# --------------------------------------------------

@tool
def search_documents(query: str) -> str:
    """
    Durchsucht die lokalen Dokumente in der ChromaDB.

    Nutze dieses Tool, wenn eine Frage Informationen
    aus den lokalen Dokumenten des Benutzers benötigt.
    """

    print(f"\n[TOOL] Dokumentensuche benutzt: {query}")

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
# Lokales LLM
# --------------------------------------------------

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0
)


# --------------------------------------------------
# Agent erstellen
# --------------------------------------------------

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
   contained in their local documents, use the
   search_documents tool.

2. If the user asks for a mathematical calculation,
   use the calculator tool.

3. Do not invent information from local documents.

4. If the document search does not contain the answer,
   clearly say that you could not find it.

5. Answer clearly and concisely.
"""
)


# --------------------------------------------------
# Chat
# --------------------------------------------------

print("Local AI Agent gestartet.")
print("Tools: Calculator + lokale Dokumentensuche")
print("Tippe 'exit', um das Programm zu beenden.\n")


messages = []


while True:

    user_input = input("Du: ")

    if user_input.lower() == "exit":
        print("Agent beendet.")
        break

    messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    result = agent.invoke(
        {
            "messages": messages
        }
    )

    messages = result["messages"]

    final_message = messages[-1]

    print("\nAI:", final_message.content)
    print()