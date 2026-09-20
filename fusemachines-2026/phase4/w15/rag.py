import glob
import os

import chromadb
from pypdf import PdfReader

DB_PATH = os.getenv("CHROMA_PATH", "./chroma_data")
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection("docs")  # default embedding model, stored in chroma


def chunk(text, size=80, overlap=20):
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words), 1), step)]


def ingest(folder="docs"):
    if collection.count() > 0:
        return collection.count()
    ids, texts, metas = [], [], []
    for path in glob.glob(os.path.join(folder, "*.pdf")):
        name = os.path.basename(path)
        for p, page in enumerate(PdfReader(path).pages, start=1):
            for i, c in enumerate(chunk(page.extract_text() or "")):
                if c.strip():
                    ids.append(f"{name}-{p}-{i}")
                    texts.append(c)
                    metas.append({"source": name, "page": p})
    if ids:
        collection.add(ids=ids, documents=texts, metadatas=metas)
    return len(ids)


def search(query, k=4):
    res = collection.query(query_texts=[query], n_results=k)
    return [
        {"text": d, "source": m["source"], "page": m["page"]}
        for d, m in zip(res["documents"][0], res["metadatas"][0])
    ]
