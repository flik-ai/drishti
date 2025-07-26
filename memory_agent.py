import asyncio
import json
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.tools import load_memory
from google.genai.types import Content, Part

# --- Constants ---
APP_NAME = "video_analysis_app"
USER_ID = "security_analyst"
MODEL = "gemini-2.5-flash"

async def add_video_analysis_to_memory(runner, memory_service, analysis_data):
    """
    Iterates through video analysis data, creating a session for each entry
    and adding it to the memory service.
    """
    print("\n--- Adding Video Analysis Data to Memory ---")
    # The runner will use its currently assigned agent (info_capture_agent)
    for i, record in enumerate(analysis_data):
        session_id = f"video_analysis_chunk_{i+1}"
        await runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        record_text = json.dumps(record, indent=2)
        user_input = Content(parts=[Part(text=record_text)], role="user")
        async for _ in runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=user_input
        ):
            pass
        completed_session = await runner.session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        await memory_service.add_session_to_memory(completed_session)
    print(f" Added all {len(analysis_data)} records to memory.")

# --- Agent Definitions ---
info_capture_agent = LlmAgent(
    model=MODEL,
    name="InfoCaptureAgent",
    instruction="Acknowledge the provided data by saying 'Data logged.'",
)

memory_recall_agent = LlmAgent(
    model=MODEL,
    name="MemoryRecallAgent",
    instruction=(
        "You are a security analyst assistant. Your task is to answer questions "
        "based on previously logged video analysis data. Use the 'load_memory' "
        "tool to find the answer from past conversations. Be concise."
    ),
    tools=[load_memory]
)

async def main():
    """Main function to set up services, load data, and run queries."""
    session_service = InMemorySessionService()
    memory_service = InMemoryMemoryService()
    runner = Runner(
        # Start with the agent for data ingestion
        agent=info_capture_agent,
        app_name=APP_NAME,
        session_service=session_service,
        memory_service=memory_service
    )

    with open("video_analysis.json", "r") as f:
        video_data = json.load(f)

    await add_video_analysis_to_memory(runner, memory_service, video_data)

    print("\n--- Querying Memory for the Last 5 Entries ---")

    # --- THE FIX ---
    # Directly reassign the agent property on the runner instance
    runner.agent = memory_recall_agent

    query_session_id = "final_query_session"
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=query_session_id
    )

    query_text = "Please provide the analysis for the last 5 timestamps from the video."
    query_input = Content(parts=[Part(text=query_text)], role="user")

    final_response_text = "(No final response)"
    async for event in runner.run_async(
        user_id=USER_ID, session_id=query_session_id, new_message=query_input
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response_text = event.content.parts[0].text

    print(f"\nFinal Agent Response:\n\n{final_response_text}")

if __name__ == "__main__":
    asyncio.run(main())