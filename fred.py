import asyncio
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from datetime import datetime
from googleapiclient.errors import HttpError
import os
import boto3
from botocore.exceptions import ClientError
from googleapiclient.discovery import build
from tools.fred_tools import FOLDER_NAME_TO_FOLDER_ID, download_file, whisper_and_fred

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']



# Use this code snippet in your app.
# If you need more information about configurations
# or implementing the sample code, visit the AWS docs:
# https://aws.amazon.com/developer/language/python/


def get_secret():
    secret_name = "client_secret_782650429580-k51cnfcs0gmn6kdkn7t5elbchinpspo1.apps.googleusercontent.com.json"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    secret = get_secret_value_response['SecretString']

    # Your code goes here.



async def main():
    try:
        """Shows basic usage of the Drive v3 API.
        Lists the names and ids of the first 10 files the user has access to.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_secret_content = get_secret('client_secret_782650429580-k51cnfcs0gmn6kdkn7t5elbchinpspo1.apps.googleusercontent.com.json')
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_content, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        drive_service = build('drive', 'v3', credentials=creds)
        loop = asyncio.get_event_loop()
        # Get a list of already downloaded files
        downloaded_files = {local_folder: set(os.listdir(local_folder)) for local_folder in FOLDER_NAME_TO_FOLDER_ID.keys()}
        print("Downloaded files:", downloaded_files)

        # Continuously poll Google Drive folder for new files
        while True:
            for local_folder, folder_id in FOLDER_NAME_TO_FOLDER_ID.items():
                # print(local_folder)
                request = drive_service.files().list(
                q="'{}' in parents and trashed = false".format(folder_id),
                fields='nextPageToken, files(id, name)',
                pageToken=None).execute()
                
                # Get all files in the Google Drive folder
                all_files = request.get('files', [])
                # print("All files currently in GD:", all_files)

                # Remove already downloaded files
                files_to_download = [file for file in all_files if file['name'] not in downloaded_files[local_folder]]
                # print("Files to download:", files_to_download)
                
                # only for files which have not been downloaded
                for file in files_to_download: # this is not perfectly ideal, since
                    print("Detected new file in " + local_folder + ": " + file['name'] + " at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    # loop.create_task(download_file_async(drive_service, file, local_folder, loop))

                    try:
                        downloaded_file_path = download_file(drive_service, file, local_folder) # this is blocking so we can't make it async
                    except Exception as e:
                        print(e)
                    
                    # Add file to the record of downloaded files so do we have to await
                    downloaded_files[local_folder].add(file['name']) # only do this if it was downloaded successfully

                    # process the file to .wav and run Fred - get GPT response and send email
                    asyncio.create_task(whisper_and_fred(target_file=file['name'], local_folder=local_folder))
                await asyncio.sleep(1) # allows for progress to be made on another coroutine - namely, whisper_and_fred

    except HttpError as error:
        print(f"An HTTP error occurred: {error}")


asyncio.run(main()) # for notebook since event loop already created