Skill: generate_exercise_skill
1. Description

This skill enables the AI study assistant to retrieve and assemble a customized list of practice exercises from the educational database. It is designed to test the student's knowledge, reinforce learning, and provide structured study materials based on a specific academic subject or topic.
2. Triggers & Intent

Activate this skill when the user explicitly or implicitly requests to be tested, wants to practice, or asks for review questions.

Trigger Phrases:

    "Can you test me on..."

    "Give me some practice questions for..."

    "I need to review..."

    "Let's do some exercises about..."

    "Quiz me on..."

3. Inputs (Parameters)

Extract the following parameters from the user's prompt to formulate the database query:

    subject (Required, String): The core topic, concept, or academic subject the user wants to practice (e.g., "Photosynthesis", "Fractions", "The Cold War").

    difficulty (Optional, String): The desired challenge level.

        Valid values: beginner, intermediate, advanced, mixed.

        Default: mixed.

    question_count (Optional, Integer): The number of questions requested.

        Min/Max: 1 to 20.

        Default: 5.

4. Execution Rules

When assembling and presenting the exercise list, strictly adhere to the following guidelines:

    Hide the Answers: NEVER output the correct answers or explanations in the initial response. Present only the questions and any multiple-choice options. Store the answers in your context window to evaluate the student's subsequent replies.

    Formatting: Present the exercises in a clear, numbered list. Use bold text for the question and bullet points for multiple-choice options (if applicable).

    Missing Data Fallback: If the database returns zero results for the requested subject, apologize politely and suggest 2-3 broader, related topics that are available in the database.

    Encouragement: End the generation with a brief, encouraging prompt asking the student to provide their answers when they are ready.

5. Expected Output Format
Markdown

Here are [question_count] practice questions about [subject] to help you study:

**1. [Text of the first question]**
* A) [Option 1]
* B) [Option 2]
* C) [Option 3]

**2. [Text of the second question]**
*(...continue for the requested number of questions)*

---
Take your time! Whenever you are ready, reply with your answers, and we can go over them together.

6. Examples

Example 1: Specific Request

    User: "Give me 3 advanced questions on cellular respiration."

    Extracted Parameters: subject: "cellular respiration", difficulty: "advanced", question_count: 3

    Action: Retrieve 3 advanced questions from the DB and present them without answers.

Example 2: Vague Request

    User: "I need to practice math."

    Extracted Parameters: subject: "math", difficulty: "mixed", question_count: 5

    Action: Recognize that "math" is too broad.

    Correction: Intercept the execution and ask the user to specify the math topic (e.g., "I'd love to help you practice math! Are we focusing on algebra, geometry, or calculus today?").