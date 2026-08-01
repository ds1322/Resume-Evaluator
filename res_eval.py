import os
import json
import io
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, ValidationError
from pypdf import PdfReader

# ----------------------------
# Load Environment Variables
# ----------------------------
# Works locally (.env file) AND on Streamlit Community Cloud (st.secrets)
load_dotenv()

my_api_key = os.getenv("GROQ_API_KEY")

if not my_api_key:
    try:
        my_api_key = st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        my_api_key = None

if not my_api_key:
    st.error(
        "GROQ_API_KEY not found. "
        "Locally: add it to a .env file. "
        "On Streamlit Cloud: add it under App settings → Secrets."
    )
    st.stop()

client = Groq(api_key=my_api_key)
model = "llama-3.3-70b-versatile"

# ----------------------------
# Pydantic Schemas
# ----------------------------
class Resume(BaseModel):
    name: str
    email: str
    phone: str
    education: str
    experience: str
    skills: list[str]
    projects: list[str]

class ResumeEvaluation(BaseModel):
    overall_score: int
    technical_skills: int
    projects: int
    education: int
    experience: int
    communication: int
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str

schema = Resume.model_json_schema()
evaluation_schema = ResumeEvaluation.model_json_schema()

response_format = {"type": "json_object"}

system_prompt = f"""
You are an expert Resume Parser.

Extract information from the resume.

Return ONLY valid JSON.

Follow this JSON schema exactly.

{schema}
"""

evaluation_system_prompt = f"""
You are an expert HR Recruiter.

Evaluate the candidate's resume.

Scoring rules (IMPORTANT):
- overall_score, technical_skills, projects, education, experience, and communication
  must ALL be integers on a scale of 0 to 100 (where 100 is the best possible score).
- Do NOT use a 1-10 scale. A strong candidate should score in the 70-95 range,
  an average candidate in the 40-70 range, and a weak candidate below 40.
- Be realistic and use the full range — do not default to low scores like 5-10
  unless the resume is genuinely very poor or largely empty.

Return ONLY valid JSON.

Follow this JSON schema exactly.

{evaluation_schema}
"""

message_system = {"role": "system", "content": system_prompt}
evaluation_message_system = {"role": "system", "content": evaluation_system_prompt}

# ----------------------------
# Output folders
# ----------------------------
PARSED_DIR = "Parsed_Resumes"
EVAL_DIR = "Evaluated_Resumes"
os.makedirs(PARSED_DIR, exist_ok=True)
os.makedirs(EVAL_DIR, exist_ok=True)


# ----------------------------
# Helper: extract text from PDF or DOCX
# ----------------------------
def extract_text(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text

    elif name.endswith(".docx"):
        try:
            import docx
        except ImportError:
            st.error("python-docx is not installed. Run: pip install python-docx")
            return ""
        document = docx.Document(uploaded_file)
        text = "\n".join(p.text for p in document.paragraphs if p.text)
        return text

    else:
        return ""


# ----------------------------
# Helper: call LLM and parse JSON
# ----------------------------
def call_llm(messages):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format
    )
    return json.loads(response.choices[0].message.content)


# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="Resume Parser & Evaluator", layout="wide")

st.title("📄 Resume Parser & Evaluator")
st.write("Drag and drop resumes (PDF or DOCX) below. Each one will be parsed and evaluated automatically.")

uploaded_files = st.file_uploader(
    "Drop resumes here",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button(f"Process {len(uploaded_files)} resume(s)"):

        for uploaded_file in uploaded_files:
            st.divider()
            st.subheader(f"📎 {uploaded_file.name}")

            try:
                text = extract_text(uploaded_file)

                if not text.strip():
                    st.warning("No extractable text found (possibly a scanned/image file). Skipped.")
                    continue

                with st.spinner("Parsing resume..."):
                    parse_messages = [
                        message_system,
                        {"role": "user", "content": f"Parse the following resume.\n\nResume:\n\n{text}"}
                    ]
                    data = call_llm(parse_messages)
                    resume = Resume(**data)

                base_name = os.path.splitext(uploaded_file.name)[0]

                # Save parsed JSON
                parsed_path = f"{PARSED_DIR}/{base_name}.json"
                with open(parsed_path, "w") as f:
                    json.dump(data, f, indent=4)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Extracted Info**")
                    st.write(f"**Name:** {resume.name}")
                    st.write(f"**Email:** {resume.email}")
                    st.write(f"**Phone:** {resume.phone}")
                    st.write(f"**Education:** {resume.education}")
                    st.write(f"**Experience:** {resume.experience}")
                    st.write(f"**Skills:** {', '.join(resume.skills)}")
                    st.write(f"**Projects:** {', '.join(resume.projects)}")

                with st.spinner("Evaluating resume..."):
                    eval_messages = [
                        evaluation_message_system,
                        {"role": "user", "content": f"Evaluate the following candidate based on their resume data.\n\nResume Data:\n\n{json.dumps(data, indent=2)}"}
                    ]
                    eval_data = call_llm(eval_messages)
                    evaluation = ResumeEvaluation(**eval_data)

                eval_path = f"{EVAL_DIR}/{base_name}.json"
                with open(eval_path, "w") as f:
                    json.dump(eval_data, f, indent=4)

                with col2:
                    st.markdown("**Evaluation**")
                    st.write(f"**Overall Score:** {evaluation.overall_score}/100")
                    st.write(f"**Technical Skills:** {evaluation.technical_skills}")
                    st.write(f"**Projects:** {evaluation.projects}")
                    st.write(f"**Education:** {evaluation.education}")
                    st.write(f"**Experience:** {evaluation.experience}")
                    st.write(f"**Communication:** {evaluation.communication}")
                    st.write(f"**Strengths:** {', '.join(evaluation.strengths)}")
                    st.write(f"**Weaknesses:** {', '.join(evaluation.weaknesses)}")
                    st.write(f"**Recommendation:** {evaluation.recommendation}")

                st.success(f"Saved to {parsed_path} and {eval_path}")

                dcol1, dcol2 = st.columns(2)
                with dcol1:
                    st.download_button(
                        "⬇️ Download parsed JSON",
                        data=json.dumps(data, indent=4),
                        file_name=f"{base_name}_parsed.json",
                        mime="application/json",
                        key=f"parsed_{uploaded_file.name}"
                    )
                with dcol2:
                    st.download_button(
                        "⬇️ Download evaluation JSON",
                        data=json.dumps(eval_data, indent=4),
                        file_name=f"{base_name}_evaluation.json",
                        mime="application/json",
                        key=f"eval_{uploaded_file.name}"
                    )

            except json.JSONDecodeError as e:
                st.error(f"Failed to parse JSON from model response: {e}")
            except ValidationError as e:
                st.error(f"Schema validation failed: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
else:
    st.info("Upload one or more resumes to get started.")
