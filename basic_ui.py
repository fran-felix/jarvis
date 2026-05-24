from retrieval_pipeline import retrieval_pipeline

# Simple handler for AI agent interaction through the terminal

def talk():
  
  while True:
    print("Type to chat with Jarvis or say EXIT to end conversation:\n")
    query = input()
    if query == "EXIT":
      break
    for msg in retrieval_pipeline(query).values():
      print(msg)


def main() -> None:
  talk()


if __name__ == "__main__":
  main()