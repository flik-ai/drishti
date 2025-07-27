import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai import types
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import pubsub_v1
# import googlemaps

# --- Configuration Constants ---
APP_NAME = "security_system"
USER_ID = "security_operator"
MODEL_NAME = "gemini-2.0-flash"

# --- Pydantic Models ---

class EventData(BaseModel):
    chunk_path: str
    start_time: int
    end_time: int
    start_utc_time: str
    end_utc_time: str
    crowd_density: str
    crowd_flow: str
    estimated_count: int
    fire_smoke_detected: str
    congested_entry_exits: str
    safety_level: str
    needs_security_intervention: str
    additional_observations: str

class QualitativeAnalysis(BaseModel):
    crowd_density_increase: bool = Field(description="Whether crowd density has increased")
    restricted_movements: bool = Field(description="Whether movements are restricted")
    fire_smoke_detected: bool = Field(description="Whether fire or smoke is detected")
    unit_to_dispatch: str = Field(description="Type of unit to dispatch (Fire station unit, police station unit, medical unit)")
    recommendations: str = Field(description="Recommendations for handling the situation")
    summary: str = Field(description="Summary of the analysis")

class SecurityChatInput(BaseModel):
    action_type: str = Field(description="Type of action: 'report', 'query', or 'help'")
    message: str = Field(description="The message content")
    location: Optional[str] = Field(default=None, description="Location if relevant")

class SecurityChatOutput(BaseModel):
    response_type: str = Field(description="Type of response: 'dispatch', 'response', or 'info'")
    content: str = Field(description="Response content")
    dispatch_data: Optional[Dict] = Field(default=None, description="Dispatch data if applicable")

class DispatchInput(BaseModel):
    dispatch_type: str = Field(description="Type of dispatch request")
    data: Dict = Field(description="Dispatch data")
    priority: str = Field(description="Priority level: high, medium, low")

class DispatchOutput(BaseModel):
    status: str = Field(description="Dispatch status")
    units_dispatched: List[str] = Field(description="List of units dispatched")
    estimated_arrival: str = Field(description="Estimated arrival time")
    message: str = Field(description="Status message")

# --- Firebase and External Services Setup ---

class FirestoreService:
    def __init__(self):
        # Initialize Firebase (assumes credentials are set up)
        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
    
    async def get_recent_events(self, limit: int = 20) -> List[Dict]:
        """Fetch recent events from Firestore 'events' collection"""
        try:
            events_ref = self.db.collection('events')
            query = events_ref.order_by('end_utc_time', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()
            
            events = []
            for doc in docs:
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
            
            return events
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

class PubSubService:
    def __init__(self):
        self.publisher = pubsub_v1.PublisherClient()
        self.project_id = "drishti-ea59b"
        self.topic_name = "dispatcher"
    
    async def publish_dispatch(self, message_data: Dict):
        """Publish dispatch message to Pub/Sub dispatcher topic"""
        try:
            topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
            message_json = json.dumps(message_data)
            message_bytes = message_json.encode('utf-8')
            
            future = self.publisher.publish(topic_path, message_bytes)
            message_id = future.result()
            print(f"Published message ID: {message_id} to {topic_path}")
            return True
        except Exception as e:
            print(f"Error publishing message: {e}")
            return False

class GoogleMapsService:
    def __init__(self, api_key: str):
        # Uncomment when googlemaps is available
        # self.gmaps = googlemaps.Client(key=api_key)
        pass
    
    async def find_nearby_hospitals(self, location: str, radius: int = 5000) -> List[Dict]:
        """Find nearby hospitals using Google Places API"""
        try:
            # Mock data for now - replace with actual API call when googlemaps is available
            mock_hospitals = [
                {"name": "City General Hospital", "vicinity": location, "rating": 4.2},
                {"name": "Emergency Medical Center", "vicinity": location, "rating": 4.0}
            ]
            return mock_hospitals
        except Exception as e:
            print(f"Error finding hospitals: {e}")
            return []

# --- Agent Tools ---

async def fetch_firestore_events() -> str:
    """Tool to fetch recent events from Firestore"""
    firestore_service = FirestoreService()
    events = await firestore_service.get_recent_events(20)
    return json.dumps(events, indent=2)

async def find_hospitals(location: str) -> str:
    """Tool to find nearby hospitals"""
    # Replace with your Google Maps API key
    maps_service = GoogleMapsService("YOUR_GOOGLE_MAPS_API_KEY")
    hospitals = await maps_service.find_nearby_hospitals(location)
    return json.dumps(hospitals[:5], indent=2)  # Return top 5 hospitals

async def dispatch_unit(unit_type: str, location: str, priority: str) -> str:
    """Tool to dispatch emergency units"""
    pubsub_service = PubSubService()
    
    dispatch_data = {
        "unit_type": unit_type,
        "location": location,
        "priority": priority,
        "timestamp": datetime.now().isoformat(),
        "status": "dispatched"
    }
    
    success = await pubsub_service.publish_dispatch(dispatch_data)
    
    if success:
        return f"Successfully dispatched {unit_type} to {location}"
    else:
        return f"Failed to dispatch {unit_type}"

async def check_recent_dispatches(unit_type: Optional[str] = None) -> str:
    """Tool to check recent dispatches to avoid duplicates
    
    Args:
        unit_type: Optional type of unit to filter by (fire, police, medical)
    
    Returns:
        JSON string of recent dispatches
    """
    # This would typically query a database of recent dispatches
    # For now, return a mock response
    recent_dispatches = {
        "fire": [],
        "police": [{"location": "Platform A", "time": "2024-01-15T10:30:00"}],
        "medical": []
    }
    
    if unit_type:
        return json.dumps(recent_dispatches.get(unit_type.lower(), []))
    return json.dumps(recent_dispatches)

# --- Agent Definitions ---

def create_qualitative_summary_agent():
    return LlmAgent(
        model=MODEL_NAME,
        name="qualitative_summary_agent",
        description="Analyzes recent security events and provides qualitative assessment",
        instruction="""You are a security analysis agent that processes recent events and provides structured analysis.

When you receive event data, you should:
1. Analyze the events to determine:
   - Whether crowd density has increased compared to historical patterns (look at crowd_density field: 'low', 'moderate', 'high', 'severe')
   - Whether movements are restricted (check crowd_flow field: 'free', 'restricted', 'severely_restricted')  
   - Whether fire or smoke is detected (check fire_smoke_detected field: 'yes' or 'no')
   - What type of unit should be dispatched based on the situation:
     * "Fire station unit" if fire/smoke detected
     * "Police station unit" if crowd control needed (severe density, restricted flow)
     * "Medical unit" if safety_level is 'critical' and stampede risk
   - Provide specific recommendations based on the additional_observations
   - Create a comprehensive summary of the current security situation

Process the events chronologically by end_utc_time to understand trends.
Focus on the most recent events but consider patterns across all events provided.

Respond with your structured analysis in JSON format matching the expected schema.
""",
        output_schema=QualitativeAnalysis,
        output_key="qualitative_analysis",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True
    )

def create_security_chat_agent():
    return LlmAgent(
        model=MODEL_NAME,
        name="security_chat_agent",
        description="Handles security personnel interactions - reports, queries, and help requests",
        instruction="""You are a security chat agent that handles three types of interactions:

1. REPORT: When security personnel report incidents
   - Collect incident details
   - Assess severity and required response
   - Generate dispatch requests if needed

2. QUERY: When personnel ask about zone status or incident details
   - Provide information about current security status
   - Answer questions about specific incidents or zones

3. HELP: When personnel need emergency assistance
   - Find nearby hospitals or emergency services
   - Coordinate emergency response
   - Generate appropriate dispatch requests

Process the input JSON with action_type, message, and optional location.
Respond in natural language with appropriate information and actions based on the request type.
Be helpful and provide clear guidance to security personnel.
""",
        tools=[check_recent_dispatches, find_hospitals],
        input_schema=SecurityChatInput,
        output_key="security_chat_response"
    )

def create_dispatch_agent():
    return LlmAgent(
        model=MODEL_NAME,
        name="dispatch_agent",
        description="Manages emergency unit dispatching with context awareness",
        instruction="""You are a dispatch coordination agent responsible for deploying emergency resources.

Your responsibilities:
1. Receive dispatch requests with priority and location information
2. Check recent dispatch history to avoid duplicate deployments
3. Coordinate with appropriate emergency services via Pub/Sub
4. Track unit availability and estimated response times
5. Provide status updates on dispatch operations

Before dispatching:
- Check if similar units were recently dispatched to the same area using check_recent_dispatches tool
- Assess current emergency load and unit availability
- Prioritize based on severity and urgency
- Coordinate multiple unit types if needed
- Use dispatch_unit tool to actually dispatch units

Process the input JSON with dispatch_type, data, and priority.
Always provide clear status updates and estimated arrival times.
Return a comprehensive dispatch status response in natural language.
""",
        tools=[dispatch_unit, check_recent_dispatches],
        input_schema=DispatchInput,
        output_key="dispatch_status"
    )

def create_orchestrator_agent(sub_agents: List[LlmAgent]):
    return LlmAgent(
        model=MODEL_NAME,
        name="security_orchestrator",
        description="Main orchestrator that routes requests and manages system memory",
        instruction="""You are the main security system orchestrator. You manage communication between sub-agents and maintain system memory.

When you receive an /event message:
1. Parse the event data from the message
2. Use the fetch_firestore_events tool to get recent events data
3. Combine the current event with recent events data
4. Transfer to qualitative_summary_agent for analysis by saying "transfer to qualitative_summary_agent" and providing the combined event data
5. Process the analysis response and coordinate any dispatch actions if needed

When you receive other messages:
1. Determine the appropriate response based on the message type:
   - For security personnel communication: transfer to security_chat_agent
   - For dispatch requests: transfer to dispatch_agent
   - For queries: provide information from available data or transfer to appropriate agent

2. Use tools when needed (e.g., fetch recent events for analysis)
3. Always maintain context and ensure proper information flow
4. Store important event data and analysis results for future reference

To transfer to sub-agents, use the format: "transfer to [agent_name]" followed by the relevant data.
Always provide clear, actionable responses and coordinate system-wide operations.
""",
        tools=[fetch_firestore_events],
        sub_agents=sub_agents,
        output_key="orchestrator_response"
    )

# --- System Setup and Main Class ---

class SecurityMultiAgentSystem:
    def __init__(self):
        # Initialize services
        self.session_service = InMemorySessionService()
        self.memory_service = InMemoryMemoryService()
        
        # Initialize setup flag
        self.setup_complete = False
        
        # Create agents
        self.qualitative_agent = create_qualitative_summary_agent()
        self.security_chat_agent = create_security_chat_agent()
        self.dispatch_agent = create_dispatch_agent()
        
        self.orchestrator = create_orchestrator_agent([
            self.qualitative_agent,
            self.security_chat_agent, 
            self.dispatch_agent
        ])
        
        # Create session IDs
        self.session_ids = {
            "orchestrator": "orchestrator_session",
            "qualitative": "qualitative_session",
            "security_chat": "security_chat_session",
            "dispatch": "dispatch_session"
        }
        
        # Create runners
        self.runners = {
            "orchestrator": Runner(
                agent=self.orchestrator,
                app_name=APP_NAME,
                session_service=self.session_service,
                memory_service=self.memory_service
            ),
            "qualitative": Runner(
                agent=self.qualitative_agent,
                app_name=APP_NAME,
                session_service=self.session_service,
                memory_service=self.memory_service
            ),
            "security_chat": Runner(
                agent=self.security_chat_agent,
                app_name=APP_NAME,
                session_service=self.session_service,
                memory_service=self.memory_service
            ),
            "dispatch": Runner(
                agent=self.dispatch_agent,
                app_name=APP_NAME,
                session_service=self.session_service,
                memory_service=self.memory_service
            )
        }
    
    async def setup_sessions(self):
        """Setup sessions asynchronously"""
        if not self.setup_complete:
            for session_id in self.session_ids.values():
                await self.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=session_id
                )
            self.setup_complete = True
    
    async def process_message(self, message: str, agent_type: str = "orchestrator") -> str:
        """Process a message through the specified agent"""
        await self.setup_sessions()
        
        runner = self.runners[agent_type]
        session_id = self.session_ids[agent_type]
        
        user_content = types.Content(
            role='user',
            parts=[types.Part(text=message)]
        )
        
        final_response = "No response received"
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=user_content
        ):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
        
        return final_response
    
    async def handle_event(self, event_data: Dict) -> str:
        """Handle incoming event data from video splitter"""
        await self.setup_sessions()
        
        # Validate event data structure
        try:
            validated_event = EventData(**event_data)
        except Exception as e:
            print(f"Invalid event data structure: {e}")
            return f"Error: Invalid event data structure - {e}"
        
        # Store event in memory with UTC timestamp as key
        event_key = f"event_{validated_event.end_utc_time}"
        print(f"Storing event in memory with key: {event_key}")
        
        # First, get recent events from Firestore
        try:
            firestore_service = FirestoreService()
            recent_events = await firestore_service.get_recent_events(20)
        except Exception as e:
            print(f"Error fetching recent events: {e}")
            recent_events = []
        
        # Combine current event with recent events
        combined_data = [event_data] + recent_events
        
        # Process through qualitative summary agent directly for analysis
        combined_message = json.dumps(combined_data)
        analysis_response = await self.process_message(combined_message, "qualitative")
        
        # Return the analysis
        return f"Event Analysis: {analysis_response}"
    
    async def handle_security_chat(self, action_type: str, message: str, location: str = None) -> str:
        """Handle security chat interactions"""
        await self.setup_sessions()
        
        chat_input = {
            "action_type": action_type,
            "message": message,
            "location": location
        }
        
        chat_message = json.dumps(chat_input)
        return await self.process_message(chat_message, "security_chat")
    
    async def handle_dispatch(self, dispatch_type: str, data: Dict, priority: str = "medium") -> str:
        """Handle dispatch requests"""
        await self.setup_sessions()
        
        dispatch_input = {
            "dispatch_type": dispatch_type,
            "data": data,
            "priority": priority
        }
        
        dispatch_message = json.dumps(dispatch_input)
        return await self.process_message(dispatch_message, "dispatch")

# --- Usage Example ---

async def main():
    """Example usage of the security multi-agent system"""
    system = SecurityMultiAgentSystem()
    
    # Example event data with correct structure
    event_data = {
        "chunk_path": "video_chunks/chunk_002.mp4",
        "start_time": 4,
        "end_time": 9,
        "start_utc_time": "2025-07-27T04:13:28.187916+00:00Z",
        "end_utc_time": "2025-07-27T04:13:33.187916+00:00Z",
        "crowd_density": "severe",
        "crowd_flow": "severely_restricted",
        "estimated_count": 500,
        "fire_smoke_detected": "no",
        "congested_entry_exits": "yes",
        "safety_level": "critical",
        "needs_security_intervention": "yes",
        "additional_observations": "A massive crowd fills the entire visible area of what appears to be a railway station concourse or passage, causing severe congestion and extremely restricted movement. On-screen text indicates this footage is from before a fatal stampede at New Delhi Railway Station."
    }
    
    # Handle event
    print("=== Processing Event ===")
    event_response = await system.handle_event(event_data)
    print(f"Event Response: {event_response}")
    
    # Handle security chat - report
    print("\n=== Security Chat - Report ===")
    chat_response = await system.handle_security_chat(
        action_type="report",
        message="Suspicious activity detected in Zone A, multiple individuals acting erratically",
        location="Zone A, Platform 3"
    )
    print(f"Chat Response: {chat_response}")
    
    # Handle security chat - query
    print("\n=== Security Chat - Query ===")
    query_response = await system.handle_security_chat(
        action_type="query",
        message="What is the current status of Platform 2?",
        location="Platform 2"
    )
    print(f"Query Response: {query_response}")
    
    # Handle dispatch
    print("\n=== Dispatch Request ===")
    dispatch_response = await system.handle_dispatch(
        dispatch_type="emergency",
        data={
            "unit_type": "medical",
            "location": "Platform 3, Zone A",
            "incident_type": "crowd_control"
        },
        priority="high"
    )
    print(f"Dispatch Response: {dispatch_response}")

if __name__ == "__main__":
    asyncio.run(main())