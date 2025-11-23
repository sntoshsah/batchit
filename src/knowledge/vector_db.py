from pymilvus import MilvusClient
from pymilvus import model

from pymilvus import MilvusClient

client = MilvusClient(
    uri="http://localhost:19530",
    token="root:Milvus"
)

databases = client.list_databases()
print("Databases:", databases)


if not "KnowledgeDB" in databases:
    client.create_database(
        db_name="KnowledgeDB"
    )

client.use_database("KnowledgeDB")

collection_name = "knowledge_base"

if  not client.has_collection(collection_name="knowledge_base"):
    client.create_collection(
        collection_name=collection_name,
        dimension=768,  # The vectors we will use in this demo has 768 dimensions
    )


embedding_fn = model.DefaultEmbeddingFunction()

docs = [
    "Artificial intelligence was founded as an academic discipline in 1956.",
    "Alan Turing was the first person to conduct substantial research in AI.",
    "Born in Maida Vale, London, Turing was raised in southern England.",
]

vectors = embedding_fn.encode_documents(docs)
print("Dim:", embedding_fn.dim, vectors[0].shape)  # Dim: 768 (768,)

data = [
    {"id": i, "vector": vectors[i], "text": docs[i], "subject": "history"}
    for i in range(len(vectors))
]

print("Data has", len(data), "entities, each with fields: ", data[0].keys())
print("Vector dim:", len(data[0]["vector"]))

client.insert(
    collection_name=collection_name,
    data=data,
)


