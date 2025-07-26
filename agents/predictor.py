from google.adk.agents import Agent

class CrowdDensityAnalysisAgent:
    def __init__(self):
        self.instruction = self._build_instruction()
        self.agent = Agent(
            name="crowd_density_analysis_agent",
            model="gemini-2.0-flash",
            description="An AI-powered agent that predicts crowd density and flow for the next frame based on the latest 5 frames of analysis data.",
            instruction=self.instruction,
            tools=[self.predict_next_frame]
        )

    def _build_instruction(self):
        """
        System prompt for the Crowd Density Analysis Agent.
        This prompt defines the agent's role and how it should use the latest 5 frames of analysis data to predict the 6th frame.
        """
        return (
            "I am an AI-powered security monitoring agent that analyzes the latest 5 frames of crowd analysis data and predicts the 6th frame's crowd conditions.\n"
            "I can analyze crowd data, and predict future crowd conditions.\n\n"
            "You must use the latest 5 frames of analysis data, pulled from in-memory, to predict the next (6th) frame.\n\n"
            "Based on this analysis data, respond ONLY in JSON format with the following keys:\n"
            "1. 'crowd_density_increase': (True or False) - Indicate if there is an increase in crowd density.\n"
            "2. 'restricted_movements': (True or False) - Indicate if there are any restricted movements.\n"
            "3. 'fire_smoke_detected': (True or False) - Indicate if any fire or smoke is detected.\n"
            "4. 'unit_to_dispatch': (Fire station unit, police station unit, medical unit) - Specify which unit should be dispatched to the zone.\n"
            "5. 'recommendations': (string) - Provide recommendations for action.\n"
            "6. 'summary': (string) - Provide a brief summary of the situation.\n\n"
            "Your output must be a valid JSON object containing all the above keys. Do not include any text outside the JSON object.\n\n"
            "I prioritize public safety and will immediately flag any critical situations that require emergency response."
        )

    def fetch_latest_5_frames(self):
        """
        Fetch the latest 5 frames of crowd analysis data from in-memory storage.
        Replace this placeholder with actual logic to access your in-memory data source.
        Returns:
            list: A list of the latest 5 frame analysis data.
        """
        # TODO: Implement actual in-memory data retrieval logic
        return []

    def predict_next_frame(self):
        """
        Tool: predict_next_frame
        Use this tool to predict the crowd analysis for the next (6th) frame based on the latest 5 frames of in-memory analysis data.
        Returns:
            dict: JSON object with keys:
                - 'crowd_density_increase' (True or False)
                - 'restricted_movements' (True or False)
                - 'fire_smoke_detected' (True or False)
                - 'unit_to_dispatch' (Fire station unit, police station unit, medical unit)
                - 'recommendations' (string)
                - 'summary' (string)
        Example:
            predict_next_frame()
        """
        latest_frames = self.fetch_latest_5_frames()
        # TODO: Implement prediction logic using latest_frames
        # Placeholder response:
        return {
            "crowd_density_increase": False,
            "restricted_movements": False,
            "fire_smoke_detected": False,
            "unit_to_dispatch": "None",
            "recommendations": "No immediate action required.",
            "summary": "Situation is normal based on recent trends."
        }

    def get_agent(self):
        """Return the underlying Agent instance."""
        return self.agent