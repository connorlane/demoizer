from bs4 import BeautifulSoup
import requests
import os
import urllib.parse
from pathlib import Path
import hashlib
import time
import json
import argparse
import sys

# Load configuration from JSON file
def load_config(config_file="demoizer_settings.json"):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found.")
        print("Please create a demoizer_settings.json file with your configuration.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration file '{config_file}': {e}")
        return []

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Process HTML files: remove scripts, download resources, and replace links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default JSON config file
  python demoizer.py
  
  # Use custom JSON config file
  python demoizer.py --config my_config.json
  
  # Process single file with command line args
  python demoizer.py --input GoogleRaw.html --output Google.html --link-replacement SearchResults.html --base-url https://www.google.com
  
  # Process single file with minimal args (uses defaults)
  python demoizer.py --input GoogleRaw.html --output Google.html
        """
    )
    
    # Configuration file option
    parser.add_argument('--config', '-c', 
                       default='demoizer_settings.json',
                       help='JSON configuration file (default: demoizer_settings.json)')
    
    # Single file processing options
    parser.add_argument('--input', '-i',
                       help='Input HTML file to process')
    parser.add_argument('--output', '-o', 
                       help='Output HTML file name')
    parser.add_argument('--link-replacement', '-l',
                       default='#',
                       help='URL to replace all links with (default: #)')
    parser.add_argument('--base-url', '-b',
                       default='https://www.google.com',
                       help='Base URL for resolving relative URLs (default: https://www.google.com)')
    
    return parser.parse_args()

def get_files_to_process():
    """Get files to process based on command line arguments or config file"""
    args = parse_arguments()
    
    # If input and output are specified, use command line mode
    if args.input and args.output:
        return [{
            "input_filename": args.input,
            "output_filename": args.output,
            "link_replacement": args.link_replacement,
            "base_url": args.base_url
        }]
    
    # Otherwise, use config file
    if args.input or args.output:
        print("Error: Both --input and --output must be specified for command line mode")
        sys.exit(1)
    
    return load_config(args.config)

# Load files to process from configuration or command line
files_to_process = get_files_to_process()

# Exit if no valid configuration found
if not files_to_process:
    print("No valid configuration found. Exiting.")
    exit(1)

def create_local_filename(url, resources_dir):
    """Create a safe local filename from a URL"""
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Get the path and filename
    path = parsed.path
    if not path or path == '/':
        # If no path, use domain name
        filename = parsed.netloc.replace('.', '_') + '.html'
    else:
        # Extract filename from path
        filename = os.path.basename(path)
        if not filename:
            # If path ends with /, use the directory name
            filename = os.path.basename(os.path.dirname(path)) + '.html'
    
    # Handle special Google bundled resources
    if 'xjs' in path and '_/ss/' in path:
        filename = 'google_bundle_styles.css'
    elif 'xjs' in path and '_/js/' in path:
        filename = 'google_bundle_scripts.js'
    elif '/images/' in path:
        # Keep original extension for images
        if '.' not in filename:
            filename += '.png'
    
    # If no extension, try to guess from URL or default to .html
    if '.' not in filename:
        if any(keyword in url.lower() for keyword in ['css', 'style', '/ss/']):
            filename += '.css'
        elif any(keyword in url.lower() for keyword in ['js', 'script', '/js/']):
            filename += '.js'
        elif any(keyword in url.lower() for keyword in ['font', 'woff', 'ttf']):
            filename += '.woff2'
        elif any(keyword in url.lower() for keyword in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']):
            filename += '.png'
        else:
            filename += '.html'
    
    # Make filename safe for filesystem
    filename = "".join(c for c in filename if c.isalnum() or c in '.-_').rstrip()
    
    # Add hash to avoid conflicts
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    name, ext = os.path.splitext(filename)
    safe_filename = f"{name}_{url_hash}{ext}"
    
    return os.path.join(resources_dir, safe_filename)

def download_resource(url, local_path, session):
    """Download a resource from URL to local path"""
    try:
        # Add protocol if missing
        if url.startswith('//'):
            url = 'https:' + url
        elif not url.startswith(('http://', 'https://')):
            return False
            
        print(f"  Downloading: {url}")
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = session.get(url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Write the file
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"    Saved to: {local_path}")
        return True
        
    except Exception as e:
        print(f"    Failed to download {url}: {e}")
        return False

def process_html_file(input_file, output_file, link_replacement, base_url):
    """Process a single HTML file: remove scripts, replace links, download resources, and remove ping attributes"""
    print(f"Processing {input_file} -> {output_file}")
    print(f"  Base URL: {base_url}")
    
    # Create resources directory
    resources_dir = "resources"
    os.makedirs(resources_dir, exist_ok=True)
    
    # Read the original HTML
    with open(input_file, "r", encoding="utf-8") as f:
        html = f.read()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Create a session for downloading resources
    session = requests.Session()
    
    # Dictionary to track downloaded resources (URL -> local path)
    downloaded_resources = {}

    # Process different types of resources
    resource_selectors = [
        # Images
        ('img', 'src'),
        # SVG images
        ('image', 'src'),
        # Meta tags with image content
        ('meta[itemprop="image"]', 'content'),
        ('meta[property="og:image"]', 'content'),
        ('meta[name="twitter:image"]', 'content'),
        # CSS files
        ('link', 'href'),
        # JavaScript files (we'll remove scripts but handle other JS references)
        ('script', 'src'),
        # Favicon
        ('link[rel="icon"]', 'href'),
        ('link[rel="shortcut icon"]', 'href'),
        # Fonts and other resources in CSS url() functions will be handled separately
    ]
    
    print(f"  Downloading external resources...")
    
    for selector, attr in resource_selectors:
        elements = soup.select(selector)
        for element in elements:
            if element.has_attr(attr):
                url = element[attr]
                
                # Skip data URLs, javascript:, mailto:, tel:, etc.
                if url.startswith(('data:', 'javascript:', 'mailto:', 'tel:', '#')):
                    continue
                
                # Convert relative URLs to absolute URLs
                if url.startswith('/'):
                    # Absolute path relative to domain
                    url = urllib.parse.urljoin(base_url, url)
                elif not url.startswith(('http://', 'https://', '//')):
                    # Relative path - resolve against base URL
                    url = urllib.parse.urljoin(base_url, url)
                
                # Skip if still not a valid external URL
                if not url.startswith(('http://', 'https://', '//')):
                    continue
                
                # Check if we've already downloaded this resource
                if url in downloaded_resources:
                    element[attr] = downloaded_resources[url]
                    continue
                
                # Create local filename
                local_path = create_local_filename(url, resources_dir)
                
                # Download the resource
                if download_resource(url, local_path, session):
                    # Update the reference in HTML
                    relative_path = os.path.relpath(local_path, os.path.dirname(output_file))
                    # Ensure forward slashes for web compatibility
                    relative_path = relative_path.replace('\\', '/')
                    element[attr] = relative_path
                    downloaded_resources[url] = relative_path
                    
                    # Small delay to be respectful
                    time.sleep(0.1)

    # Process CSS files for embedded resources (fonts, images in CSS)
    print(f"  Processing CSS files for embedded resources...")
    for css_file in [path for url, path in downloaded_resources.items() if path.endswith('.css')]:
        try:
            with open(css_file, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            # Find URLs in CSS (basic regex for url() functions)
            import re
            css_urls = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', css_content)
            
            for css_url in css_urls:
                # Convert relative URLs to absolute
                if css_url.startswith('//'):
                    css_url = 'https:' + css_url
                elif css_url.startswith('/'):
                    css_url = urllib.parse.urljoin(base_url, css_url)
                elif not css_url.startswith(('http://', 'https://')):
                    css_url = urllib.parse.urljoin(base_url, css_url)
                
                if css_url.startswith(('http://', 'https://')) and css_url not in downloaded_resources:
                    local_path = create_local_filename(css_url, resources_dir)
                    if download_resource(css_url, local_path, session):
                        relative_path = os.path.relpath(local_path, os.path.dirname(output_file))
                        # Ensure forward slashes for web compatibility
                        relative_path = relative_path.replace('\\', '/')
                        css_content = css_content.replace(css_url, relative_path)
                        downloaded_resources[css_url] = relative_path
                        time.sleep(0.1)
            
            # Write updated CSS back
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write(css_content)
                
        except Exception as e:
            print(f"    Error processing CSS file {css_file}: {e}")

    # Process inline CSS in <style> tags for embedded resources
    print(f"  Processing inline CSS for embedded resources...")
    for style_tag in soup.find_all('style'):
        if style_tag.string:
            css_content = style_tag.string
            
            # Find URLs in CSS (basic regex for url() functions)
            import re
            css_urls = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', css_content)
            
            for css_url in css_urls:
                original_css_url = css_url
                
                # Convert relative URLs to absolute
                if css_url.startswith('//'):
                    css_url = 'https:' + css_url
                elif css_url.startswith('/'):
                    css_url = urllib.parse.urljoin(base_url, css_url)
                elif not css_url.startswith(('http://', 'https://')):
                    css_url = urllib.parse.urljoin(base_url, css_url)
                
                if css_url.startswith(('http://', 'https://')) and css_url not in downloaded_resources:
                    local_path = create_local_filename(css_url, resources_dir)
                    if download_resource(css_url, local_path, session):
                        relative_path = os.path.relpath(local_path, os.path.dirname(output_file))
                        # Ensure forward slashes for web compatibility
                        relative_path = relative_path.replace('\\', '/')
                        css_content = css_content.replace(original_css_url, relative_path)
                        downloaded_resources[css_url] = relative_path
                        time.sleep(0.1)
            
            # Update the style tag content
            style_tag.string = css_content

    # Process inline style attributes for background images
    print(f"  Processing inline style attributes for background images...")
    for element in soup.find_all(attrs={"style": True}):
        style_content = element.get("style", "")
        if "url(" in style_content:
            # Find URLs in style attribute (basic regex for url() functions)
            import re
            css_urls = re.findall(r'url\(["\']?([^"\')\s]+)["\']?\)', style_content)
            
            for css_url in css_urls:
                original_css_url = css_url
                
                # Convert relative URLs to absolute
                if css_url.startswith('//'):
                    css_url = 'https:' + css_url
                elif css_url.startswith('/'):
                    css_url = urllib.parse.urljoin(base_url, css_url)
                elif not css_url.startswith(('http://', 'https://')):
                    css_url = urllib.parse.urljoin(base_url, css_url)
                
                # Check if we've already downloaded this resource
                if css_url in downloaded_resources:
                    style_content = style_content.replace(original_css_url, downloaded_resources[css_url])
                elif css_url.startswith(('http://', 'https://')):
                    local_path = create_local_filename(css_url, resources_dir)
                    if download_resource(css_url, local_path, session):
                        relative_path = os.path.relpath(local_path, os.path.dirname(output_file))
                        # Ensure forward slashes for web compatibility
                        relative_path = relative_path.replace('\\', '/')
                        style_content = style_content.replace(original_css_url, relative_path)
                        downloaded_resources[css_url] = relative_path
                        time.sleep(0.1)
            
            # Update the style attribute
            element["style"] = style_content

    # Remove all <script> tags (after downloading any external scripts)
    for script in soup.find_all("script"):
        script.decompose()

    # Replace all href attributes and remove ping attributes
    for link in soup.find_all("a", href=True):
        link["href"] = link_replacement
        # Remove ping attribute if it exists
        if link.has_attr("ping"):
            del link["ping"]

    # Write cleaned HTML back out
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    
    session.close()
    print(f"Completed processing {input_file}")
    print(f"  Downloaded {len(downloaded_resources)} resources")

# Process all files in the configuration
for file_config in files_to_process:
    try:
        process_html_file(
            file_config["input_filename"],
            file_config["output_filename"],
            file_config["link_replacement"],
            file_config["base_url"]
        )
    except FileNotFoundError:
        print(f"Warning: Input file '{file_config['input_filename']}' not found, skipping...")
    except Exception as e:
        print(f"Error processing {file_config['input_filename']}: {e}")

print("All files processed!")
