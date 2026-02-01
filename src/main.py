from __future__ import annotations
import os
import sys

# Ensure the root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.agent import Agent


def main():
    """Run a sample research agent."""
    # Attempt to load environment variables from .env
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    try:
        # Initialize the agent from environment configuration
        agent = Agent.from_env()

        # Define a sample goal
        sample_goal = "Analyze the current state of artificial intelligence in 2026."

        print(f"--- Starting Agent Execution ---")
        print(f"Goal: {sample_goal}\n")

        # Run the agent
        result = agent.run(goal=sample_goal)

        print("\n--- Agent Execution Completed ---")
        print(f"Steps executed: {result.steps_executed}")
        # print(f"Final State: {result.state}")

    except Exception as exc:
        print(f"An error occurred while running the agent: {exc}")


if __name__ == "__main__":
    main()
