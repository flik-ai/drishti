from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
import uvicorn
from agent_app.orchestrator import OrchestratorAgent


app = FastAPI()


@app.post("/analyze")
async def analyze_crowd(request: Request):
    """
    Endpoint to send user input to the orchestrator agent and get the response.
    """
    body = await request.json()
    orchestrator = OrchestratorAgent()
    response = orchestrator.invoke(body.get("user_id"), body.get("message"))
    return {"response": response}

# For local development/testing
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
