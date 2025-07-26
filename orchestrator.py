from google.adk.agents import Agent
import json
import re
from datetime import datetime
from vertexai.preview.reasoning_engines import AdkApp
from agent_app.agents.security_commander_assistant import SecurityCommanderAssistant
from agent_app.agents.predictor import CrowdDensityAnalysisAgent
from agent_app.agents.dispatcher import DispatcherAgent


class OrchestratorAgent:
    def __init__(self):
        self.crowd_density_analysis_agent = CrowdDensityAnalysisAgent().get_agent()
        self.security_commander_assistant = SecurityCommanderAssistant().get_agent()
        self.dispatcher_agent = DispatcherAgent().get_agent()
        self.agent = Agent(
            name="Orchestrator",
            model="gemini-2.0-flash",
            description="I coordinate between the crowd and hazard analysis agent and the security commander assistant.",
            sub_agents=[
                self.crowd_density_analysis_agent,
                self.security_commander_assistant,
                self.dispatcher_agent
            ]
        )
        self.runner = AdkApp(agent=self.agent)

    def get_agent(self):
        return self.agent

    def get_runner(self):
        return self.runner

    def invoke(self, user_id, message):
        all_events = []
        for event in self.runner.stream_query(user_id=user_id, message=message):
            all_events.append(event)
        if all_events:
            return all_events[-1]["content"]["parts"][0]
        return None 