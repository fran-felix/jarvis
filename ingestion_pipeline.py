import os
import unicodedata
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()


def normalize_text(text):

  normalized_text = unicodedata.normalize("NFKC", text)
  normalized_text = normalized_text.replace("\r\n", "\n").replace("\r", "\n")
  normalized_text = "".join(
    char
    for char in normalized_text
    if char in {"\n", "\t"} or not unicodedata.category(char).startswith("C")
  )

  return normalized_text


def normalize_documents(documents):

  normalized_documents = []

  for document in documents:
    document.page_content = normalize_text(document.page_content)
    normalized_documents.append(document)

  return normalized_documents


def load_documents(docs_path="data"):

  if not os.path.exists(docs_path):
    raise FileNotFoundError(f"The directory {docs_path} does not exist.")
  
  documents = []
  
  # Load PDF files
  pdf_loader = DirectoryLoader(
    path=docs_path,
    glob="*.pdf",
    loader_cls=PyPDFLoader # type: ignore
  )
  documents.extend(pdf_loader.load())
  
  # Load TXT files
  txt_loader = DirectoryLoader(
    path=docs_path,
    glob="*.txt",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
  )
  documents.extend(txt_loader.load())

  if len(documents) == 0:
    raise FileNotFoundError(f"The directory {docs_path} is empty, please add files.")
  
  return normalize_documents(documents)


def chunk_documents(documents, chunk_size=800, chunk_overlap=0):

  # Splitting documents into smaller chunks
  text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
  )
  
  chunks = text_splitter.split_documents(documents)

  return chunks


def create_embedding(chunks, persist_directory="dataset/chroma_db"):

  embedding_model = OpenAIEmbeddings(
    model=os.getenv("LOCAL_EMBEDDING_MODEL", "Qwen3-Embedding-8B-Q5_K_M-GGUF"),
    base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8081/v1"),
    api_key=os.getenv("LOCAL_API_KEY", "local"), # type: ignore
    check_embedding_ctx_length=False,
  )

  vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding_model,
    persist_directory=persist_directory,
    collection_metadata={"hnsw:space": "cosine"},
  )

  return vectorstore


def ingestion_pipeline():

  docs_path="data"
  persist_directory="dataset/chroma_db"

  # Loading documents from the "data" directory
  documents = load_documents(docs_path)

  #documents = converter_md()

  #Spliting documents into smaller chunks
  chunks = chunk_documents(documents, chunk_size=800, chunk_overlap=200)

  # Creating embeddings for the split documents
  vectorstore = create_embedding(chunks, persist_directory)

  return vectorstore