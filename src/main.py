from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure the root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.agent import Agent, AgentConfig


def main():
    """Run the StoryGraph AI Agent for character and relationship analysis."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="StoryGraph AI Agent - Analyze literary works for characters and relationships"
    )
    parser.add_argument(
        "source_file",
        nargs="?",
        default="static/war-and-peace-by-leo-tolstoy.txt",
        help="Path to the text file to analyze",
    )
    parser.add_argument(
        "--title",
        default="War and Peace",
        help="Title of the book being analyzed",
    )
    parser.add_argument(
        "--output",
        default="output/report",
        help="Directory for the HTML report output",
    )
    parser.add_argument(
        "--max-chapters",
        type=int,
        default=None,
        help="Maximum number of chapters to process (for testing)",
    )
    parser.add_argument(
        "--load-state",
        dest="load_state",
        default=None,
        help="Path to a JSON file containing a previously saved AgentState to resume from",
    )
    args = parser.parse_args()

    # Attempt to load environment variables from .env
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    # Validate source file
    source_path = Path(args.source_file)
    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}")
        sys.exit(1)

    try:
        # Configure the agent
        config = AgentConfig(
            output_directory=args.output,
            report_title=f"StoryGraph Analysis: {args.title}",
        )

        # Initialize the agent from environment configuration
        agent = Agent.from_env(agent_config=config)

        # Optionally load a saved state
        initial_state = None
        if args.load_state:
            from src.memory.models import AgentState

            state_path = Path(args.load_state)
            if not state_path.exists():
                print(f"Error: State file not found: {state_path}")
                sys.exit(1)
            try:
                import json

                with state_path.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                # Use pydantic v2 model validation
                try:
                    initial_state = AgentState.model_validate(payload)
                except AttributeError:
                    # Fallback for pydantic v1
                    initial_state = AgentState.parse_obj(payload)
            except Exception as exc:
                print(f"Error loading state file: {exc}")
                sys.exit(1)

        # Define the analysis goal
        goal = f"Analyze '{args.title}' to extract characters, relationships, and significant events."

        print("=" * 60)
        print("StoryGraph AI Agent")
        print("=" * 60)
        print(f"Source File: {source_path}")
        print(f"Book Title: {args.title}")
        print(f"Output Directory: {args.output}")
        print("=" * 60)
        print()

        # Run the agent
        result = agent.run(
            goal=goal,
            source_file_path=str(source_path.absolute()),
            book_title=args.title,
            initial_state=initial_state,
        )

        print()
        print("=" * 60)
        print("Analysis Complete!")
        print("=" * 60)
        print(result.summary())
        print()

        if result.report_path:
            print(f"Open the report in your browser:")
            print(f"  file://{Path(result.report_path).absolute()}")

    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"An error occurred: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
