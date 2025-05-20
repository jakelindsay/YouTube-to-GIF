import os
import yt_dlp
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from yt_dlp import DownloadError

def download_video_segment(youtube_url: str, start_time: int, end_time: int, output_dir: str = 'temp_videos') -> str:
    """
    Downloads a segment of a YouTube video.
    """
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': f'{output_dir}/%(id)s_%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio', # Placeholder, actual cutting is done by postprocessor_args
            'preferredcodec': 'aac', # Placeholder
        }],
        'postprocessor_args': [
            '-ss', str(start_time),
            '-to', str(end_time),
            '-c:v', 'libx264', '-c:a', 'aac', # Re-encode
            '-avoid_negative_ts', 'make_zero', # Avoid issues with negative timestamps
        ],
        # 'ffmpeg_location': '/path/to/ffmpeg', # Optional: specify if not in PATH
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
            # Construct the filename based on outtmpl and info_dict
            # yt-dlp replaces special characters in title, so we rely on its generated filename
            # The actual filename is available after download in info_dict['_filename'] if using generic extractor
            # or more reliably by listing the directory if only one file is expected.
            # For simplicity, we'll assume the postprocessor_args correctly name and place the file.
            
            # After processing, yt-dlp might change the extension or filename slightly.
            # We need to find the actual file created.
            # A common pattern is that the original extension might be kept before processing,
            # and then a new file with .mp4 is created.
            
            # Simplest approach: find the first .mp4 file in the output_dir
            # This assumes only one video is processed at a time in this directory by this function.
            downloaded_files = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
            if not downloaded_files:
                # Fallback if no mp4, maybe original extension was kept
                 downloaded_files = [f for f in os.listdir(output_dir) if ydl.prepare_filename(info_dict).startswith(os.path.join(output_dir, os.path.splitext(f)[0]))]

            if downloaded_files:
                # Assuming the first match is our processed file
                # If multiple files, this might pick the wrong one.
                # A more robust way would be to get the exact output filename from ydl_opts['outtmpl']
                # and info_dict, then expect that name.
                
                # yt-dlp's prepare_filename can give the expected name BEFORE postprocessing.
                # The postprocessor might change it.
                # Let's try to guess the filename based on the template
                base_name_template = ydl.prepare_filename(info_dict).rsplit('.', 1)[0]
                
                # Search for files that start with the base name and end with .mp4
                possible_files = [f for f in os.listdir(output_dir) if f.startswith(os.path.basename(base_name_template)) and f.endswith('.mp4')]

                if not possible_files: # if no such file, maybe the original extension was kept by postprocessing
                    original_ext = ydl.prepare_filename(info_dict).rsplit('.', 1)[-1]
                    possible_files = [f for f in os.listdir(output_dir) if f.startswith(os.path.basename(base_name_template)) and f.endswith(f'.{original_ext}')]


                if possible_files:
                    # To be safer, sort by modification time if multiple matches, take newest.
                    # For now, just take the first one.
                    processed_filename = possible_files[0]
                    return os.path.join(output_dir, processed_filename)
                else:
                    # If still no file, this is an issue.
                    raise FileNotFoundError(f"Could not find processed video file in {output_dir} for {youtube_url}")

            else:
                raise FileNotFoundError(f"No video file found in {output_dir} after download attempt for {youtube_url}")

    except DownloadError as e:
        print(f"Error downloading video: {e}")
        # Consider re-raising or returning a specific error code/value
        raise  # Re-raise the exception for the caller to handle
    except Exception as e:
        print(f"An unexpected error occurred during download: {e}")
        raise

def convert_to_gif(video_path: str, gif_path: str, fps: int = 10) -> str:
    """
    Converts a video file to a GIF.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    output_gif_dir = os.path.dirname(gif_path)
    if output_gif_dir: # Ensure directory exists if gif_path includes a directory
        os.makedirs(output_gif_dir, exist_ok=True)

    try:
        clip = VideoFileClip(video_path)
        clip.write_gif(gif_path, fps=fps)
        clip.close() # Release resources
        return gif_path
    except Exception as e:
        print(f"Error converting video to GIF: {e}")
        # Clean up partial GIF if created? MoviePy might handle this.
        if os.path.exists(gif_path):
            # Potentially remove corrupted/partial gif
            # os.remove(gif_path) # Or leave it for inspection
            pass
        raise

def add_text_overlay(input_gif_path: str, output_gif_path: str, text: str,
                     text_start_time: float, duration_on_screen: float = -1,
                     font_size: int = 24, font_color: str = 'white',
                     position: tuple = ('center', 'bottom'), font: str = 'Arial') -> str:
    """
    Adds text overlay to an existing GIF.
    """
    if not os.path.exists(input_gif_path):
        raise FileNotFoundError(f"Input GIF not found: {input_gif_path}")

    output_gif_dir = os.path.dirname(output_gif_path)
    if output_gif_dir: # Ensure directory exists
        os.makedirs(output_gif_dir, exist_ok=True)

    try:
        gif_clip = VideoFileClip(input_gif_path)

        # Ensure text_start_time is within bounds
        if text_start_time < 0:
            text_start_time = 0
        elif text_start_time > gif_clip.duration:
            text_start_time = gif_clip.duration
            print(f"Warning: Text start time ({text_start_time}s) exceeds GIF duration ({gif_clip.duration}s). Text may not be visible.")


        if duration_on_screen == -1 or (text_start_time + duration_on_screen > gif_clip.duration):
            text_duration = gif_clip.duration - text_start_time
        else:
            text_duration = duration_on_screen
        
        if text_duration <= 0:
            print(f"Warning: Calculated text duration is {text_duration}s. Text will not be visible. GIF duration: {gif_clip.duration}, start_time: {text_start_time}")
            # If duration is zero or negative, just copy the original gif or return error
            # For now, let it proceed, moviepy might handle it or create a very short/no text.
            # A better approach might be to not add text if duration is <=0
            if text_duration <=0 and gif_clip.duration > 0 : # only write if there is something to write
                 gif_clip.write_gif(output_gif_path, fps=gif_clip.fps or 10) # use original fps or default
                 gif_clip.close()
                 return output_gif_path


        txt_clip = TextClip(text, fontsize=font_size, color=font_color, font=font)
        txt_clip = txt_clip.set_position(position).set_start(text_start_time).set_duration(text_duration)

        # CompositeVideoClip needs a list of clips, with the base clip first
        final_clip = CompositeVideoClip([gif_clip, txt_clip])
        
        # Use original GIF's fps, or a default if not available (e.g., 10 fps)
        output_fps = gif_clip.fps
        if not output_fps or output_fps <= 0:
            print(f"Warning: Input GIF FPS is invalid ({gif_clip.fps}). Using default FPS of 10.")
            output_fps = 10
            
        final_clip.write_gif(output_gif_path, fps=output_fps)
        
        gif_clip.close()
        txt_clip.close()
        final_clip.close()
        
        return output_gif_path
    except Exception as e:
        print(f"Error adding text to GIF: {e}")
        if os.path.exists(output_gif_path):
            # os.remove(output_gif_path) # Optional: remove partial/corrupted output
            pass
        # Ensure clips are closed if an error occurs mid-process
        if 'gif_clip' in locals() and gif_clip: gif_clip.close()
        if 'txt_clip' in locals() and txt_clip: txt_clip.close()
        if 'final_clip' in locals() and final_clip: final_clip.close()
        raise

# Example Usage (optional, for testing)
if __name__ == '__main__':
    # This block will only run if the script is executed directly
    # You'll need a YouTube link and ffmpeg installed to test download_video_segment
    # And a video file to test convert_to_gif

    # --- Test download_video_segment ---
    # test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Example: Rick Astley
    # print(f"Attempting to download segment from {test_url}...")
    # try:
    #     # Ensure ffmpeg is in PATH or specify 'ffmpeg_location' in ydl_opts if testing locally
    #     video_file = download_video_segment(test_url, start_time=10, end_time=15, output_dir='temp_downloaded_videos')
    #     print(f"Video segment downloaded to: {video_file}")
    #
    #     # --- Test convert_to_gif ---
    #     if video_file and os.path.exists(video_file):
    #         print(f"Attempting to convert {video_file} to GIF...")
    #         gif_output_path = os.path.join('temp_gifs', os.path.basename(video_file).replace('.mp4', '.gif'))
    #         converted_gif = convert_to_gif(video_file, gif_output_path, fps=15)
    #         print(f"Video converted to GIF: {converted_gif}")
    #
    #         # --- Test add_text_overlay ---
    #         if converted_gif and os.path.exists(converted_gif):
    #             print(f"Attempting to add text to {converted_gif}...")
    #             text_gif_output_path = os.path.join('temp_gifs_with_text', os.path.basename(converted_gif).replace('.gif', '_text.gif'))
    #             final_gif = add_text_overlay(
    #                 converted_gif,
    #                 text_gif_output_path,
    #                 text="Hello from MoviePy!",
    #                 text_start_time=0.5, # Start text 0.5s into the GIF
    #                 duration_on_screen=3, # Show text for 3 seconds
    #                 font_size=30,
    #                 font_color='yellow',
    #                 position=('center', 'center')
    #             )
    #             print(f"GIF with text created: {final_gif}")
    #         else:
    #             print("Skipping text overlay test as GIF conversion failed or produced no file.")
    #     else:
    #         print("Skipping GIF conversion test as video download failed or produced no file.")
    #
    # except Exception as e:
    #     print(f"An error occurred during the test run: {e}")
    # finally:
    #     # Clean up test files (optional)
    #     # import shutil
    #     # if os.path.exists('temp_downloaded_videos'): shutil.rmtree('temp_downloaded_videos')
    #     # if os.path.exists('temp_gifs'): shutil.rmtree('temp_gifs')
    #     # if os.path.exists('temp_gifs_with_text'): shutil.rmtree('temp_gifs_with_text')
    #     pass
    pass
