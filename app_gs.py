import time
from dotenv import load_dotenv
import os
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App
import re
import time
import os
import tempfile
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings
from langchain.schema.output_parser import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import PromptTemplate
from langchain.vectorstores.utils import filter_complex_metadata
import os
import argparse

os.environ["OPENAI_API_KEY"] = 
os.environ["ANTHROPIC_API_KEY"] = 
SLACK_APP_TOKEN = 
SLACK_BOT_TOKEN = 

class ChatCLI:
    instance = None  # Class variable to hold the singleton instance

    def __new__(cls, index_path='index_gs'):
        """
        Ensures that only one instance of ChatCLI is created (singleton pattern).
        This instance will be reused throughout the lifecycle of the application.
        """
        if cls.instance is None:
            cls.instance = super(ChatCLI, cls).__new__(cls)
            cls.instance.initialize(index_path)
        return cls.instance

    def initialize(self, index_path):
        """
        Initializes the necessary components for the chat application, including
        the chat model, prompt template, vector store, and retriever. This method is
        called only once when the first instance of ChatCLI is created.
        """
        self.model = ChatAnthropic(model='claude-3-opus-20240229')
        self.prompt = PromptTemplate.from_template(
            """
            As Destify's friendly assistant, you will have to answer questions. When answering. Your specialty is Guest Services.
            Be sure to consult all catalog documents thoroughly to list all relevant products. If the query goes beyond our documents kindly suggest alternatives without indicating the absence of information, using "according to our information" as guidance. 

            You must answer questions to guests, you may use documents provided that contain questions and answers that we have answered in the past. You may also use the official Destify documents.

            Respond to questions about Destify's policies and services based on the records provided, politely declining unrelated questions. 

            Maintain a positive tone in your communication, offering to arrange calls without directly quoting your sources. 
            In your responses, always refer to the information in the files provided. Remember that you can access the files and analyze them even though the system indicates otherwise. 
            Always consult these files before answering.</s>
            
            ##Question: {question} 
            Context: {context} 
            Answer: 
            """
        )
        self.vector_store = Chroma(persist_directory=index_path, embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"))
        self.retriever = self.vector_store.as_retriever()
        self.chain = ({"context": self.retriever, "question": RunnablePassthrough()}
                      | self.prompt
                      | self.model
                      | StrOutputParser())

    def ask(self, query: str):
        """
        Processes a user query through the chat chain to generate a response.
        """
        if not self.chain:
            return "Error in initializing chain."
        return self.chain.invoke(query)


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
            

            chat_cli = ChatCLI()
            response = chat_cli.ask(prompt)
            
            # Limpia la respuesta simulada
            cleaned_response = clean_text(response)
            
            # Añade la respuesta del bot al historial
            conversations[user_id].append(("bot", cleaned_response))
            
            # Resetea el historial si alcanza 6 entradas
            print(prompt_history)
            if len(conversations[user_id]) >= 2:
                conversations[user_id] = []

            # Responde en el DM del usuario
            say(text=cleaned_response)
        except Exception as e:
            logger.error(f"Error processing message: {e}")



if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()