### AI Resume Parser & Evaluator | Python, Streamlit, LLM (Groq API), Pydantic


•	Built an AI-powered tool using the Groq LLM API to automatically parse resumes (PDF/DOCX) into structured,schema-validated data and generate HR-style candidate evaluations with scores and recommendations.

•	Designed reliable structured-output prompts with Pydantic schema validation to ensure consistent, JSON-safeLLM responses.

•	Implemented a two-stage LLM pipeline: resume parsing (name, education, skills, experience, projects) followedby automated evaluation across technical skills, projects, education, experience and communication.

•	Added robust error handling for malformed AI responses and unreadable files, with per-file isolation so one failuredoesn't stop batch processing.
•	Deployed a live, public Streamlit web app with drag-and-drop multi-resume upload and downloadable results.


App Link :- https://resume-evaluator-syqne5rocxthgpp8zgy6bi.streamlit.app/
