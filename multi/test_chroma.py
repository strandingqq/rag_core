from pathlib import Path
import sys
import os
import chromadb
import langchain_chroma

from chroma_store import init_chroma_db

persist_dir = Path(os.environ.get("CHROMA_PERSIST_DIR", "chroma_all_v2")).resolve()
collection_name = "question"

print("python:", sys.executable)
print("cwd:", os.getcwd())
print("chromadb:", chromadb.__version__)
print("langchain_chroma:", langchain_chroma.__file__)
print("persist_dir:", persist_dir)
if not str(persist_dir).isascii():
    print("warning: persist_dir contains non-ASCII characters; Chroma on Windows may fail to load HNSW indexes.")

db = init_chroma_db(str(persist_dir), collection_name)
print(db._collection.count())

docs = db.similarity_search(
    "React 中 useEffect 的依赖数组有什么作用？",
    k=3,
)
for i , doc in enumerate(docs, 1):
    print("doc i")
    print(type(doc))
    print(doc.page_content)