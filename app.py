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
assistant_id = "asst_97amebtgQjowJj7rJCgg949i"


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
    # Define el patrón para remover
    pattern_to_remove = r"【\d+†.*?】"
    # Usa re.sub para reemplazar el patrón encontrado con una cadena vacía
    cleaned_text = re.sub(pattern_to_remove, "", original_text)
    return cleaned_text

@app.event("message")
def handle_direct_message_events(body, logger, say):
    channel_id = body["event"]["channel"]

    try:
        channel_info = client.conversations_info(channel=channel_id)
        is_direct_message = channel_info["channel"]["is_im"]
                    # Añadir reacción 'eyes' para indicar procesamiento
        client.reactions_add(
                channel=body["event"]["channel"],
                timestamp=body["event"]["ts"],
                name="eyes"
            )
    except Exception as e:
        logger.error(f"Error fetching channel info: {e}")
        return

    if not is_direct_message:
        logger.info(f"Message not in DM, channel_id: {channel_id}")
        return  # Asegúrate de retornar si no es un DM

    if is_direct_message:
        user_id = body["event"]["user"]
        user_message = body["event"]["text"]
        print(user_message)
        try:
            # Asegura que el historial de conversaciones del usuario existe
            if user_id not in conversations:
                conversations[user_id] = []

            # Añade el mensaje del usuario al historial
            conversations[user_id].append(("user", user_message))

            # Construye el prompt para el modelo
            prompt_history = " ".join([f"{conv[0].capitalize()}: {conv[1]}" for conv in conversations[user_id][-6:]])
            prompt = f"Based on the following conversation: {prompt_history} respond to the next question User: {user_message}"
            
            # Aquí deberías llamar a tu modelo o servicio para generar una respuesta
            # Por simplicidad, aquí se simula una respuesta
                        # Usar tu modelo para generar una respuesta
            openai.api_key = OPENAI_API_KEY
            assistant_id = "asst_97amebtgQjowJj7rJCgg949i"
            response = create_and_check_thread(assistant_id, prompt)
            
            # Limpia la respuesta simulada
            cleaned_response = clean_text(response)
            
            # Añade la respuesta del bot al historial
            conversations[user_id].append(("bot", cleaned_response))
            
            # Resetea el historial si alcanza 6 entradas
            print(prompt_history)
            if len(conversations[user_id]) >= 6:
                conversations[user_id] = []

            # Responde en el DM del usuario
            say(text=cleaned_response)
        except Exception as e:
            logger.error(f"Error processing message: {e}")



if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()