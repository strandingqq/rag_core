from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

""" 
主要用于Chroma db 的初始化创建和修改

init_chroma_db 初始化并连接db
add_documents_to_chroma 将组织好的document导入db
"""


def init_chroma_db(persist_dir, collection_name):
    """ 
    初始化 HuggingFace embedding 模型，并连接指定目录和 collection 的 Chroma 数据库。

    Args:
        persist_dir(str) db存储位置
        collection_name(str) db的collection名

    Returns:
        需要用一个db去接受 Chroma向量数据库对象
    """
    emb = HuggingFaceEmbeddings(
        model_name = "sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs = {"device":"cuda"},
        encode_kwargs={"normalize_embeddings": True}
    )

    db = Chroma(
        persist_directory=persist_dir,
        collection_name=collection_name,
        embedding_function=emb,
    )  
    return db

def add_documents_to_chroma(db, documents, ids):
    """ 
    把 Document 列表和对应 ID 写入 Chroma collection。

    Args:
        db:Chroma对象
        Documents
        ids
    
    Returns:
        写入文档后的Chroma数据库对象
    """
    db.add_documents(documents, ids=ids)
    return db