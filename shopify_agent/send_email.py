import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()
SECRETS_FILE = os.environ.get('CLIENT_SECRETS_FILE_PATH')
TOKENS_FILE = os.environ.get('CLIENT_TOKEN_FILE_PATH')
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate_gmail():
    """Shows user authentication flow and returns credentials."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(TOKENS_FILE):
        creds = Credentials.from_authorized_user_file(TOKENS_FILE, SCOPES)
    
    # If there are no valid credentials, initiate the flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Replace 'client_secret.json' with your downloaded credentials file
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKENS_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def create_message_with_attachment(sender, to, subject, message_text, file_path):
    """
    Creates a multipart/mixed message with a text body and a file attachment, 
    and then Base64URL-encodes it.
    """
    # Create a 'mixed' container for the main body and the attachment
    message = MIMEMultipart('mixed')
    message['To'] = to
    message['From'] = sender
    message['Subject'] = subject

    # Attach the email body (plain text)
    msg_body = MIMEText(message_text, 'plain')
    message.attach(msg_body)

    # Determine the file's MIME type
    content_type, encoding = mimetypes.guess_type(file_path)
    if content_type is None or encoding is not None:
        content_type = 'application/octet-stream' # Default if MIME type can't be guessed

    main_type, sub_type = content_type.split('/', 1)
    
    # Create the MIMEBase object for the attachment
    # 'application/csv' or 'text/csv' are often used for CSV files
    msg_attachment = MIMEBase(main_type, sub_type) 
    
    # Read the file content
    with open(file_path, 'rb') as f:
        msg_attachment.set_payload(f.read())
        
    # Encode the content in Base64
    encoders.encode_base64(msg_attachment)
    
    # Set the file name header
    msg_attachment.add_header(
        'Content-Disposition', 
        'attachment', 
        filename=os.path.basename(file_path)
    )

    # Attach the file to the main message container
    message.attach(msg_attachment)
    
    # Base64URL-encode the entire message for the Gmail API
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}


def send_email_with_csv_attachment(recipient_email, data_file):
    """Authenticates and sends the email with the local CSV file."""
    
    # --- Configuration ---
    # NOTE: You MUST create a local file named 'data.csv' for this to work.
    data_file = data_file
    
    # Create a dummy CSV file if it doesn't exist for testing
    if not os.path.exists(data_file):
        with open(data_file, 'w') as f:
            f.write("Header1,Header2\n")
            f.write("ValueA,100\n")
            f.write("ValueB,200\n")
        print(f"Created a dummy file: {data_file}")

    creds = authenticate_gmail()
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # --- Email Details ---
        sender_email = 'mohammadarqam0@gmail.com' 
        recipient_email = recipient_email# Change this
        subject_line = 'Shopify Store Manager Alerts'
        body_content = 'Please find the attached Excel file with the latest report about the issues identified in the Products and their proposed solution.'
        
        # 1. Format and Encode the message
        message = create_message_with_attachment(
            sender_email, 
            recipient_email, 
            subject_line, 
            body_content, 
            data_file
        )
        
        # 2. Send the message via the API
        send_message = (service.users().messages().send(userId=sender_email, body=message).execute())
        
        print(f"✅ Message Id: {send_message['id']} sent successfully with {data_file}.")
    
    except HttpError as error:
        print(f'❌ An error occurred: {error}')


import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText # Only need MIMEText for a simple body
# Removed: from email.mime.multipart import MIMEMultipart
# Removed: from email.mime.base import MIMEBase
# Removed: from email import encoders
# Removed: import mimetypes

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def authenticate_gmail():
    """Shows user authentication flow and returns credentials."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists(TOKENS_FILE):
        creds = Credentials.from_authorized_user_file(TOKENS_FILE, SCOPES)
    
    # If there are no valid credentials, initiate the flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Replace 'client_secret.json' with your downloaded credentials file
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKENS_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

# --- SIMPLIFIED MESSAGE CREATION FUNCTION ---
def create_message(sender, to, subject, message_text):
    """
    Creates a simple text message and Base64URL-encodes it.
    """
    # Create a simple MIMEText object for the plain text email body
    message = MIMEText(message_text, 'plain')
    message['To'] = to
    message['From'] = sender
    message['Subject'] = subject

    # Base64URL-encode the entire message for the Gmail API
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}


def send_simple_email(recipient_email, message_):
    """Authenticates and sends the simple email."""
    
    # Authenticate first
    creds = authenticate_gmail()
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        # --- Email Details ---
        # NOTE: 'me' is a special value that refers to the authenticated user. 
        # You can use 'me' instead of the actual sender email in the API call.
        sender_email = 'mohammadarqam0@gmail.com' 
        recipient_email = recipient_email
        subject_line = 'Shopify Store Manager Alert'
        body_content = message_
        
        # 1. Format and Encode the message
        # Use the simplified function
        message = create_message(
            sender_email, 
            recipient_email, 
            subject_line, 
            body_content
        )
        
        # 2. Send the message via the API
        # The 'userId' parameter in the API call can safely be 'me'
        send_message = (service.users().messages().send(userId=sender_email, body=message).execute())
        
        print(f"✅ Message Id: {send_message['id']} sent successfully to {recipient_email}.")
    
    except HttpError as error:
        print(f'❌ An error occurred: {error}')

# --- EXAMPLE USAGE ---
# This line is where you would call the function.
# You need to replace 'target@example.com' with the actual recipient email.
# send_simple_email('target@example.com') 
# print("\nTo run the code, uncomment the 'send_simple_email' line and provide a recipient.")