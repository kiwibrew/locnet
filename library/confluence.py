import os
import json
import time
import requests
import base64
import re
from requests.auth import HTTPBasicAuth
import logging
from config import CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN, CONFLUENCE_PAGE_ID, CONFLUENCE_QSG_PAGE_ID, CONFLUENCE_BASE_URL

# Constants
CACHE_FILE = "cache/confluence_documentation.json"
CACHE_QSG_FILE = "cache/confluence_qsg.json"  # Cache file for Quick Start Guide
CACHE_IMAGES_DIR = "static/confluence_images"
CACHE_EXPIRY = 86400  # 24 hours in seconds


def fetch_confluence_content(page_id=CONFLUENCE_PAGE_ID):
    """
    Fetches content from Confluence API for the specified page ID.
    
    Args:
        page_id (str): The Confluence page ID to fetch content from
    
    Returns:
        str: HTML content of the Confluence page
    """
    # Using REST API v2 endpoint
    url = f"{CONFLUENCE_BASE_URL}/api/v2/pages/{page_id}?body-format=storage"
    
    auth = HTTPBasicAuth(CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()  # Raise exception for non-200 status codes
        
        data = response.json()
        html_content = data['body']['storage']['value']
        return html_content
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Confluence content: {e}")
        return "<p>Error fetching documentation content. Please try again later.</p>"


def fetch_confluence_attachments(page_id=CONFLUENCE_PAGE_ID):
    """
    Fetches all attachments for the specified Confluence page.
    
    Args:
        page_id (str): The Confluence page ID to fetch attachments from
    
    Returns:
        dict: Dictionary mapping attachment filenames to their download URLs
    """
    # Using REST API v2 endpoint
    url = f"{CONFLUENCE_BASE_URL}/api/v2/pages/{page_id}/attachments"
    
    auth = HTTPBasicAuth(CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        attachments = {}
        
        for attachment in data.get('results', []):
            filename = attachment.get('title', '')
            download_link = attachment.get('downloadLink', '')
            
            if filename and download_link:
                # downloadLink is a relative URL, prepend base URL
                download_url = f"{CONFLUENCE_BASE_URL}{download_link}"
                attachments[filename] = download_url
        
        return attachments
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Confluence attachments: {e}")
        return {}


def download_and_cache_image(url, filename):
    """
    Downloads an image from the given URL and caches it locally.
    
    Args:
        url (str): URL to download the image from
        filename (str): Filename to save the image as
        
    Returns:
        str: Path to the cached image file, or None if download failed
    """
    # Ensure cache directory exists
    os.makedirs(CACHE_IMAGES_DIR, exist_ok=True)
    
    # Generate a safe filename
    safe_filename = re.sub(r'[^\w\-.]', '_', filename)
    cache_path = os.path.join(CACHE_IMAGES_DIR, safe_filename)
    
    # If the file already exists in cache, return its path
    if os.path.exists(cache_path):
        return f"/{cache_path}"
    
    # Download the image
    try:
        auth = HTTPBasicAuth(CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN)
        response = requests.get(url, auth=auth, stream=True)
        response.raise_for_status()
        
        with open(cache_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return f"/{cache_path}"
    
    except Exception as e:
        logging.error(f"Error downloading image {filename}: {e}")
        return None


def process_image_references(html_content, attachments):
    """
    Processes image references in the HTML content and replaces them with
    references to locally cached images.
    
    Args:
        html_content (str): HTML content from Confluence
        attachments (dict): Dictionary mapping attachment filenames to download URLs
        
    Returns:
        str: Processed HTML content with updated image references
    """
    processed_html = html_content
    
    # Find all image references in the HTML content
    image_pattern = r'<ac:image[^>]*>.*?<ri:attachment ri:filename="([^"]+)"[^>]*>.*?</ac:image>'
    
    # Extract attributes from ac:image tags
    def extract_image_attributes(tag):
        width_match = re.search(r'ac:width="(\d+)"', tag)
        width = width_match.group(1) if width_match else None
        
        align_match = re.search(r'ac:align="([^"]+)"', tag)
        align = align_match.group(1) if align_match else None
        
        alt_match = re.search(r'ac:alt="([^"]+)"', tag)
        alt = alt_match.group(1) if alt_match else None
        
        return width, align, alt
    
    # Replace each image tag with an HTML img tag
    for match in re.finditer(image_pattern, processed_html, re.DOTALL):
        full_tag = match.group(0)
        filename = match.group(1)
        
        if filename in attachments:
            # Download and cache the image
            image_path = download_and_cache_image(attachments[filename], filename)
            
            if image_path:
                # Extract image attributes
                width, align, alt = extract_image_attributes(full_tag)
                
                # Build the img tag with appropriate attributes
                img_tag = f'<img src="{image_path}"'
                if width:
                    img_tag += f' width="{width}"'
                if alt:
                    img_tag += f' alt="{alt}"'
                img_tag += ' class="img-fluid"'  # Make image responsive
                
                # Add alignment if specified
                img_tag += '>'  # Close the img tag first
                
                if align:
                    if align == "center":
                        img_tag = f'<div style="text-align: center;">{img_tag}</div>'
                    elif align == "right":
                        img_tag = f'<div style="text-align: right;">{img_tag}</div>'
                
                # Replace the Confluence tag with the HTML img tag
                processed_html = processed_html.replace(full_tag, img_tag)
    
    return processed_html


def get_documentation_content():
    """
    Gets documentation content from cache if available and not expired,
    otherwise fetches from Confluence API and updates cache.
    
    Returns:
        str: HTML content of the documentation with processed image references
    """
    # Check if cache file exists and is not expired
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            if time.time() - cache_data['timestamp'] < CACHE_EXPIRY:
                return cache_data['content']
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"Cache file is invalid: {e}")
    
    # Fetch fresh content and attachments from Confluence
    content = fetch_confluence_content()
    attachments = fetch_confluence_attachments()
    
    # Process image references in the content
    processed_content = process_image_references(content, attachments)
    
    # Update cache
    try:
        cache_data = {
            'timestamp': time.time(),
            'content': processed_content
        }
        
        # Ensure cache directory exists
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    
    except Exception as e:
        logging.error(f"Error updating cache: {e}")
    
    return processed_content


def get_qsg_content():
    """
    Gets Quick Start Guide content from cache if available and not expired,
    otherwise fetches from Confluence API and updates cache.
    
    Returns:
        str: HTML content of the Quick Start Guide with processed image references
    """
    # Check if cache file exists and is not expired
    if os.path.exists(CACHE_QSG_FILE):
        try:
            with open(CACHE_QSG_FILE, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            if time.time() - cache_data['timestamp'] < CACHE_EXPIRY:
                return cache_data['content']
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"Cache file is invalid: {e}")
    
    # Fetch fresh content and attachments from Confluence
    content = fetch_confluence_content(CONFLUENCE_QSG_PAGE_ID)
    attachments = fetch_confluence_attachments(CONFLUENCE_QSG_PAGE_ID)
    
    # Process image references in the content
    processed_content = process_image_references(content, attachments)
    
    # Update cache
    try:
        cache_data = {
            'timestamp': time.time(),
            'content': processed_content
        }
        
        # Ensure cache directory exists
        os.makedirs(os.path.dirname(CACHE_QSG_FILE), exist_ok=True)
        
        with open(CACHE_QSG_FILE, 'w') as f:
            json.dump(cache_data, f)
    
    except Exception as e:
        logging.error(f"Error updating cache: {e}")
    
    return processed_content