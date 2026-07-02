from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from backend.services.content_analysis import analyzeprofile

app = FastAPI(
    title = "AI Skill Analyzer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all addresses
    allow_credentials=True,
    allow_methods=["*"],  # Allows all actions like GET, POST
    allow_headers=["*"],
)

@app.get("/")
def readingroot():
    return {"status":"online"}
    
@app.post("/api/analyze-profile")
async def processprofile(
    job_preferences: str = Form(...),                  
    resume_file: UploadFile | None = File(None),               
    certificate_files: list[UploadFile] | None = File(None)
):
    try:
       resume_bytes = await resume_file.read() if resume_file else b""
        
        # Loop through the list of certificates to extract bytes for each one
       cert_bytes_list = []
       if certificate_files:
            for file in certificate_files:
                file_bytes = await file.read()
                cert_bytes_list.append(file_bytes)

        # Pass the new job_preferences string and the cert bytes list into the function
       result = await analyzeprofile(job_preferences, resume_bytes, cert_bytes_list)
       return result
    
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred during binary data text mapping: {str(e)}"
        )
        
    
