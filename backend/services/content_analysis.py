from pydantic import BaseModel #BaseModel is used to follow that structure strictly
from google import genai
from backend.config import settings #object which has the key
import re
import httpx


#creating basemodel structure
#this is called by a function with a type to check if the variable is following these conditions
class InputFormat(BaseModel) :
    student_id : int
    resume_text : str
    certification_details : str
    @model_validator(mode="after") #@ is used to connect the function following to pydantic
    def checkinput(self):
        if not self.resume_text.strip() and not self.certification_details.strip():
            raise ValueError("Please provide either resume or certification details")
        return self

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

async def analyzeprofile(payload:InputFormat)->dict:
    client = genai.Client(api_key=settings["GEMINI_API_KEY"])

    github_code= await fetchgithubcode(payload.resume_text)

    prompt = f"Analyze profile for student : {payload.student_id}"

    if payload.resume_text.strip():
        prompt+=f"Resume: {payload.resume_text}"

    if github_code:
        prompt+=f"Raw Project Code : {github_code}"

    if payload.certification_details.strip():
        prompt+=f"Certification Details:{payload.certification_details}"
    
    prompt+=(
        "INSTRUCTIONS:"
        "1.Read the repository files to find the actual programming languages and skills used"
        "2.For projects with broken links or code , infer the requirements from the repository title"
        "3.Find the skills and concepts learned from the certification details"
        "Generate a final structured skill analysis report"
    )

    #async function
    response = await client.aio.models.generate_content(
        model = 'gemini-2.5-flash',
        contents = prompt

    ) 

    return{
        "student_id": payload.student_id,
        "analysis": response.text,
        "repos found": bool(github_code)
    }