from google.adk.agents import Agent

class SecurityCommanderAssistant:
    def __init__(self):
        self.analysis_data = self.load_analysis_data()
        self.instruction = self._build_instruction()
        self.agent = Agent(
            name="security_commander_assistant",
            model="gemini-2.0-flash",
            description="An AI-powered assistant that helps both security commanders/teams and the general public to understand the situation at the site and assist them in making decisions or staying safe.",
            instruction=self.instruction,
            tools=[self.raise_a_reported_incident]
        )

    def load_analysis_data(self):
        """Load the crowd analysis data to include in the agent's context."""
        try:
            with open('analysis.txt', 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return "Analysis data file not available."

    def _build_instruction(self):
        """
        System prompt for the Security Commander Assistant agent.
        This prompt defines the agent's role, capabilities, and how it should interact with both security personnel and the public.
        """
        return f"""You are SecurityCommanderAssistant, an AI-powered assistant for both security commanders/teams and the general public at a monitored, high-crowded site or event.

                Your primary responsibilities:
                - Answer questions about crowd density, movement, anomalies, and potential security or safety risks.
                - Provide safety information, directions, and general assistance to the public.
                - Assist in decision-making by providing clear, concise, and actionable insights.
                - When a user (public or security) requests to report an incident, use the 'raise_a_reported_incident' tool with the reportee's name and a detailed incident description.

                Guidelines:
                - Always base your answers on the CURRENT CROWD ANALYSIS DATA provided below.
                - If you do not have enough information to answer a question, politely ask for clarification or specify what data is missing.
                - Be concise, professional, and focused on security, safety, and helpfulness.
                - If you detect a potential incident or anomaly, recommend immediate actions and offer to raise a reported incident.
                - Treat all users (public or security) with respect and provide clear, accessible information.

                CURRENT CROWD ANALYSIS DATA:
                {self.analysis_data}
                """

    def raise_a_reported_incident(self, reportee, incident_description):
        """
        Tool: raise_a_reported_incident
        Use this tool to formally report a security or safety incident.
        Parameters:
            - reportee (str): The name or identifier of the person reporting the incident (can be a member of the public or security team).
            - incident_description (str): A clear, detailed description of the incident, including location, time, and any relevant context.
        Prompt Template:
            When invoking this tool, provide the reportee's name and a comprehensive description of the incident. Ensure the description is actionable and includes all necessary details for the security team to respond effectively.
        Example:
            raise_a_reported_incident(reportee="Jane Smith", incident_description="Overcrowding observed near Main Stage at 18:45. Requesting crowd control assistance.")
        """

        print(f"Raising a reported incident: {reportee} - {incident_description}")
        pass
    
    def get_agent(self):
        """Return the underlying Agent instance."""
        return self.agent
