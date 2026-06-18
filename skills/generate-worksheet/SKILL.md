---
name: generate-worksheet
description: Generates a comprehensive educational worksheet based on user-provided topic, using relevant documents from the ChromaDB vector database. Supports mixed question formats, difficulty levels, and source citations.
parameters:
  - name: topic
    type: string
    description: The topic or subject for which the worksheet should be generated.
  - name: difficulty
    type: string
    description: Difficulty level - "easy", "medium", or "hard". Affects question complexity and depth.
  - name: number_of_questions
    type: integer
    description: The number of questions to include in the worksheet (recommended 5-15).
  - name: include_answer_key
    type: boolean
    default: true
    description: Whether to include an answer key with the worksheet.
  - name: include_citations
    type: boolean
    default: true
    description: Whether to include source document citations.
---

# Generate Worksheet Skill

## Overview
This skill enables the agent to create customized educational worksheets by:
1. Retrieving relevant documents from the ChromaDB vector database
2. Extracting key concepts and information from those documents
3. Generating varied question types based on the difficulty level
4. Optionally creating answer keys and source citations

## Workflow

### Step 1: Document Retrieval
- Use the retrieval pipeline to search ChromaDB with the provided topic
- Retrieve 3-5 of the most relevant documents based on semantic similarity
- Store the retrieved documents and their sources for later citation

**Key functions to use:**
- `query_chroma_db(topic)` - searches the vector database
- Extract document content and metadata (source, page numbers if available)

### Step 2: Content Analysis
- Analyze retrieved documents to identify:
  - Main concepts and definitions
  - Key facts and examples
  - Important relationships between concepts
  - Common misconceptions or edge cases
- Prioritize content based on relevance to the topic

### Step 3: Question Generation

Generate questions in **mixed formats** based on difficulty:

#### Easy Level (Beginner):
- **Definition questions**: "What is [concept]?"
- **Recall questions**: "According to the document, what are the main characteristics of [topic]?"
- **True/False statements**: Based on facts from the documents
- Require direct retrieval from source material

#### Medium Level (Intermediate):
- **Application questions**: "How would you apply [concept] to [scenario]?"
- **Comparison questions**: "Compare and contrast [concept A] with [concept B]"
- **Short answer questions**: "Explain why [fact/concept] is important in [context]"
- Require some interpretation and synthesis

#### Hard Level (Advanced):
- **Analysis questions**: "Why does [phenomenon] occur based on [concept]?"
- **Synthesis questions**: "How do [concept A], [concept B], and [concept C] relate to solve [problem]?"
- **Critical thinking**: "What would happen if [condition changed]? Explain your reasoning."
- **Evaluation questions**: "Assess the validity of [statement] based on the evidence presented."
- Require higher-order thinking and synthesis across multiple concepts

### Step 4: Answer Key Generation (if requested)
- Provide concise, accurate answers (1-3 sentences for short answers)
- Include key points that should be covered
- For multiple choice: list the correct option
- Reference the source document section where the answer is found

### Step 5: Source Citation (if requested)
- Include citations in format: `[Source: Document Name, Section]`
- Track which document each question is based on
- Maintain document titles/references for transparency

## Output Format (Plain Text)

```
═══════════════════════════════════════════════════════════════
WORKSHEET: [Topic]
Difficulty Level: [Easy/Medium/Hard]
Number of Questions: [X]
═══════════════════════════════════════════════════════════════

QUESTIONS:

1. [Question Type] - [Question text]
   [Source: Document Name]

2. [Question Type] - [Question text]
   [Source: Document Name]

---Additional questions continue---

═══════════════════════════════════════════════════════════════
ANSWER KEY:

1. [Answer]
   [Key points/Explanation]

2. [Answer]
   [Key points/Explanation]

---Additional answers continue---
```

## Best Practices

1. **Relevance**: Ensure all questions directly relate to the retrieved documents
2. **Variety**: Mix question types to maintain engagement and test different cognitive levels
3. **Clarity**: Use clear, unambiguous language without unnecessary jargon
4. **Accuracy**: Verify all facts against the source documents
5. **Progression**: Order questions from foundational to more complex
6. **Citations**: Always track source documents for transparency and verification

## Key Considerations

- If fewer than 3 relevant documents found, inform the user and offer to adjust the topic
- Balance the mix of question types (e.g., 40% recall, 40% application, 20% analysis for medium level)
- Adjust question complexity by varying sentence structure, technical depth, and scenario complexity
- For citations, include enough detail so a user can locate the information in the source

## Integration Notes

- Works with the existing retrieval_pipeline.py and ChromaDB setup
- Requires access to document metadata for proper citation tracking
- Difficulty adjustment should affect not just complexity but also required depth of knowledge
