import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from openai import embeddings
from openai import OpenAI

load_dotenv()


def load_documents(docs_path="data"):

  if not os.path.exists(docs_path):
    raise FileNotFoundError(f"The directory {docs_path} does not exist.")
  
  documents = []
  
  # Load PDF files
  pdf_loader = DirectoryLoader(
    path=docs_path,
    glob="*.pdf",
    loader_cls=PyPDFLoader
  )
  documents.extend(pdf_loader.load())
  
  # Load TXT files
  txt_loader = DirectoryLoader(
    path=docs_path,
    glob="*.txt",
    loader_cls=TextLoader
  )
  documents.extend(txt_loader.load())

  if len(documents) == 0:
    raise FileNotFoundError(f"The directory {docs_path} is empty, please add files.")
  
  return documents

def chunk_documents(documents, chunk_size=800, chunk_overlap=0):

  # Splitting documents into smaller chunks
  text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
  )
  
  chunks = text_splitter.split_documents(documents)

  return chunks

def create_embedding(chunks, persist_directory="dataset/chroma_db"):

  embedding_model = OpenAIEmbeddings(model='google/gemma-3-12b-it')

  vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding_model,
    persist_directory=persist_directory,
    collection_metadata={"hnsw:space": "cosine"},
  )

  return vectorstore


def main():

  docs_path="data"
  persist_directory="dataset/chroma_db"

  # Loading documents from the "data" directory
  documents = load_documents(docs_path)

  # Spliting documents into smaller chunks
  chunks = chunk_documents(documents, chunk_size=800, chunk_overlap=200)

  # Creating embeddings for the split documents
  embeddings = create_embedding(chunks, persist_directory)

  # Store embeddings in Chroma vector database
  #chroma_db = Chroma(collection_name="my_collection", embedding_function=embeddings)
  #chroma_db.add_documents(split_documents, doc_embeddings)



if __name__ == "__main__":
  main()