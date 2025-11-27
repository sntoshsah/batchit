from data_preprocess import embed_text
from vector_db import client



QUERY_EMBEDDING_MODEL = "all-minilm"
def get_query_embedding(text: str):
    resp = embed_text(text)
    return resp


def similarity_search(query_embedding, top_k=5):
    # This function should interact with the vector database to retrieve similar items
    client.use_database("KnowledgeDB")
    collection_name = "knowledge_base"
    search_params = {
        "metric_type": "COSINE",
        # "params": {"nprobe": 10},
    }
    results = client.search(
        collection_name=collection_name,
        data=[query_embedding],
        anns_field="vector",
        search_params=search_params,
        limit=top_k,
        output_fields=["text"]
    )
    return results

if __name__ == "__main__":
    sample_text = """Supply a minimum of 24 SFP ports (100/1000 Mbps) with 24 
compatible 1G SFP single-mode LC modules (20 km range, transmitter 
and receiver), 4 SFP uplink ports (1/10 Gbps) with 4 compatible 10G 
single-mode dual-fiber modules (20 km range, transmitter and 
receiver), fully compatible with all OEM products,"""
    embedding = get_query_embedding(sample_text)
    results = similarity_search(embedding, top_k=3)
    print("Search Results:", results)
