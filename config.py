import os
from dotenv import load_dotenv

# Load environment variables from a .env file (if present)
load_dotenv()

# Grist API Configuration
GRIST_SERVER = os.getenv("GRIST_SERVER")  # Default for local dev
GRIST_DOC_ID = os.getenv("GRIST_DOC_ID")
GRIST_API_KEY = os.getenv("GRIST_API_KEY")

# Confluence API Configuration
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_PAGE_ID = os.getenv("CONFLUENCE_PAGE_ID")
CONFLUENCE_QSG_PAGE_ID = os.getenv("CONFLUENCE_QSG_PAGE_ID")
CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL")
