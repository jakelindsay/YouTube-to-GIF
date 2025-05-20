# YouTube to GIF Generator with Meme Text

A Python-based web application that allows you to specify a link to a YouTube video, define a start and end time for a segment, and export it as a GIF. You can also overlay custom meme text onto the generated GIF.

## Features

*   Download a specific segment of a YouTube video.
*   Convert the video segment to an animated GIF.
*   Overlay custom text (meme text) onto the GIF at a specified start time.
*   Simple web interface for providing inputs and viewing/downloading the generated GIF.

## Requirements

*   Python 3.7+
*   `pip` (Python package installer)
*   `ffmpeg`: This application relies on `ffmpeg` for video processing tasks performed by `yt-dlp` and `MoviePy`. It **must** be installed on your system and accessible in the system's PATH.

## Setup and Installation

1.  **Clone the repository (Example):**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create and activate a virtual environment (Recommended):**
    ```bash
    python -m venv venv
    ```
    *   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        venv\Scripts\activate
        ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install `ffmpeg`:**
    *   **Linux (Debian/Ubuntu):** `sudo apt update && sudo apt install ffmpeg`
    *   **macOS (using Homebrew):** `brew install ffmpeg`
    *   **Windows:** Download binaries from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` directory to your system's PATH.
    *   Verify installation by typing `ffmpeg -version` in your terminal.

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Run the Flask application:
    ```bash
    python app.py
    ```
3.  Open your web browser and navigate to:
    [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## File Structure

```
.
├── app.py               # Main Flask application logic
├── gif_generator.py     # Core functions for video download, GIF conversion, and text overlay
├── requirements.txt     # Python package dependencies
├── static/
│   └── generated_gifs/  # Directory where generated GIFs are stored
├── templates/
│   ├── index.html       # Main page with the input form
│   └── results.html     # Page to display the generated GIF and download link
└── temp_videos/         # Temporary storage for downloaded video segments (cleaned up automatically)
```

## Troubleshooting

*   **`ffmpeg`/`ffprobe` not found errors:** This usually means `ffmpeg` is not installed correctly or its location is not in your system's PATH environment variable. Please verify your `ffmpeg` installation.
*   **Download errors:** Ensure the YouTube URL is correct, the video is public, and not region-restricted. Some very long videos or live streams might also cause issues.
*   **Permissions errors:** Ensure the application has write permissions for the `static/generated_gifs` and `temp_videos` directories. (This is usually not an issue with default Flask development server setups).
```
