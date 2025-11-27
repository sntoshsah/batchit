import os
from pymilvus import MilvusClient
from data_preprocess import extract_text_from_pdf, embed_text
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

if client.has_collection(collection_name=collection_name):
    client.drop_collection(collection_name=collection_name)

if  not client.has_collection(collection_name="knowledge_base"):
    client.create_collection(
        collection_name=collection_name,
        dimension=384,  # The vectors we will use in this demo has 384 dimensions
    )


file_list = os.listdir("uploaded_docs/")
for file_name in file_list:
    print("Processing file:", file_name)
    file_path = os.path.join("uploaded_docs/", file_name)
    extracted_text = extract_text_from_pdf(file_path)
    embedding = embed_text(extracted_text)
    text = extract_text_from_pdf(file_path)
    vector = embed_text(text)

    client.insert(
        collection_name="knowledge_base",
        data=[
            {
                "id": 1,
                "text": text,
                "vector": vector  # (should be a list of floats)
            }
        ]
    )

# print(client.get_collection_stats(collection_name=collection_name))

# print(client.list_collections())
# print(client.describe_collection(collection_name=collection_name))