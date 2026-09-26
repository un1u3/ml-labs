import glob
import os

import chromadb
from pypdf import PdfReader

DB_PATH = os.getenv("CHROMA_PATH", "./chroma_data")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "80"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "20"))
client = chromadb.PersistentClient(path=DB_PATH)
collection = None


def chunk(text, size=80, overlap=20):
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words), 1), step)]


def use_chunking(size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    global collection
    collection = client.get_or_create_collection(f"docs_{size}_{overlap}")  # default embedding model
    return ingest(size=size, overlap=overlap)


def ingest(folder="docs", size=None, overlap=None):
    if collection is None:
        return use_chunking()
    if collection.count() > 0:
        return collection.count()
    size, overlap = size or CHUNK_SIZE, overlap or CHUNK_OVERLAP
    ids, texts, metas = [], [], []
    for path in glob.glob(os.path.join(folder, "*.pdf")):
        name = os.path.basename(path)
        for p, page in enumerate(PdfReader(path).pages, start=1):
            for i, c in enumerate(chunk(page.extract_text() or "", size, overlap)):
                if c.strip():
                    ids.append(f"{name}-{p}-{i}")
                    texts.append(c)
                    metas.append({"source": name, "page": p})
    if ids:
        collection.add(ids=ids, documents=texts, metadatas=metas)
    return len(ids)


def search(query, k=4):
    if collection is None:
        use_chunking()
    res = collection.query(query_texts=[query], n_results=k)
    return [
        {"text": d, "source": m["source"], "page": m["page"]}
        for d, m in zip(res["documents"][0], res["metadatas"][0])
    ]
