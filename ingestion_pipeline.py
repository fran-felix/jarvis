import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from openai import embeddings

load_dotenv()


def load_documents(docs_path="documents"):

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
  
  for i, doc in enumerate(documents[:5]):
    print(f"\nDocument {i+1}:")
    print(f"  Source: {doc.metadata['source']}")
    print(f"  Content length: {len(doc.page_content)} characters")
    print(f"  Content preview: {doc.page_content[:100]}...")
    print(f"  metadata: {doc.metadata}")
  
  return documents


def main():
  # Load documents from the "data" directory
  documents = load_documents(docs_path="documents")


  # Split documents into smaller chunks
  #text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
  #split_documents = text_splitter.split_documents(documents)

  # Create embeddings for the split documents
  #embeddings = OpenAIEmbeddings()
  #doc_embeddings = embeddings.embed_documents([doc.page_content for doc in split_documents])

  # Store embeddings in Chroma vector database
  #chroma_db = Chroma(collection_name="my_collection", embedding_function=embeddings)
  #chroma_db.add_documents(split_documents, doc_embeddings)



if __name__ == "__main__":
  main()