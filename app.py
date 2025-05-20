import os
import uuid
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
from gif_generator import download_video_segment, convert_to_gif, add_text_overlay
from yt_dlp import DownloadError # Import DownloadError to catch it specifically if needed

app = Flask(__name__)
app.secret_key = os.urandom(24) # For flashing messages

# Configuration for temporary and output folders
TEMP_VIDEO_FOLDER = 'temp_videos'
GENERATED_GIF_FOLDER = 'static/generated_gifs' # static is conventional for Flask
app.config['TEMP_VIDEO_FOLDER'] = TEMP_VIDEO_FOLDER
app.config['GENERATED_GIF_FOLDER'] = GENERATED_GIF_FOLDER

# Ensure directories exist
os.makedirs(TEMP_VIDEO_FOLDER, exist_ok=True)
os.makedirs(GENERATED_GIF_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_gif():
    video_path = None 
    temp_gif_path = None

    try:
        youtube_url = request.form['youtube_url']
        meme_text = request.form['meme_text']

        # Validate and convert time inputs
        try:
            video_start_time = int(request.form['video_start_time'])
            video_end_time = int(request.form['video_end_time'])
            text_start_time = float(request.form['text_start_time'])
        except ValueError:
            flash('Invalid input for time fields. Please use numbers only (e.g., 10, 20.5).', 'error')
            return redirect(url_for('index'))

        if not youtube_url:
            flash('YouTube URL is required.', 'error')
            return redirect(url_for('index'))
        if video_start_time >= video_end_time:
            flash('Video start time must be less than end time.', 'error')
            return redirect(url_for('index'))
        if video_start_time < 0:
            flash('Video start time cannot be negative.', 'error')
            return redirect(url_for('index'))
        if text_start_time < 0:
            flash('Text overlay start time cannot be negative.', 'error')
            return redirect(url_for('index'))


        unique_id = uuid.uuid4().hex
        
        # Call to download_video_segment
        video_path = download_video_segment(youtube_url, video_start_time, video_end_time, output_dir=app.config['TEMP_VIDEO_FOLDER'])
        
        if not video_path or not os.path.exists(video_path):
             flash(f'Failed to download video segment. Check URL and times. The video might be too long, private, or unavailable.', 'error')
             return redirect(url_for('index'))

        # Define GIF paths
        base_gif_filename = f"{unique_id}_temp.gif"
        final_gif_filename = f"{unique_id}.gif"
        temp_gif_path = os.path.join(app.config['GENERATED_GIF_FOLDER'], base_gif_filename)
        final_gif_path = os.path.join(app.config['GENERATED_GIF_FOLDER'], final_gif_filename)
        
        # Call to convert_to_gif
        convert_to_gif(video_path, temp_gif_path) 

        if not os.path.exists(temp_gif_path):
            flash('Failed to convert video to GIF. The video segment might be too short or corrupted.', 'error')
            if os.path.exists(video_path): 
                 os.remove(video_path)
            return redirect(url_for('index'))
            
        # Call to add_text_overlay
        add_text_overlay(temp_gif_path, final_gif_path, meme_text, text_start_time)
        
        if not os.path.exists(final_gif_path):
            flash('Failed to add text overlay to GIF.', 'error')
            if os.path.exists(video_path): os.remove(video_path)
            if os.path.exists(temp_gif_path): os.remove(temp_gif_path)
            return redirect(url_for('index'))

        # Successful generation, clean up intermediate files
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(temp_gif_path) and temp_gif_path != final_gif_path : 
             os.remove(temp_gif_path)

        return redirect(url_for('show_result', filename=final_gif_filename))

    except DownloadError as e: # Specific handling for yt-dlp download errors
        flash(f'Error downloading video: {str(e)}. Please check the URL and ensure the video is public and accessible.', 'error')
        # Cleanup based on which files might exist
        if video_path and os.path.exists(video_path): os.remove(video_path)
        if temp_gif_path and os.path.exists(temp_gif_path): os.remove(temp_gif_path)
        return redirect(url_for('index'))
    except FileNotFoundError as e: # Specific handling for file not found errors from gif_generator
        flash(f'A required file was not found: {str(e)}', 'error')
        if video_path and os.path.exists(video_path): os.remove(video_path)
        if temp_gif_path and os.path.exists(temp_gif_path): os.remove(temp_gif_path)
        return redirect(url_for('index'))
    except Exception as e: # General error handler
        flash(f'An unexpected error occurred: {str(e)}', 'error')
        if video_path and os.path.exists(video_path): os.remove(video_path)
        if temp_gif_path and os.path.exists(temp_gif_path): os.remove(temp_gif_path)
        return redirect(url_for('index'))

@app.route('/results/<filename>')
def show_result(filename):
    if '..' in filename or filename.startswith('/'): 
        flash('Invalid filename.', 'error')
        return redirect(url_for('index'))
    gif_url = url_for('static', filename=f'generated_gifs/{filename}')
    return render_template('results.html', gif_url=gif_url, filename=filename)

@app.route('/download/<filename>')
def download_gif(filename):
    if '..' in filename or filename.startswith('/'): 
        flash('Invalid filename.', 'error')
        return redirect(url_for('index'))
    return send_from_directory(app.config['GENERATED_GIF_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
