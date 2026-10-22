from pathlib import Path
import hashlib

from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


DATA_DIR = Path("data")
DB_DIR = "chroma_db"


def file_hash(file_path):
    """
    Erstellt einen eindeutigen Hash für eine Datei.
    Wenn sich der Dateiinhalt ändert, ändert sich auch der Hash.
    """
    hasher = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_documents():
    documents = []

    for file_path in DATA_DIR.iterdir():

        if not file_path.is_file():
            continue

        current_hash = file_hash(file_path)

        if file_path.suffix.lower() == ".txt":
            text = file_path.read_text(encoding="utf-8")

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": file_path.name,
                        "file_hash": current_hash
                    }
                )
            )

        elif file_path.suffix.lower() == ".pdf":
            reader = PdfReader(file_path)

            for page_number, page in enumerate(reader.pages, start=1):
                text = page.extract_text()

                if text and text.strip():
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": file_path.name,
                                "page": page_number,
                                "file_hash": current_hash
                            }
                        )
                    )

    return documents


# 1. Dateien laden
documents = load_documents()

print(f"{len(documents)} Dokumentabschnitte geladen.")


# 2. Dokumente in Chunks zerlegen
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150
)

chunks = text_splitter.split_documents(documents)

print(f"{len(chunks)} Chunks erstellt.")


# 3. Embedding-Modell
embeddings = OllamaEmbeddings(
    model="nomic-embed-text"
)


# 4. Persistente ChromaDB laden
vectorstore = Chroma(
    collection_name="local_knowledge",
    embedding_function=embeddings,
    persist_directory=DB_DIR
)


# 5. Bereits gespeicherte Datei-Hashes auslesen
existing_data = vectorstore.get(
    include=["metadatas"]
)

existing_hashes = set()

for metadata in existing_data["metadatas"]:
    if metadata and "file_hash" in metadata:
        existing_hashes.add(metadata["file_hash"])


# 6. Nur neue Dateien indexieren
new_chunks = [
    chunk
    for chunk in chunks
    if chunk.metadata.get("file_hash") not in existing_hashes
]

if new_chunks:
    vectorstore.add_documents(new_chunks)

    print(
        f"{len(new_chunks)} neue Chunks "
        f"zur Datenbank hinzugefügt."
    )

else:
    print("Keine neuen Dateien gefunden.")


# 7. Lokales LLM
llm = ChatOllama(
    model="llama3.2:3b"
)


# 8. Fragen stellen
while True:

    question = input("\nFrage: ")

    if question.lower() == "exit":
        print("Programm beendet.")
        break


    results = vectorstore.similarity_search(
        question,
        k=4
    )


    context = "\n\n".join(
        f"Quelle: {doc.metadata}\n{doc.page_content}"
        for doc in results
    )


    prompt = f"""
Answer the question only using the provided context.

If the answer is not contained in the context, say:
"I don't know based on the available documents."

Context:
{context}

Question:
{question}
"""


    response = llm.invoke(prompt)


    print("\nAntwort:")
    print(response.content)


    print("\nQuellen:")

    for doc in results:
        print(doc.metadata)