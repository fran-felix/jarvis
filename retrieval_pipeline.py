import os
import json
import re
from pydantic import SecretStr
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from journal import JournalDB
from ingestion_pipeline import ingestion_pipeline

load_dotenv()

"""LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8081/v1")
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
)"""

# Global journal database instance - persists across all function calls
_journal_db = None

def get_journal_db():
    """Get or initialize the global journal database instance"""
    global _journal_db
    if _journal_db is None:
        _journal_db = JournalDB()
    return _journal_db

def close_journal_db():
    """Close the global journal database instance"""
    global _journal_db
    if _journal_db is not None:
        _journal_db.close()
        _journal_db = None

# Tool schemas for the model
TOOLS_SCHEMA = [
    {
        "name": "add_task",
        "description": "Add a new task to the journal database",
        "parameters": {
            "title": "str - Title of the task (required)",
            "description": "str - Description of the task (optional)",
            "category": "str - Category: 'test', 'essay', 'class', or 'other' (default: 'other')",
            "due_date": "str - Due date in format DD/MM/YYYY (optional)",
            "course": "str - Course or subject name (optional)",
            "completed": "bool - Whether the task is completed (default: False)"
        }
    },
    {
        "name": "list_tasks",
        "description": "Retrieve all tasks from the journal database with optional filtering",
        "parameters": {
            "category": "str - Filter by category (optional)",
            "completed": "bool - Filter by completion status (optional)",
            "course": "str - Filter by course (optional)",
            "due_before": "str - Filter tasks due before this date (optional)",
            "due_after": "str - Filter tasks due after this date (optional)"
        }
    },
    {
        "name": "mark_task_completed",
        "description": "Mark a task as completed or incomplete in the database",
        "parameters": {
            "task_id": "int - The ID of the task (required)",
            "completed": "bool - True to mark as completed, False to mark as incomplete (default: True)"
        }
    },
    {
        "name": "add_class_session",
        "description": "Add a class session to the weekly schedule. Classes cannot overlap.",
        "parameters": {
            "course": "str - Course name (required)",
            "day_of_week": "str - Day: 'Monday' through 'Sunday' (required)",
            "start_time": "str - Start time in HH:MM format (required)",
            "end_time": "str - End time in HH:MM format (required)",
            "location": "str - Class location (optional)",
            "notes": "str - Additional notes (optional)"
        }
    },
    {
        "name": "list_class_schedule",
        "description": "Retrieve the class schedule with optional filtering",
        "parameters": {
            "course": "str - Filter by course (optional)",
            "day_of_week": "str - Filter by day of week (optional)"
        }
    }
]

def format_tools_context():
    """Format tool definitions for the model"""
    tools_text = "You have access to the following tools:\n\n"
    for tool in TOOLS_SCHEMA:
        tools_text += f"Tool: {tool['name']}\n"
        tools_text += f"Description: {tool['description']}\n"
        tools_text += "Parameters:\n"
        for param, description in tool['parameters'].items():
            tools_text += f"  - {param}: {description}\n"
        tools_text += "\n"
    return tools_text

def extract_tool_calls(response_text):
    """Extract tool calls from model response in JSON format"""
    tool_calls = []
    
    print(f"\n[DEBUG] Model response:\n{response_text}")
    
    # Find all potential JSON objects by looking for { and matching }
    i = 0
    while i < len(response_text):
        # Find opening brace
        start = response_text.find('{', i)
        if start == -1:
            break
        
        # Check if this looks like a tool call by searching ahead for "tool_name"
        if '"tool_name"' not in response_text[start:start+200]:
            i = start + 1
            continue
        
        # Find matching closing brace by counting braces
        brace_count = 0
        end = start
        for j in range(start, len(response_text)):
            if response_text[j] == '{':
                brace_count += 1
            elif response_text[j] == '}':
                brace_count -= 1
            
            if brace_count == 0:
                end = j + 1
                break
        
        if end > start:
            json_str = response_text[start:end]
            try:
                tool_call = json.loads(json_str)
                if "tool_name" in tool_call:
                    tool_calls.append(tool_call)
                    print(f"[DEBUG] Tool call extracted: {tool_call}")
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Failed to parse JSON: {e}")
            
            i = end
        else:
            i = start + 1
    
    print(f"[DEBUG] Found {len(tool_calls)} tool calls in response")
    return tool_calls

def execute_tool_call(tool_call):
    """Execute a single tool call and return the result"""
    try:
        journal_db = get_journal_db()
        tool_name = tool_call.get("tool_name")
        parameters = tool_call.get("parameters", {})
        
        print(f"\n[DEBUG] Executing tool: {tool_name}")
        print(f"[DEBUG] Parameters: {parameters}")
        print(f"[DEBUG] Database path: {journal_db.db_path}")
        
        if tool_name == "add_task":
            result = journal_db.add_task(**parameters)
            print(f"[DEBUG] Task added with ID: {result}")
            return {"success": True, "message": f"Task added with ID: {result}"}
        
        elif tool_name == "list_tasks":
            tasks = journal_db.list_tasks(**parameters)
            print(f"[DEBUG] Found {len(tasks)} tasks")
            task_list = []
            for task in tasks:
                task_list.append({
                    "id": task.id,
                    "title": task.title,
                    "category": task.category,
                    "due_date": task.due_date,
                    "course": task.course,
                    "completed": task.completed,
                    "description": task.description
                })
            return {"success": True, "tasks": task_list}
        
        elif tool_name == "mark_task_completed":
            success = journal_db.mark_task_completed(**parameters)
            status = "completed" if parameters.get("completed", True) else "marked as incomplete"
            print(f"[DEBUG] Task marked as {status}, success: {success}")
            return {"success": success, "message": f"Task {status}"}
        
        elif tool_name == "add_class_session":
            result = journal_db.add_class_session(**parameters)
            print(f"[DEBUG] Class session added with ID: {result}")
            return {"success": True, "message": f"Class session added with ID: {result}"}
        
        elif tool_name == "list_class_schedule":
            sessions = journal_db.list_class_schedule(**parameters)
            print(f"[DEBUG] Found {len(sessions)} class sessions")
            session_list = []
            for session in sessions:
                session_list.append({
                    "id": session.id,
                    "course": session.course,
                    "day_of_week": session.day_of_week,
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "location": session.location,
                    "notes": session.notes
                })
            return {"success": True, "sessions": session_list}
        
        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    except Exception as e:
        error_msg = f"Tool execution error: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": error_msg}


def _normalize_content(content):
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content)
    except TypeError:
        return str(content)

# Handler to load vectorstore even without an embedding model (in case you have a database already processed)
def load_vectorstore(persist_directory="dataset/chroma_db"):
    if os.path.exists(persist_directory):
        return Chroma(persist_directory=persist_directory)
    return ingestion_pipeline()

def retrieval_pipeline(query):
    
    vectorstore = load_vectorstore() # insert directory here if it's another one
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": 3,
            "score_threshold": 0.5
        }
    )

    relevant_docs = retriever.invoke(query)
    tools_context = format_tools_context()

    combined_input = f"""Using the following documents and available tools, considering what the query is requiring, answer this request : {query}

{tools_context}

Documents:
{chr(10).join([f"- {doc.page_content}" for doc in relevant_docs])}

IMPORTANT: When the user is asking you to perform an action (like adding a task, viewing tasks, marking tasks complete, or viewing the schedule), respond with a JSON tool call in this format:
{{"tool_name": "function_name", "parameters": {{"param1": "value1", "param2": "value2"}}}}

For example:
{{"tool_name": "add_task", "parameters": {{"title": "Study for exam", "category": "test", "due_date": "31/05/2026"}}}}

If the user is asking for information, first try to answer using the documents provided. If you need to use a tool to answer, include the JSON tool call above.
Only Answer with information provided within the documents, if you cannot answer based on the documents, inform that you could not find the information.
"""
    
    model_name = os.getenv("MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
    chat_api_key = os.getenv("CHAT_API_KEY")
    openai_api_key = SecretStr(chat_api_key) if chat_api_key is not None else None
    base_url = os.getenv("CHAT_BASE_URL")

    model = ChatOpenAI(
        model=model_name,
        api_key=openai_api_key,
        base_url=base_url
    )

    messages = [
        SystemMessage(content="You are a helpful academic assistant that can access a student's journal database. You understand the user's needs and can perform actions using the available tools."),
        HumanMessage(content=combined_input),
    ]

    result = model.invoke(messages)
    content = _normalize_content(result.content)

    documents = ""
    for i, doc in enumerate(relevant_docs, 1):
        documents += f"Document {i}:\n{doc.page_content}\n\n"

    # Extract and execute tool calls
    tool_calls = extract_tool_calls(content)
    tool_results = []
    final_response = content  # Default to original response if no tool calls
    
    print(f"\n[DEBUG] Total tool calls to execute: {len(tool_calls)}")
    
    if tool_calls:
        for i, tool_call in enumerate(tool_calls):
            print(f"\n[DEBUG] Executing tool call {i+1}/{len(tool_calls)}")
            result = execute_tool_call(tool_call)
            tool_results.append(result)
            print(f"[DEBUG] Tool call result: {result}")
        
        # Get natural language response from model after tool execution
        print("\n[DEBUG] Generating natural language response from tool results...")
        
        # Format tool results for the model
        tool_results_text = "Tool Execution Results:\n"
        for i, result in enumerate(tool_results, 1):
            tool_results_text += f"\nTool Call {i}:\n"
            if result.get("success"):
                tool_results_text += f"Status: Success\n"
                for key, value in result.items():
                    if key != "success":
                        if isinstance(value, list):
                            tool_results_text += f"{key}: {len(value)} items found\n"
                            for item in value[:3]:  # Show first 3 items
                                tool_results_text += f"  - {item}\n"
                        else:
                            tool_results_text += f"{key}: {value}\n"
            else:
                tool_results_text += f"Status: Failed\nError: {result.get('error', 'Unknown error')}\n"
        
        # Create follow-up message with tool results
        follow_up_prompt = f"""Based on the tool execution results below, provide a natural language response to the user's original query: "{query}"

{tool_results_text}

Please provide a clear, concise, and helpful response in natural language that incorporates the information from the tool results. Be conversational and friendly."""
        
        # Get natural language response
        # Need to add AIMessage with the initial tool call response to maintain proper alternation
        follow_up_messages = messages + [
            AIMessage(content=content),
            HumanMessage(content=follow_up_prompt)
        ]
        
        follow_up_result = model.invoke(follow_up_messages)
        final_response = _normalize_content(follow_up_result.content)
        
        print(f"[DEBUG] Natural language response generated")
    else:
        print("[DEBUG] No tool calls extracted from model response")
    
    answer = {
        "query": f"User Query: {query}\n\n--- Context ---\n",
        "documents": documents,
        "content": "--- Answer ---\n\n" + final_response + '\n',
        "tool_calls": tool_calls,
        "tool_results": tool_results
    }

    return answer