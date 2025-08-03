import os
import io
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file'] # Allows app to access files it creates

def get_google_drive_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check if credentials.json is uploaded via Streamlit secrets or directly
            if 'google_credentials' in st.secrets:
                # Use credentials from Streamlit secrets (if stored as string)
                creds_info = json.loads(st.secrets['google_credentials'])
                flow = InstalledAppFlow.from_client_config(creds_info, SCOPES)
            elif os.path.exists('credentials.json'):
                # Use credentials.json file if present in the repo
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            else:
                st.error("Google Drive 'credentials.json' not found. Please upload it to your Streamlit repository or configure it in Streamlit secrets.")
                st.stop() # Stop execution if credentials are not found

            # This will open a new browser tab for OAuth.
            # In Streamlit Cloud, this flow can be tricky.
            # For a more robust solution in production, consider a custom OAuth callback.
            # For this example, we'll assume the user can complete the flow.
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.markdown(f"Please authorize Google Drive access by clicking this link: [Authorize Google Drive]({auth_url})", unsafe_allow_html=True)
            
            # Streamlit re-runs the script, so we need to wait for the user to authorize
            # and then handle the redirect. This is a simplified flow for demonstration.
            # In a real app, you'd need to handle the redirect URI and code exchange.
            st.warning("After authorizing, you might need to manually copy the redirect URL and paste it back here if the automatic redirect doesn't work in Streamlit Cloud.")
            auth_code = st.text_input("Enter the authorization code from the redirect URL (if prompted):")
            if auth_code:
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            else:
                st.stop() # Wait for auth code

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except HttpError as error:
        st.error(f'An error occurred: {error}')
        return None

def upload_to_google_drive(file_content_bytes, file_name):
    service = get_google_drive_service()
    if not service:
        raise Exception("Google Drive service not available.")

    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(io.BytesIO(file_content_bytes),
                              mimetype='application/octet-stream',
                              resumable=True)
    try:
        file = service.files().create(body=file_metadata, media_body=media,
                                      fields='id').execute()
        st.write(f"File ID: {file.get('id')}")
        st.success(f"File '{file_name}' uploaded to Google Drive!")
    except HttpError as error:
        st.error(f'An error occurred during upload: {error}')
        raise Exception(f"Google Drive upload failed: {error}")

