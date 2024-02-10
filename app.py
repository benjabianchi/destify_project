import time
from dotenv import load_dotenv
import os
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App
import re
import time
from openai._client import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv('SECRET_KEY')
SLACK_APP_TOKEN = os.getenv('SLACK_KEY')
SLACK_BOT_TOKEN = os.getenv('BOT_KEY')
assistant_id = "asst_L3ZIW6VHTknyLx62KuPrGf4p"


OPENAI_API_KEY = os.getenv('SECRET_KEY')
openai = OpenAI(api_key = OPENAI_API_KEY)
def create_and_check_thread(ass_id, prompt):
    # Crear un hilo
    thread = openai.beta.threads.create()
    my_thread_id = thread.id

    # Crear un mensaje
    message = openai.beta.threads.messages.create(
        thread_id=my_thread_id,
        role="user",
        content=prompt
    )

    # Ejecutar
    run = openai.beta.threads.runs.create(
        thread_id=my_thread_id,
        assistant_id=ass_id,
    )
    run_id = run.id

    # Verificar estado
    status = openai.beta.threads.runs.retrieve(
        thread_id=my_thread_id,
        run_id=run_id,
    ).status

    while status != "completed":
        time.sleep(2)
        status = openai.beta.threads.runs.retrieve(
            thread_id=my_thread_id,
            run_id=run_id,
        ).status

    # Obtener respuesta
    response = openai.beta.threads.messages.list(
        thread_id=my_thread_id
    )

    if response.data:
        return response.data[0].content[0].text.value
    else:
        return None
    

# Assuming we have a dictionary to store conversations by channel
# Key is the channel ID, and value is a list of tuples (user_message, bot_response)
app = App(token=SLACK_BOT_TOKEN)
client = WebClient(token=SLACK_BOT_TOKEN)


# Assuming we have a dictionary to store conversations by channel
# Key is the channel ID, and value is a list of tuples (user_message, bot_response)
conversations = {}

def clean_text(original_text):
    # Define the pattern to remove: Matches 【, any number of digits, †, any characters, 】
    pattern_to_remove = r"【\d+†.*?】"
    # Use re.sub to replace the found pattern with an empty string
    cleaned_text = re.sub(pattern_to_remove, "", original_text)
    return cleaned_text
@app.event("message")
def handle_message_events(body, logger, say):
    if body["event"].get("subtype") is None or body["event"].get("subtype") != "bot_message":
        channel_id = body["event"]["channel"]
        user_message = body["event"]["text"]
        specific_channel_id = "C06DH4MMFKK"  # Replace with your specific channel ID

        if channel_id == specific_channel_id:
            try:
                # Add 'eyes' reaction to indicate processing
                client.reactions_add(
                    channel=channel_id,
                    timestamp=body["event"]["ts"],
                    name="eyes"
                )
                
                # Ensure the channel history exists
                if channel_id not in conversations:
                    conversations[channel_id] = []

                # Append the user message to the history
                conversations[channel_id].append({"type": "user", "text": user_message})
                print(conversations)
                # Construct the prompt
                prompt_history = " ".join([f"{conv['type'].capitalize()}: {conv['text']}" for conv in conversations[channel_id][-6:]])  # Last 3 pairs of user-bot interactions
                prompt = f"Based on the following conversation: {prompt_history} respond to the next question User: {user_message}"
                print(prompt)
                # Create and check thread with ChatGPT
                openai.api_key = OPENAI_API_KEY
                assistant_id = "asst_EheArdYAAxyan2HELJ4mhet5"
                response = create_and_check_thread(assistant_id, prompt)
                
                # Clean the response to remove unwanted patterns
                cleaned_response = clean_text(response)
                
                # Append the bot's response to the history
                conversations[channel_id].append({"type": "bot", "text": cleaned_response})
                
                # Reset the conversation history if it reaches 6 entries (3 user messages and 3 bot responses)
                if len(conversations[channel_id]) >= 6:
                    conversations[channel_id] = []

                # Remove 'eyes' reaction
                client.reactions_remove(
                    channel=channel_id,
                    timestamp=body["event"]["ts"],
                    name="eyes"
                )
                
                # Respond in the channel
                say(text=cleaned_response)
            except SlackApiError as e:
                logger.error(f"Error in Slack API: {e}")

            logger.info(f"User: {user_message} Bot: {cleaned_response}")


if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()