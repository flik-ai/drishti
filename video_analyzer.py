import os
import google.generativeai as genai
import time
from dotenv import load_dotenv
import warnings
import json
import re

# Ignore all warnings
warnings.filterwarnings("ignore")
import logging
logging.basicConfig(level=logging.ERROR)

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def run_gemini_analysis_sync(video_bytes: bytes) -> dict:
    """
    A synchronous function to run the Gemini analysis.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        analysis_start_time = time.time()
        
        response = model.generate_content(
            contents=[
                {
                    "inline_data": {
                        "data": video_bytes,
                        "mime_type": 'video/mp4'
                    }
                },
                {
                    "text": '''From the video, analyze and return ONLY a JSON object with this structure:
            {
                "crowd_density": "low|medium|high|severe",
                "crowd_flow": "unrestricted|moderately_restricted|severely_restricted",
                "estimated_count": number_or_null,
                "fire_smoke_detected": "yes|no",
                "congested_entry_exits": "yes|no",
                "safety_level": "safe|moderate_risk|high_risk|critical",
                "needs_security_intervention": "yes|no",
                "additional_observations": "brief description"
            }'''
                }
            ]
        )
        
        analysis_end_time = time.time()
        print(f"Time taken for analysis: {analysis_end_time - analysis_start_time:.2f} seconds")
        
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            json_str = match.group(0)
            data = json.loads(json_str)
            print(json.dumps(data, indent=2))
            return data
        else:
            print("No JSON object found in response.")
            return {"error": "No JSON object found in response."}
            
    except Exception as e:
        print(f"An error occurred during analysis: {e}")
        return {"error": str(e)}

def analyze_video_chunk(video_path: str, start_time: float, end_time: float) -> dict:
    """
    Analyzes a video chunk synchronously.
    """
    print(f"Analyzing {video_path} from {start_time:.2f}s to {end_time:.2f}s")
    
    with open(video_path, 'rb') as f:
        video_bytes = f.read()
    
    analysis_result = run_gemini_analysis_sync(video_bytes)
    
    return analysis_result

if __name__ == '__main__':
    video_file = "stampede.mp4"
    if os.path.exists(video_file):
        analysis = analyze_video_chunk(video_file, 0, 5)
        print(json.dumps(analysis, indent=4))
    else:
        print(f"Test video '{video_file}' not found. Skipping example usage.")