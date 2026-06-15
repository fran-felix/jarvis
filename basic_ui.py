from retrieval_pipeline import retrieval_pipeline, close_journal_db
from journal import JournalDB

# Simple handler for AI agent interaction through the terminal

def talk():
  
  while True:
    print("Type to chat with Jarvis or say EXIT to end conversation:\n")
    query = input()
    if query == "EXIT":
      break
    
    result = retrieval_pipeline(query)
    
    # Display the answer
    print(result.get("content", ""))
    
    # Display tool results if any
    if result.get("tool_results"):
      print("\n--- Tool Execution Results ---")
      for i, tool_result in enumerate(result["tool_results"], 1):
        if tool_result.get("success"):
          print(f"Tool {i} - Success: {tool_result}")
        else:
          print(f"Tool {i} - Error: {tool_result.get('error', 'Unknown error')}")
      print("--- End Tool Results ---\n")


def main() -> None:
  try:
    talk()
  finally:
    close_journal_db()


if __name__ == "__main__":
  main()