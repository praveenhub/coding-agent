from google import genai
from google.genai import types
import os
import sys
from pathlib import Path
from src.tools import read_file, list_files, edit_file, execute_bash_command, run_in_sandbox, find_arxiv_papers, get_current_date_and_time
import traceback
import argparse
import functools

# Choose your Gemini model - unless you want something crazy "gemini-2.5-flash-preview-04-17" is the default model
MODEL_NAME = "gemini-2.5-flash-preview-04-17"
DEFAULT_THINKING_BUDGET = 256

# Define project root - needed here for agent initialization
project_root = Path(__file__).resolve().parents[1]

# --- Code Agent Class ---
class CodeAgent:
    """A simple coding agent using Google Gemini (google-genai SDK)."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-preview-04-17", verbose: bool = False):
        """Initializes the agent with API key and model name."""
        self.api_key = api_key
        self.verbose = verbose
        self.model_name = f'models/{model_name}' # Add 'models/' prefix
        # Use imported tool functions
        self.tool_functions = [
            read_file,
            list_files,
            edit_file,
            execute_bash_command,
            run_in_sandbox,
            find_arxiv_papers,
            get_current_date_and_time
        ]
        if self.verbose:
            self.tool_functions = [self._make_verbose_tool(f) for f in self.tool_functions]
        self.client = None
        self.chat = None
        self.conversation_history = [] # Manual history for token counting ONLY
        self.current_token_count = 0 # Store token count for the next prompt
        self._configure_client()

    def _configure_client(self):
        """Configures the Google Generative AI client."""
        print("\n\u2692\ufe0f Configuring genai client...")
        try:

            self.client = genai.Client(api_key=self.api_key)
            print("\u2705 Client configured successfully.")
        except Exception as e:
            print(f"\u274c Error configuring genai client: {e}")
            traceback.print_exc()
            sys.exit(1)

    def start_interaction(self):
        """Starts the main interaction loop using a stateful ChatSession via client.chats.create."""
        if not self.client:
            print("\n\u274c Client not configured. Exiting.")
            return

        print("\n\u2692\ufe0f Initializing chat session...")
        try:
            # Create a chat session using the client
            self.chat = self.client.chats.create(model=self.model_name, history=[])
            print("\u2705 Chat session initialized.")
        except Exception as e:
            print(f"\u274c Error initializing chat session: {e}")
            traceback.print_exc()
            sys.exit(1)

        print("\n\u2692\ufe0f Agent ready. Ask me anything. Type 'exit' to quit.")

        # Prompt for thinking budget per session
        try:
            budget_input = input(f"Enter thinking budget (0 to 24000) for this session [{DEFAULT_THINKING_BUDGET}]: ").strip()
            self.thinking_budget = int(budget_input) if budget_input else DEFAULT_THINKING_BUDGET
        except ValueError:
            print(f"⚠️ Invalid thinking budget. Using default of {DEFAULT_THINKING_BUDGET}.")
            self.thinking_budget = DEFAULT_THINKING_BUDGET
        self.thinking_config = types.ThinkingConfig(thinking_budget=self.thinking_budget)

        # Prepare tool config with thinking_config
        tool_config = types.GenerateContentConfig(tools=self.tool_functions, thinking_config=self.thinking_config)

        while True:
            try:
                # Display token count from *previous* turn in the prompt
                prompt_text = f"\n🔵 You ({self.current_token_count}): "
                user_input = input(prompt_text).strip()

                if user_input.lower() in ["exit", "quit"]:
                    print("\n👋 Goodbye!")
                    break
                if not user_input:
                    continue

                # --- Update manual history (for token counting ONLY) --- 
                # Add user message BEFORE sending to model
                new_user_content = types.Content(parts=[types.Part(text=user_input)], role="user")
                self.conversation_history.append(new_user_content)

                # --- Keep existing Tool Config and Send Message call --- 
                print("\n⏳ Sending message and processing...")
                # Prepare tool configuration (Assuming this structure is correct based on earlier state/memory)
                tool_config = types.GenerateContentConfig(tools=self.tool_functions, thinking_config=self.thinking_config)

                # Send message using the chat object's send_message method
                response = self.chat.send_message(
                    message=user_input, # Pass only the new user input here
                    config=tool_config # Use 'config' kwarg with GenerateContentConfig
                )

                # --- Update manual history and calculate new token count AFTER response --- 
                agent_response_content = None
                if response.candidates and response.candidates[0].content:
                    agent_response_content = response.candidates[0].content
                    self.conversation_history.append(agent_response_content)
                else:
                    print("\n⚠️ Agent response did not contain content for history/counting.")

                # Print agent's response text to user
                print(f"\n🟢 \x1b[92mAgent:\x1b[0m {response.text}")

                # Calculate and store token count for the *next* prompt
                try:
                    token_count_response = self.client.models.count_tokens(
                        model=self.model_name,
                        contents=self.conversation_history # Use the updated manual history
                    )
                    self.current_token_count = token_count_response.total_tokens
                except Exception as count_error:
                    # Don't block interaction if counting fails, just report it and keep old count
                    print(f"\n⚠️ \x1b[93mCould not update token count: {count_error}\x1b[0m")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n🔴 \x1b[91mAn error occurred during interaction: {e}\x1b[0m")
                traceback.print_exc() # Print traceback for debugging

    def _make_verbose_tool(self, func):
        """Wrap tool function to print verbose info when called."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"\n🔧 Tool called: {func.__name__}, args: {args}, kwargs: {kwargs}")
            result = func(*args, **kwargs)
            print(f"\n▶️ Tool result ({func.__name__}): {result}")
            return result
        return wrapper

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Run the Code Agent")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose tool logging')
    args = parser.parse_args()
    print("🚀 Starting Code Agent...")
    api_key = os.getenv('GEMINI_API_KEY')

    # Make project_root available to the tools module if needed indirectly
    # (Though direct definition in tools.py is preferred)
    # import src.tools
    # src.tools.project_root = project_root

    agent = CodeAgent(api_key=api_key, model_name=MODEL_NAME, verbose=args.verbose)
    agent.start_interaction()

if __name__ == "__main__":
    main()