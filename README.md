# HTML Demoizer Script

A powerful Python script that processes HTML files to create self-contained, offline-ready demo versions by downloading all external resources and cleaning up unwanted elements.

## Features

- 🧹 **Script Removal**: Removes all `<script>` tags and JavaScript code
- 🔗 **Link Replacement**: Replaces all links with specified URLs  
- 📥 **Resource Download**: Downloads all external resources (images, CSS, fonts, etc.)
- 🎯 **Comprehensive Processing**: Handles images, CSS files, fonts, favicons, meta tags, inline styles, and more
- ⚙️ **Flexible Configuration**: Support for JSON config files or command line arguments
- 🛡️ **Error Handling**: Graceful handling of missing resources and network issues
- 🌐 **Cross-Platform**: Works on Windows, Mac, and Linux

## Installation

1. **Clone or download the script files**
2. **Install required dependencies**:
   ```bash
   pip install beautifulsoup4 requests
   ```

## Usage

### Method 1: JSON Configuration File (Recommended for multiple files)

1. **Create a configuration file** `demoizer_settings.json`:
   ```json
   [
        {
            "input_filename": "ORIGINAL_HTML.html",
            "output_filename": "STRIPPED_HTML.html",
            "link_replacement": "REPLACE_LINKS_WITH_THIS.html",
            "base_url": "original-site.com"
        },
        {
            "input_filename": "ORIGINAL_HTML_2.html",
            "output_filename": "STRIPPED_HTML_2.html",
            "link_replacement": "REPLACE_LINKS_WITH_THIS.html",
            "base_url": "original-site.com"
        }
    ]
   ```

2. **Run the script**:
   ```bash
   python demoizer.py
   ```

3. **Use a custom config file**:
   ```bash
   python demoizer.py --config my_custom_config.json
   ```

### Method 2: Command Line Arguments (Quick single file processing)

**Basic usage**:
```bash
python demoizer.py --input ORIGINAL_SITE.html --output PROCESSED_SITE.html
```

**With all options**:
```bash
python demoizer.py \
  --input ORIGINAL_SITE.html \
  --output PROCESSED_SITE.html \
  --link-replacement "REPLACE_LINK_WITH_THIS.html" \
  --base-url "https://www.original-site.com"
```

## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--config` | `-c` | JSON configuration file | `demoizer_settings.json` |
| `--input` | `-i` | Input HTML file to process | - |
| `--output` | `-o` | Output HTML file name | - |
| `--link-replacement` | `-l` | URL to replace all links with | `#` |
| `--base-url` | `-b` | Base URL for resolving relative URLs | `https://www.original-site.com` |

## Configuration File Format

The JSON configuration file should contain an array of objects, each with these properties:

- **`input_filename`**: Path to the source HTML file
- **`output_filename`**: Path for the processed HTML file
- **`link_replacement`**: URL to replace all links with
- **`base_url`**: Base URL for resolving relative resource URLs

## What the Script Does

### 1. 🧹 **Cleans HTML**
- Removes all `<script>` tags
- Removes `ping` attributes from links
- Replaces all `href` attributes with your specified URL

### 2. 📥 **Downloads Resources**
- **Images**: `<img src="">`, `<image src="">` (SVG)
- **Stylesheets**: `<link rel="stylesheet">`, `<link href="">`
- **Fonts**: Fonts and other web fonts
- **Icons**: Favicons and other icons
- **Meta Images**: Social media preview images
- **CSS Resources**: Images and fonts referenced in CSS files
- **Inline Styles**: Background images in `style` attributes

### 3. 🔄 **Updates References**
- Replaces all external URLs with local file paths
- Creates a `resources/` folder for downloaded files
- Ensures cross-platform compatibility with proper path separators

## Output Structure

After processing, you'll have:
```
your-folder/
├── Google.html              # Processed HTML file
├── SearchResults.html       # Processed HTML file  
├── resources/               # Downloaded resources
│   ├── image1_abc123.png
│   ├── font1_def456.woff2
│   ├── styles_ghi789.css
│   └── ...
└── demoizer_settings.json
```

## Examples

### Example 1: Create Offline Google Homepage
```bash
# Download Google homepage
curl "https://www.google.com" > GoogleRaw.html

# Process it
python demoizer.py --input GoogleRaw.html --output Google.html --link-replacement "offline.html"
```

### Example 2: Process Multiple Pages
Create `config.json`:
```json
[
    {
        "input_filename": "homepage.html",
        "output_filename": "homepage_clean.html", 
        "link_replacement": "contact.html",
        "base_url": "https://example.com"
    },
    {
        "input_filename": "about.html",
        "output_filename": "about_clean.html",
        "link_replacement": "contact.html", 
        "base_url": "https://example.com"
    }
]
```

Run: `python demoizer.py --config config.json`

## Troubleshooting

### Common Issues

**1. ModuleNotFoundError**
```bash
pip install beautifulsoup4 requests
```

**2. File not found errors**
- Ensure input HTML files exist in the current directory
- Check file paths in your configuration

**3. Download failures** 
- Some resources may be blocked or require authentication
- The script will continue processing other resources

**4. Permission errors**
- Ensure you have write permissions in the output directory

### Getting Help
```bash
python demoizer.py --help
```

## Requirements

- Python 3.6+
- beautifulsoup4
- requests

## License

This script is provided as-is for educational and personal use.

## Contributing

Feel free to submit issues and enhancement requests!
