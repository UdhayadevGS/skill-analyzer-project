"""
We are using config.py because it will first load the gemini key from the .env file 
and if the key is invalid it will crash immediately on server startup .. this is better than
working through many steps in the frontend and realising the key is broken during the processing 
step

we are importing os because it gives python the ability to access os and give the data to python
from dotenv we are importing load_dotenv to read the .env file and store it in os system environment
then we are calling the function to load the .env file
we are storing the key in a dictionary and naming it settings 
"""

import os
from dotenv import load_dotenv

load_dotenv()

api_key=os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("FATAL ERROR : Gemini API key is missing from your environment variables")

settings = { 
    "GEMINI_API_KEY":  api_key
}

