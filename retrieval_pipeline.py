import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()



LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8081/v1")
EMBEDDING_MODEL_NAME = os.getenv(
  "EMBEDDING_MODEL_NAME",
  "Qwen3-Embedding-8B-Q5_K_M-GGUF",
)

persistent_directory = "dataset/chroma_db"

embedding_model = OpenAIEmbeddings(
    model=EMBEDDING_MODEL_NAME,
    base_url=LOCAL_LLM_BASE_URL,
    api_key=os.getenv("OPENAI_API_KEY", "local"), # type: ignore
    check_embedding_ctx_length=False,
  )

vectorstore = Chroma(
    persist_directory=persistent_directory,
    embedding_function=embedding_model,
    collection_metadata={"hnsw:space": "cosine"}
)

query = "what is a chromosome?"

#retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={
        "k": 3,
        "score_threshold": 0.5
    }
)

relevant_docs = retriever.invoke(query)

# print(f"User Query: {query}")
# print("--- Context ---")
# for i, doc in enumerate(relevant_docs, 1):
#     print(f"Document {i}:\n{doc.page_content}\n")

combined_input = f"""Based on the following documents, please answer this question: {query}

Documents:
{chr(10).join([f"- {doc.page_content}" for doc in relevant_docs])}

Please provide a clear, helpful answer using only the information from these documents. If you can't find the answer in the documents, say "I don't have enough information to answer that question based on the provided documents."
"""

model = ChatOpenAI(model = "google/gemma-3-12b-it", api_key = os.getenv("CHAT_API_KEY"), base_url = os.getenv("CHAT_BASE_URL"))

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content=combined_input),
]

result = model.invoke(messages)

print(result.content)