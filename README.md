# file2fileV2

Setup Instructions (Recap and Clarification)

Google Drive API:

Go to Google Cloud Console.

Create a new project.

Navigate to "APIs & Services" -> "Enabled APIs & services". Search for and enable "Google Drive API".

Go to "APIs & Services" -> "OAuth consent screen".

Choose "External" user type.

Fill in required app information.

In "Scopes", add .../auth/drive.file. This scope limits your app to only accessing files it creates, which is good for security.

Add yourself as a "Test user" if you're not publishing the app.

Go to "APIs & Services" -> "Credentials".

Click "CREATE CREDENTIALS" -> "OAuth client ID".

Choose "Web application".

For "Authorized redirect URIs", add http://localhost:8501 (for local Streamlit testing) and https://share.streamlit.io/your-github-username/your-repo-name/main/file2file.py (replace with your actual Streamlit Cloud URL).

Download the credentials.json file.

How to use credentials.json with Streamlit Cloud:

Option A (Recommended for simplicity): Upload credentials.json directly to your Streamlit Cloud app's secrets. In your app's dashboard, go to "Settings" -> "Secrets" and upload it. Streamlit will then make it available as st.secrets["credentials"] or similar. You might need to adjust google_drive.py to read from st.secrets if you do this.

Option B (Less secure for public repos): Place credentials.json directly in your GitHub repository. Be very careful with this if your repo is public, as it exposes your credentials. For a private repo, it can work, but Streamlit Secrets is generally preferred.

Dropbox API:

Go to Dropbox App Console.

Click "Create app".

Choose "Scoped access" (recommended for new apps).

Choose "Full Dropbox" access type.

Give your app a name.

Once created, go to the "Settings" tab of your app.

Under "OAuth 2", click "Generate" to generate an access token.

Copy this long-lived access token.

Store this token securely: Add it to your .streamlit/secrets.toml file as DROPBOX_ACCESS_TOKEN = "your_token_here".
