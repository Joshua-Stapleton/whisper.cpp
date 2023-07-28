import openai
from dotenv import load_dotenv
import os
import aiohttp
import re
import asyncio
import json
from tools.notification_functions import send_email, send_email_async
load_dotenv()
OPENAI_KEY = os.environ.get('OPEN_AI_KEY')


def api_endpoint_from_url(request_url):
    """Extract the API endpoint from the request URL."""
    match = re.search('^https://[^/]+/v\\d+/(.+)$', request_url)
    return match[1]


def generate_gpt3_response(prompt:str) -> str:
    openai.api_key = OPENAI_KEY
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5,
    )
    message = response["choices"][0]["text"]
    return message


def generate_gpt4_response(prompt:str) -> str:
    print("Generating GPT-4 response...")
    openai.api_key = OPENAI_KEY
    message = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        max_tokens=2048,
        temperature=1,
        messages = message
    )

    return response['choices'][0]['message']['content']


async def generate_gpt4_response_async(prompt:str, task_num:int) -> str:
    print("Generating GPT-4 response for task #", task_num, "...")
    openai.api_key = OPENAI_KEY
    messages = {'model': 'gpt-4', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.8}
    api_endpoint = "https://api.openai.com/v1/chat/completions"
    request_header = {"Authorization": f"Bearer {OPENAI_KEY}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url=api_endpoint, headers=request_header, json=messages) as response:
                response = await response.json()
                print("FINISHED TASK NUM", task_num, ". RESPONSE:", response['choices'][0]['message']['content'])
                response = response['choices'][0]['message']['content']
                asyncio.create_task(send_email_async(os.environ.get('SENDING_EMAIL_ADDRESS'), 'joshua.stapleton.ai@gmail.com', "FRED response for task " + str(task_num), response + "\n\n-----------------------\n\nTRANSCRIPT:\n", os.environ.get('EMAIL_PASSWORD')))
                return response

    except Exception as e:
        print(f"Request {task_num} failed with Exception {e}")
