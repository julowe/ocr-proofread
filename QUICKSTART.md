# Quick Start Guide

## Installation

### Option 1: Docker (Recommended for Web App)

**Prerequisites:**
- Docker (version 20.10+)
- Docker Compose (version 1.29+)

**Steps:**

```bash
# Method 1: Use pre-built image (fastest)
docker run -d -p 5000:5000 --name ocr-proofread ghcr.io/julowe/ocr-proofread:latest

# Method 2: Use Docker Compose with pre-built image
docker-compose -f docker-compose.prebuilt.yml up -d

# Method 3: Build from source
git clone https://github.com/julowe/ocr-proofread.git
cd ocr-proofread
docker-compose up -d

# Access the application
# Open your browser to: http://localhost:5000
```

**Note:** Pre-built images are automatically published to GitHub Container Registry when code is merged to the main branch. They support both AMD64 and ARM64 architectures.

**Docker Commands:**

```bash
# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Restart after config changes
docker-compose restart
```

### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/julowe/ocr-proofread.git
cd ocr-proofread

# Install dependencies
pip install -r requirements.txt
```

### Option 3: Install as Package

```bash
# Install in development mode
pip install -e .

# Or install normally
pip install .
```

## Running the Application

### Web Application

**Option 1: Using Docker (Recommended)**

```bash
# Start the application
docker-compose up -d

# Access at http://localhost:5000
```

**Option 2: From source**

```bash
python3 run_web.py
```

**Option 3: After installation**

```bash
ocr-proofread-web
```

Then open your browser to: http://127.0.0.1:5000

### Desktop Application

**From source:**
```bash
python3 run_desktop.py
```

**After installation:**
```bash
ocr-proofread-desktop
```

## First Time Use

### 1. Prepare Your Files

Organize your images and hOCR files in one of two ways:

**Flat Directory:**
```
my-files/
  ├── page001.jpg
  ├── page001.hocr
  ├── page002.jpg
  └── page002.hocr
```

**Batch Subdirectories:**
```
my-batches/
  ├── batch001/
  │   ├── scan.jpg
  │   └── ocr.hocr
  └── batch002/
      ├── scan.jpg
      └── ocr.hocr
```

### 2. Load Files

**Web App:**
- Click "Select Files" or drag and drop your directory
- Click "Upload and Start Proofreading"

**Desktop App:**
- Click "Load Files"
- Select your directory
- Wait for validation to complete

### 3. Proofread

1. **Navigate**: Use arrow buttons to move between pages and words
2. **Select**: Click on yellow/green boxes in the image to select words
3. **Edit**: Choose from detected text versions or type custom text
4. **Save**: Export individual pages or all changes

### 4. Export

**Save Current Page**: Exports just the active page with your changes

**Save All Changed**: Creates individual files for all modified pages

**Export Merged**: Combines all pages into one hOCR file

## Tips

- **Green boxes** = Text matches across all OCR files
- **Yellow boxes** = Text differs between OCR sources
- Enable **"Skip matching words"** to focus on discrepancies
- Use **keyboard navigation** for faster proofreading
- Check the **log panel** for validation warnings

## Sample Data

Try the application with included sample data:
```bash
# From the repository root
python3 run_desktop.py
# Then load: tests/sample-data/life-of/
```

## Troubleshooting

### Dependencies Not Installing

```bash
# Update pip first
pip install --upgrade pip

# Try installing dependencies one at a time
pip install Flask Pillow lxml PyYAML PyQt6
```

### PyQt6 Issues

On Linux, you may need system packages:
```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt6

# Or use pip with system packages
pip install PyQt6 --user
```

### Web App Not Starting

Check if port 5000 is already in use:
```bash
# Find what's using port 5000
lsof -i :5000

# Or use a different port
python3 -c "from ocr_proofread.web.app import run_web_app; run_web_app(port=5001)"
```

### JP2 Images Not Loading

Install OpenJPEG library:
```bash
# Ubuntu/Debian
sudo apt-get install libopenjp2-7

# macOS
brew install openjpeg

# Then install glymur
pip install glymur
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the configuration file: `config.yaml`
- Check out the sample data in `tests/sample-data/`
- Build desktop executables with `build_desktop.sh` or `build_desktop.bat`

## Need Help?

- Check the [README.md](README.md) for detailed information
- Review validation messages in the log panel
- Look for error messages in the terminal/console
- File an issue on GitHub for bugs or feature requests
