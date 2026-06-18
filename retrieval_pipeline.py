import os
import json
import re
from datetime import datetime
from pydantic import SecretStr
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from journal import JournalDB
from ingestion_pipeline import ingestion_pipeline
load_dotenv()

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
    },
    {
        "name": "generate_worksheet",
        "description": "Generate an educational worksheet on a given topic using retrieved documents. This tool loads the worksheet generation skill instructions and applies them to create a customized worksheet with questions, answer keys, and citations.",
        "parameters": {
            "topic": "str - The topic for the worksheet (required)",
            "difficulty": "str - Difficulty level: 'easy', 'medium', or 'hard' (default: 'medium')",
            "number_of_questions": "int - Number of questions to generate (default: 10, recommended 5-15)",
            "include_answer_key": "bool - Whether to include an answer key (default: True)",
            "include_citations": "bool - Whether to include source citations (default: True)"
        }
    }
]

def load_retrieval_tools_skill():
    """Load the retrieval-pipeline-tools SKILL.md for system context"""
    skill_path = "skills/retrieval-pipeline-tools/SKILL.md"
    try:
        if os.path.exists(skill_path):
            with open(skill_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            print(f"[WARNING] Retrieval pipeline tools SKILL.md not found at {skill_path}")
            return ""
    except Exception as e:
        print(f"[WARNING] Could not read retrieval pipeline tools SKILL.md: {e}")
        return ""

def get_current_datetime_context():
    """Get current date and time in a formatted context for the agent"""
    now = datetime.now()
    
    day_name = now.strftime("%A")
    date_formatted = now.strftime("%d/%m/%Y")  # DD/MM/YYYY format for task dates
    time_formatted = now.strftime("%H:%M")      # HH:MM format for class times
    
    weekday_number = now.weekday()  # 0=Monday, 6=Sunday
    week_number = now.isocalendar()[1]
    
    context = f"""CURRENT DATE AND TIME CONTEXT:
- Date: {date_formatted} ({day_name})
- Time: {time_formatted} (24-hour format)
- Week Number: {week_number}
- ISO Weekday: {weekday_number} (0=Monday, 6=Sunday)

IMPORTANT: Use these values when:
- Creating tasks with due dates (format: DD/MM/YYYY)
- Adding class sessions (use day name: Monday-Sunday)
- Setting class times (use 24-hour format: HH:MM)
- Filtering tasks by date ranges (use DD/MM/YYYY format)"""
    
    return context

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
        
        elif tool_name == "generate_worksheet":
            topic = parameters.get("topic")
            if not topic:
                return {"success": False, "error": "Topic is required for worksheet generation"}
            
            # Load the SKILL.md file for worksheet generation instructions
            skill_path = "skills/generate-worksheet/SKILL.md"
            skill_instructions = ""
            
            try:
                if os.path.exists(skill_path):
                    with open(skill_path, 'r', encoding='utf-8') as f:
                        skill_instructions = f.read()
                    print(f"[DEBUG] Loaded SKILL.md from {skill_path}")
                else:
                    print(f"[WARNING] SKILL.md not found at {skill_path}")
            except Exception as e:
                print(f"[WARNING] Could not read SKILL.md: {e}")
            
            difficulty = parameters.get("difficulty", "medium")
            number_of_questions = parameters.get("number_of_questions", 10)
            include_answer_key = parameters.get("include_answer_key", True)
            include_citations = parameters.get("include_citations", True)
            
            # Retrieve documents for the topic
            vectorstore = load_vectorstore()
            retriever = vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"k": 5, "score_threshold": 0.4}
            )
            documents = retriever.invoke(topic)
            
            if not documents:
                return {"success": False, "error": f"No documents found for topic: {topic}"}
            
            print(f"[DEBUG] Retrieved {len(documents)} documents for worksheet generation")
            
            # Prepare document context
            doc_context = ""
            for i, doc in enumerate(documents, 1):
                source = doc.metadata.get("source", "Unknown") if hasattr(doc, "metadata") else "Unknown"
                content = doc.page_content if hasattr(doc, "page_content") else str(doc)
                if len(content) > 1000:
                    content = content[:1000] + "..."
                doc_context += f"Document {i} (Source: {source}):\n{content}\n\n"
            
            # Define question generation instructions based on difficulty
            difficulty_instructions = {
                "easy": f"""Generate {number_of_questions} EASY level questions including:
- 40% Definition/Recall questions (What, Who, When, Where)
- 40% True/False statements
- 20% Simple comprehension questions
Questions should require direct retrieval from source material.""",
                
                "medium": f"""Generate {number_of_questions} MEDIUM level questions including:
- 30% Recall/Comprehension questions
- 40% Application and Comparison questions
- 30% Short answer questions requiring analysis
Questions should require interpretation and synthesis of information.""",
                
                "hard": f"""Generate {number_of_questions} HARD level questions including:
- 20% Analysis questions (Why, How does this relate)
- 40% Synthesis questions (combining multiple concepts)
- 20% Critical thinking questions (What if, evaluate validity)
- 20% Evaluation questions
Questions should require higher-order thinking and reasoning.""",
            }
            
            instructions = difficulty_instructions.get(difficulty.lower(), difficulty_instructions["medium"])
            
            # Prepare the LLM prompt with SKILL.md guidance
            prompt = f"""You are an expert educational content creator generating a worksheet. 
Follow these skill guidelines:

SKILL INSTRUCTIONS:
{skill_instructions}

---

Now, based on the documents below about "{topic}", generate exactly {number_of_questions} {difficulty} level questions for an educational worksheet.

DOCUMENTS:
{doc_context}

SPECIFIC INSTRUCTIONS FOR THIS WORKSHEET:
{instructions}

Generate questions following the format specified in the skill instructions. Ensure all questions are:
- Based directly on the provided documents
- Accurate and verifiable
- Appropriate for {difficulty} level learners
- Varied in type for better engagement

Format your response with clear Q# labels and structure."""
            
            # Generate questions using LLM
            model_name = os.getenv("MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
            chat_api_key = os.getenv("CHAT_API_KEY")
            openai_api_key = SecretStr(chat_api_key) if chat_api_key is not None else None
            base_url = os.getenv("CHAT_BASE_URL")
            
            model = ChatOpenAI(
                model=model_name,
                api_key=openai_api_key,
                base_url=base_url,
                temperature=0.7
            )
            
            messages = [
                SystemMessage(content="You are an expert educational content creator. Generate high-quality worksheet questions based on provided documents and skill guidelines. Always base questions on document content and ensure accuracy."),
                HumanMessage(content=prompt)
            ]
            
            result = model.invoke(messages)
            questions_response = _normalize_content(result.content)
            
            # Format the final worksheet
            worksheet = []
            worksheet.append("=" * 65)
            worksheet.append(f"WORKSHEET: {topic.upper()}")
            worksheet.append(f"Difficulty Level: {difficulty.capitalize()}")
            worksheet.append(f"Number of Questions: {number_of_questions}")
            worksheet.append("=" * 65)
            worksheet.append("")
            worksheet.append("QUESTIONS:")
            worksheet.append("")
            worksheet.append(questions_response)
            
            if include_answer_key:
                # Generate answer key using skill guidelines
                answer_prompt = f"""Using the same skill guidelines mentioned before:

SKILL INSTRUCTIONS:
{skill_instructions}

---

Based on the documents and questions below, generate concise answers for each question following the skill's answer key guidelines.

DOCUMENTS:
{doc_context}

QUESTIONS:
{questions_response}

Provide answers following the format specified in the skill instructions. For each answer:
- Include 1-3 key points that should be covered
- Reference the source document when applicable
- Ensure accuracy based on provided documents"""
                
                answer_messages = [
                    SystemMessage(content="You are an expert educator creating answer keys. Provide accurate, concise answers based on provided documents and skill guidelines."),
                    HumanMessage(content=answer_prompt)
                ]
                
                answer_result = model.invoke(answer_messages)
                answers_response = _normalize_content(answer_result.content)
                
                worksheet.append("")
                worksheet.append("=" * 65)
                worksheet.append("ANSWER KEY:")
                worksheet.append("=" * 65)
                worksheet.append("")
                worksheet.append(answers_response)
            
            if include_citations:
                worksheet.append("")
                worksheet.append("=" * 65)
                worksheet.append("SOURCES:")
                worksheet.append("=" * 65)
                for i, doc in enumerate(documents, 1):
                    source = doc.metadata.get("source", "Unknown") if hasattr(doc, "metadata") else "Unknown"
                    worksheet.append(f"Document {i}: {source}")
            
            return {"success": True, "worksheet": "\n".join(worksheet), "message": f"Worksheet on '{topic}' generated successfully using skill guidelines"}
        
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


def _get_embedding_function():
    return OpenAIEmbeddings(
        model=os.getenv("LOCAL_EMBEDDING_MODEL", "Qwen3-Embedding-8B-Q5_K_M-GGUF"),
        base_url=os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8081/v1"),
        api_key=os.getenv("LOCAL_API_KEY", "local"),  # type: ignore
        check_embedding_ctx_length=False,
    )

# Handler to load vectorstore even without an embedding model (in case you have a database already processed)
def load_vectorstore(persist_directory="dataset/chroma_db"):
    if os.path.exists(persist_directory):
        return Chroma(
            persist_directory=persist_directory,
            embedding_function=_get_embedding_function(),
        )
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
    
    # Load the retrieval-pipeline-tools skill for system context
    tools_skill = load_retrieval_tools_skill()
    
    # Get current date and time context
    datetime_context = get_current_datetime_context()
    

    combined_input = f"""Using the following documents and available tools, considering what the query is requiring, answer this request : {query}

{tools_context}

Documents:
{chr(10).join([f"- {doc.page_content}" for doc in relevant_docs])}

IMPORTANT: When the user is asking you to perform an action (like adding a task, viewing tasks, marking tasks complete, viewing the schedule, or generating a worksheet), respond with a JSON tool call in this format:
{{"tool_name": "function_name", "parameters": {{"param1": "value1", "param2": "value2"}}}}

For example:
{{"tool_name": "add_task", "parameters": {{"title": "Study for exam", "category": "test", "due_date": "31/05/2026"}}}}
{{"tool_name": "generate_worksheet", "parameters": {{"topic": "Renewable Energy", "difficulty": "medium", "number_of_questions": 10}}}}

For the generate_worksheet tool: The tool will automatically load the skill instructions (SKILL.md) and apply them to generate a high-quality worksheet with questions, answer keys, and citations based on your parameters.

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

    # Build system message with tool skill context and datetime awareness
    system_message = f"""You are a helpful academic assistant named Jarvis that can access a student's journal database. You understand the user's needs and can perform actions using the available tools.

{datetime_context}

---

TOOL USAGE GUIDELINES:
Please refer to the following comprehensive skill guide for optimal tool usage and understanding:

{tools_skill}

---

Use this skill guide to:
- Select the appropriate tools for the user's request
- Understand all available parameters and their requirements
- Follow best practices for data integrity and efficiency
- Choose proper filter combinations for efficient queries
- Generate quality worksheets with appropriate difficulty levels
- Manage tasks and schedules effectively
- Always use the current date/time context provided above when creating or filtering tasks and schedules
"""

    messages = [
        SystemMessage(content=system_message),
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
                        elif key == "worksheet" and isinstance(value, str):
                            # For worksheet, include the full content
                            tool_results_text += f"{key}:\n{value}\n"
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