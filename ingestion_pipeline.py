import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from openai import embeddings

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



def main():

  # Load documents from the "data" directory
  documents = load_documents(docs_path="data")

  # Split documents into smaller chunks
  chunks = chunk_documents(documents, chunk_size=800, chunk_overlap=200)

  # Create embeddings for the split documents
  #embeddings = OpenAIEmbeddings()
  #doc_embeddings = embeddings.embed_documents([doc.page_content for doc in split_documents])

  # Store embeddings in Chroma vector database
  #chroma_db = Chroma(collection_name="my_collection", embedding_function=embeddings)
  #chroma_db.add_documents(split_documents, doc_embeddings)



if __name__ == "__main__":
  main()