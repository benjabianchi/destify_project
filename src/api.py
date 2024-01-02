from flask import Flask, request, jsonify
import time
import openai
import time
from dotenv import load_dotenv
import os
from openai._client import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv('SECRET_KEY')
openai = OpenAI(api_key = OPENAI_API_KEY)
assistant_id = "asst_r1T1n60YQhDuqF4beV5PYcyM"

def create_thread(ass_id,prompt):
    #Get Assitant
    #assistant = openai.beta.assistants.retrieve(ass_id)

    #create a thread
    thread = openai.beta.threads.create()
    my_thread_id = thread.id


    #create a message
    message = openai.beta.threads.messages.create(
        thread_id=my_thread_id,
        role="user",
        content=prompt
    )

    #run
    run = openai.beta.threads.runs.create(
        thread_id=my_thread_id,
        assistant_id=ass_id,
    ) 

    return run.id, thread.id


def check_status(run_id,thread_id):
    run = openai.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run_id,
    )
    return run.status


def get_response(assistant_id, prompt):
    my_run_id, my_thread_id = create_thread(assistant_id, prompt)
    print(f"Run: {my_run_id}, ")
    status = check_status(my_run_id, my_thread_id)
    while status != "completed":
        status = check_status(my_run_id, my_thread_id)
        time.sleep(2)

    response = openai.beta.threads.messages.list(thread_id=my_thread_id)

    if response.data:
        print(response.data[0].content[0].text.value)


app = Flask(__name__)


@app.route('/generate_response', methods=['POST'])
def generate_response():
    assistant_id = "asst_r1T1n60YQhDuqF4beV5PYcyM"  # Replace with your actual assistant ID
    data = request.json

    try:
        if 'prompt' in data:
            # Use your existing logic to generate the response
            my_run_id, my_thread_id = create_thread(assistant_id, data['prompt'])
            status = check_status(my_run_id, my_thread_id)

            while status != "completed":
                status = check_status(my_run_id, my_thread_id)
                time.sleep(2)

            response = openai.beta.threads.messages.list(thread_id=my_thread_id)

            if response.data:
                return jsonify({"response": response.data[0].content[0].text.value})
            else:
                return jsonify({"response": "No response generated."})
        else:
            return jsonify({"error": "No prompt provided"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)