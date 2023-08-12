from __future__ import print_function

import os
import subprocess
from dotenv import load_dotenv
import sys
import importlib
import traceback
import asyncio
import os.path
import io
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from tools.gpt_functions import generate_gpt4_response, generate_gpt4_response_async
from tools.notification_functions import send_email, send_email_async
for k,v in list(sys.modules.items()):
    if k.startswith('tools') or k.startswith('.env'):
        importlib.reload(v)


# Load the environment variables from the .env file
load_dotenv()

FOLDER_ID_TO_EMAIL = {
    # '1Qdrs4naVqJH2KIcr1maQ3vuq5DGuDK-G': 'scha@cancelledfoodcoupon.com',
    # '1AUSninKPQ9mZXFaISKAXPRv4RzpB9oNx': 'mike@mantisnetworks.co',
    # '1UHH7ZuFS8anO_NIFqe25SHqPun_stmeQ': 'clint@mantisnetworks.co',
    # '1ibUUpCy74WUROr5TSa-pLYLYM6ivUUmZ': 'loren@mantisnetworks.co',
    '1SwickgZ8MDK_BIyL7IhSn0oZdVxAMzHE': 'joshua.stapleton.ai@gmail.com',
    # '1BO0yHZO8CfrSzX2SvWhD1uUbq_M3L7X2': 'bartdenil12@gmail.com',
    # '1sA77uMfOftiR8njcATy_IFBng8-apXv0': 'brensuzy@gmail.com',
    # '1csJ4knxQ5Yp4vESB85ZMxkL8e5qKKkE_': 'brendanjstapleton@gmail.com',
}

# folder ids from google drive
FOLDER_NAME_TO_FOLDER_ID = {
    # 'audios_scha': '1Qdrs4naVqJH2KIcr1maQ3vuq5DGuDK-G',
    # 'audios_mike': '1AUSninKPQ9mZXFaISKAXPRv4RzpB9oNx',
    # 'audios_clint': '1UHH7ZuFS8anO_NIFqe25SHqPun_stmeQ',
    # 'audios_loren': '1ibUUpCy74WUROr5TSa-pLYLYM6ivUUmZ',
    'audios_josh': '1SwickgZ8MDK_BIyL7IhSn0oZdVxAMzHE',
    # 'audios_bart': '1BO0yHZO8CfrSzX2SvWhD1uUbq_M3L7X2',
    # 'audios_mom': '1sA77uMfOftiR8njcATy_IFBng8-apXv0',
    # 'audios_dad': '1csJ4knxQ5Yp4vESB85ZMxkL8e5qKKkE_'
}

FOLDER_NAME_TO_EMAIL = {folder_name: FOLDER_ID_TO_EMAIL[folder_id] for folder_name, folder_id in FOLDER_NAME_TO_FOLDER_ID.items()}


async def whisper_async(target_file:str, local_folder:str):
    base = os.path.splitext(target_file)[0]
    input_file = os.path.join(local_folder, target_file)
    output_file = os.path.join(local_folder, f"{base}.wav")

    if target_file.endswith('.m4a') or target_file.endswith('.mp3'):
        print(f"Processing {target_file}...")
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', input_file, '-ar', '16000', output_file, 
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
        )
        await process.wait()
    elif target_file.endswith('.wav'): # move straight to F
        print(f"Processing {target_file} file as .wav...")
    else:
        print(f"Unsupported file format: {target_file}")
        return

    print("Running whisper to get transcript...")
    process = await asyncio.create_subprocess_exec(
        './main', '-f', output_file, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
    )
    await process.wait()

    return output_file


async def fred_async(filename:str):
    print("FILENAME:", filename)
    receiving_email_address = FOLDER_NAME_TO_EMAIL.get(filename.split('/')[0])
    try:
        if ("transcript" in filename.lower()) or ('transcribe' in filename.lower()): # simply send the transcribed text
            print("Sending transcript...")
            with open(filename, 'r') as file:
                transcript = file.read()
            # Code to send the transcript
            asyncio.create_task(send_email_async(os.environ.get('SENDING_EMAIL_ADDRESS'), 'joshua.stapleton.ai@gmail.com', "FRED response for " + filename, "TRANSCRIPT:\n" + transcript, os.environ.get('EMAIL_PASSWORD')))

            if receiving_email_address:  # If an email address was found
                asyncio.create_task(send_email_async(os.environ.get('SENDING_EMAIL_ADDRESS'), receiving_email_address, "FRED response for " + filename, "TRANSCRIPT:\n" + transcript, os.environ.get('EMAIL_PASSWORD')))

        else:
            print("Running Fred...")
            with open(filename, 'r') as file:
                transcript = file.read()
                response = await generate_gpt4_response_async(transcript, 1) # we await this because we can't send the email until we get a response from the API
                asyncio.create_task(send_email_async(os.environ.get('SENDING_EMAIL_ADDRESS'), 'joshua.stapleton.ai@gmail.com', "FRED response for " + filename, response + "\n\n-----------------------\n\nTRANSCRIPT:\n" + transcript, os.environ.get('EMAIL_PASSWORD')))

                # UNCOMMENT TO SEND TO CORRECT EMAIL
                if receiving_email_address:  # If an email address was found
                    asyncio.create_task(send_email_async(os.environ.get('SENDING_EMAIL_ADDRESS'), receiving_email_address, "FRED response for " + filename, response + "\n\n-----------------------\n\nTRANSCRIPT:\n" + transcript, os.environ.get('EMAIL_PASSWORD')))

    except Exception as e:
        print(f"Exception in fred_async: {e}")
        traceback.print_exc()


async def whisper_and_fred(target_file:str, local_folder:str):
    filename = await whisper_async(target_file, local_folder) # need to wait for whisper to finish running before firing off fred
    response = await fred_async(filename + ".txt")
    return response


# ideally we would just load the audios into memory to avoid all this download nonsense. 
# However, whisper requires a file path, so we have to download the files to disk first.
# Also, audios might be too big.
def download_file(drive_service, file, local_folder):
    # Download file
    request = drive_service.files().get_media(fileId=file['id'])
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    print("Downloading file...", file['name'])
    while done is False:
        status, done = downloader.next_chunk()
    downloaded_file_path = os.path.join(local_folder, file['name'])
    with io.open(downloaded_file_path, 'wb') as f:
        print("Writing file...", file['name'])
        fh.seek(0)
        f.write(fh.read())
    
    return downloaded_file_path


async def download_file_async(drive_service, file, local_folder, loop):
    with ThreadPoolExecutor() as executor:
        file_path = await loop.run_in_executor(executor, download_file, drive_service, file, local_folder)
        # Process downloaded file asynchronously here
        print("Downloaded and processed", file_path)