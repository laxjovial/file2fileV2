import dropbox
import streamlit as st
from dropbox.exceptions import AuthError, ApiError

def upload_to_dropbox(access_token, file_content_bytes, dropbox_path):
    """
    Uploads a file to Dropbox.
    :param access_token: Your Dropbox access token.
    :param file_content_bytes: The content of the file as bytes.
    :param dropbox_path: The full path in Dropbox where the file will be saved (e.g., "/my_converted_file.pdf").
    """
    if not access_token or access_token == "YOUR_DROPBOX_TOKEN_HERE":
        raise Exception("Dropbox access token is not configured. Please set it in .streamlit/secrets.toml")

    try:
        dbx = dropbox.Dropbox(access_token)
        # Check if the token is valid
        dbx.users_get_current_account()
        
        # Upload the file
        dbx.files_upload(file_content_bytes, dropbox_path, mode=dropbox.files.WriteMode('overwrite'))
        st.success(f"File '{dropbox_path}' uploaded to Dropbox!")

    except AuthError:
        raise Exception("Invalid Dropbox access token. Please check your token.")
    except ApiError as err:
        # This could be due to invalid path, quota limits, etc.
        if err.error.is_path() and err.error.get_path().is_insufficient_space():
            raise Exception("Dropbox upload failed: Insufficient space.")
        elif err.user_message_text:
            raise Exception(f"Dropbox upload failed: {err.user_message_text}")
        else:
            raise Exception(f"Dropbox upload failed: {err}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred during Dropbox upload: {e}")

