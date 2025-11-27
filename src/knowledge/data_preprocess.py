from pypdf import PdfReader
from ollama import embed
import os


file_list = os.listdir("uploaded_docs/")





def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def embed_text(text):
    # Placeholder for embedding logic
    resp = embed(input=text, model="all-minilm")
    return resp.embeddings[0]




if __name__ == "__main__":
    for file_name in file_list:
        print("Processing file:", file_name)
        file_path = os.path.join("uploaded_docs/", file_name)
    extracted_text = extract_text_from_pdf(file_path)
    embedding = embed_text(extracted_text)
    # print(embedding)  # Print the length of the embedding vector
    print(type(embedding))
    print(dir(embedding))