from google.adk.agents import Agent

class DispatcherAgent:
    def __init__(self):
        self.instruction = self._build_instruction()
        self.agent = Agent(
            name="dispatcher_agent",
            model="gemini-2.0-flash",
            description="An agent that dispatches emergency units (police, ambulance, fire) based on input metadata.",
            instruction=self.instruction,
            tools=[
                self.dispatch_police_unit,
                self.dispatch_ambulance_unit,
                self.dispatch_fire_team_unit
            ]
        )

    def _build_instruction(self):
        """
        System prompt for the Dispatcher Agent.
        This prompt defines the agent's role and how it should interpret metadata to dispatch the correct unit.
        """
        return (
            "You are DispatcherAgent, an AI-powered dispatcher for emergency response units. "
            "Based on the input metadata (string), you must decide whether to dispatch a police unit, ambulance unit, or fire team unit. "
            "Use the appropriate tool for each type of emergency. "
            "If the metadata mentions crime, violence, theft, or law enforcement, dispatch the police unit. "
            "If it mentions injury, medical, health, or ambulance, dispatch the ambulance unit. "
            "If it mentions fire, smoke, burning, or rescue, dispatch the fire team unit. "
            "If the metadata is unclear, politely ask for clarification."
        )

    def dispatch_police_unit(self, location: str, details: str):
        """
        Tool: dispatch_police_unit
        Use this tool to dispatch a police unit to the specified location.
        Parameters:
            - location (str): The location where police assistance is needed.
            - details (str): Details about the incident requiring police intervention.
        Example:
            dispatch_police_unit(location="Main Gate", details="Suspicious activity reported.")
        """
        # Here you would integrate with a real dispatch system or log the dispatch
        pass

    def dispatch_ambulance_unit(self, location: str, details: str):
        """
        Tool: dispatch_ambulance_unit
        Use this tool to dispatch an ambulance unit to the specified location.
        Parameters:
            - location (str): The location where medical assistance is needed.
            - details (str): Details about the medical emergency.
        Example:
            dispatch_ambulance_unit(location="Zone 3", details="Person fainted and is unresponsive.")
        """
        # Here you would integrate with a real dispatch system or log the dispatch
        pass

    def dispatch_fire_team_unit(self, location: str, details: str):
        """
        Tool: dispatch_fire_team_unit
        Use this tool to dispatch a fire team unit to the specified location.
        Parameters:
            - location (str): The location where fire or rescue assistance is needed.
            - details (str): Details about the fire or rescue emergency.
        Example:
            dispatch_fire_team_unit(location="Building B", details="Smoke detected on second floor.")
        """
        # Here you would integrate with a real dispatch system or log the dispatch
        pass

    def get_agent(self):
        """Return the underlying Agent instance."""
        return self.agent