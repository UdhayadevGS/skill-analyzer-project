from google import genai
from backend.config import settings #object which has the key
import json
import re
import httpx
import io
from pypdf import PdfReader

#creating basemodel structure
#this is called by a function with a type to check if the variable is following these conditions

def extracttextfrompdf(file_bytes:bytes)->str:
    if not file_bytes:
        return ""

    try:
        pdf_stream = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_stream)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
              text += extracted + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF document structure: {str(e)}")

async def fetchgithubcode(resume_text:str)->str:
    links = re.findall(r"github\.com/([\w-]+)/([\w-]+)", resume_text) #the parenthesis extracts only the user and repo in tuples and adds it to the list
    if not links:
        return "" # No links found skip
     
    codedump=""
    async with httpx.AsyncClient() as client:
# httpx.AsyncClient is used to build a connection with the local python code and the internet (github)
#with is used to automatically close the connection upon completion and we are naming the connection as client
      for username,repo in links:
        api_url = f"https://api.github.com/repos/{username}/{repo}/contents"
        response = await client.get(api_url, headers={"User-Agent": "App"}) #used to send a get request and get the content from the url using the header login info app
        
        if response.status_code==200:
            files=response.json() #converts the response into a json
            codedump+=f"\nRepository : {repo}"

            for file in files[:3]:
                if file["type"]=="file" and file["name"].endswith(('.py', '.js', '.jsx', '.html', '.css')):
                    fileresponse= await client.get(file['download_url'],headers={"User-Agent":"App"})
                    if fileresponse.status_code==200:
                        codedump+=f"File Name is {file['name']}" + fileresponse.text[:800]
        return codedump

def parse_analysis_response(response_text: str, job_preferences: str) -> dict:
    if not response_text:
        response_text = "No analysis text was returned by the AI model."

    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and isinstance(parsed.get("role_scores"), list):
            return parsed
    except json.JSONDecodeError:
        pass

    return {
        "summary": "The AI returned an unstructured report, so the original analysis is shown below.",
        "role_scores": [
            {
                "role": role.strip(),
                "score": None,
                "why": response_text,
                "resume_evidence": "See report text.",
                "certification_evidence": "See report text.",
                "github_evidence": "See report text.",
                "recommendation": "Upload clearer resume, certificate, and GitHub project evidence for a more precise score.",
            }
            for role in job_preferences.split(",")
            if role.strip()
        ],
    }

async def analyzeprofile(job_preferences: str, resume_bytes: bytes, cert_bytes_list: list[bytes]) -> dict:
    client = genai.Client(api_key=settings["GEMINI_API_KEY"])
    resume_text = extracttextfrompdf(resume_bytes)

    # Loop through the list of certificate bytes and combine their text
    cert_text = ""
    for cert_bytes in cert_bytes_list:
        if cert_bytes:
            extracted = extracttextfrompdf(cert_bytes)
            if extracted:
                cert_text += extracted + "\n\n"
    cert_text = cert_text.strip()

    if not resume_text and not cert_text:
        raise ValueError("Both the uploaded resume and certificate PDFs contain no readable text.")

    github_code= await fetchgithubcode(resume_text)

    role_list = [role.strip() for role in job_preferences.split(",") if role.strip()]
    prompt = f"Target Job Preferences: {', '.join(role_list)}\n\n"

    if resume_text:
        prompt+=f"Resume: {resume_text}"

    if github_code:
        prompt+=f"Raw Project Code : {github_code}"

    if cert_text:
        prompt+=f"Certification Details:{cert_text}"
    
    prompt+=(
        "INSTRUCTIONS AND CRITICAL FILTER CONSTRAINTS:\n"
        "1. Focus EXCLUSIVELY on what the student actually built, customized, or configured manually in their code.\n"
        "2. DO NOT attribute core platform/framework languages to the student. For example, if the student built "
        "an n8n workflow or custom node extension, DO NOT state that they have core engineering expertise in Node.js "
        "or TypeScript unless their custom written script logic explicitly proves they wrote those underlying systems from scratch.\n"
        "3. Read the repository files to find the actual programming languages and skills used.\n"
        "4. Find the skills and concepts learned from the certification details.\n\n"
        "MATCHING AND SCORING REQUIREMENT:\n"
        f"Evaluate the user's matching score for EACH requested role: {role_list}.\n"
        "You MUST provide a definitive integer percentage score from 0 to 100 for every role.\n"
        "Keep explanations concise and evidence-based. Do not write long paragraphs.\n"
        "For every role, explain why the score was given using resume evidence, certification evidence, and GitHub/project evidence separately.\n"
        "If evidence is missing, say that clearly. Recommend 2-3 specific actions the user should take to boost the score.\n\n"
        "OUTPUT FORMAT:\n"
        "Return ONLY valid JSON. Do not include markdown fences or extra text.\n"
        "Use this exact structure:\n"
        "{\n"
        '  "summary": "One short overall sentence.",\n'
        '  "role_scores": [\n'
        "    {\n"
        '      "role": "Role name",\n'
        '      "score": 75,\n'
        '      "why": "One short reason for the score.",\n'
        '      "resume_evidence": "Short resume-based evidence.",\n'
        '      "certification_evidence": "Short certificate-based evidence.",\n'
        '      "github_evidence": "Short GitHub/project-based evidence.",\n'
        '      "recommendation": "2-3 concise actions to improve this role score."\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    #async function
    response = await client.aio.models.generate_content(
        model = 'gemini-2.5-flash',
        contents = prompt

    ) 

    analysis_text = response.text or ""
    structured_analysis = parse_analysis_response(analysis_text, job_preferences)

    return{
        "analysis": analysis_text,
        "summary": structured_analysis.get("summary", ""),
        "role_scores": structured_analysis.get("role_scores", []),
        "repos found": bool(github_code)
    }   
