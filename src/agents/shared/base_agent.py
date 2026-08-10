from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Abstract base class for all wellness platform agents."""

    @abstractmethod
    def analyze(self, user_id: str) -> dict:
        """Run the agent's analysis for a given user and return a recommendation."""
        ...

    @abstractmethod
    def build_prompt(self, *args, **kwargs) -> str:
        """Build the LLM prompt for this agent."""
        ...
