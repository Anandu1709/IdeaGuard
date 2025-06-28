import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_ADVISOR_API_KEY = os.getenv('GEMINI_ADVISOR_API_KEY')

advisor_genai_model = None
if GEMINI_ADVISOR_API_KEY:
    try:
        genai.configure(api_key=GEMINI_ADVISOR_API_KEY)
        advisor_genai_model = genai.GenerativeModel('gemini-2.5-flash') # Using gemini-2.5-flash as per your screenshot
        print("Gemini Advisor model configured successfully.")
    except Exception as e:
        print(f"Error configuring Gemini Advisor API with provided key: {e}. Advisor chat will use mock responses.")
else:
    print("GEMINI_ADVISOR_API_KEY not found in .env. Advisor chat will use mock responses.")

def get_advisor_response(user_message, chat_history=None, user_context=None):
    """
    Gets a response from the Gemini Advisor model.
    If the model is not configured or an error occurs, returns a mock response.
    Includes user context in the initial prompt if provided.
    """
    if not advisor_genai_model:
        return "I am currently under development. Please check back later for real-time assistance!"

    try:
        formatted_history = []
        
        # Add user context as an initial system message or user message if available
        if user_context and not any(msg.get('role') == 'user' and 'context_message' in msg.get('parts', ['']) for msg in chat_history):
            context_message = (
                f"The user's name is {user_context.get('first_name', '')} {user_context.get('last_name', '')}. "
                f"They work at {user_context.get('company', 'an unknown company')} as a {user_context.get('job_title', 'professional')}. "
                f"Their email is {user_context.get('email', 'unknown')}. "
                "Keep this context in mind when providing advice."
            )
            # Add as a user message with a special flag to avoid re-adding
            formatted_history.append({'role': 'user', 'parts': [context_message], 'context_message': True})
            # Add a dummy model response to balance the turn
            formatted_history.append({'role': 'model', 'parts': ["Understood. How can I assist you today?"]})

        if chat_history:
            for msg in chat_history:
                # Only add actual chat messages, not the internal context message
                if not msg.get('context_message'):
                    formatted_history.append({'role': msg['role'], 'parts': [msg['text']]})
        
        chat = advisor_genai_model.start_chat(history=formatted_history)
        response = chat.send_message(user_message)
        
        return response.text
    except Exception as e:
        print(f"Error during Gemini Advisor API call: {e}. Returning mock response.")
        return "I am experiencing technical difficulties. Please try again later, or contact support if the issue persists."
