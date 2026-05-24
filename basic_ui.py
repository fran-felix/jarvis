# Simple handler for AI agent interaction through the terminal

def talk():
  
  print("Type to chat with Jarvis or say EXIT to end conversation:")
  while True:
    query = input()
    # Send query to AI model, invoke retrieval_pipeline operations
    # Print answer and loop back
    print("Looping...")
    if query == "EXIT":
      break


def main() -> None:
  talk()


if __name__ == "__main__":
  main()