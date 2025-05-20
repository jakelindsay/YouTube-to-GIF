import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add project root to sys.path to allow importing gif_generator
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from gif_generator import download_video_segment, convert_to_gif, add_text_overlay
from yt_dlp.utils import DownloadError # For testing exception handling
# from moviepy.editor import VideoClip # Base for mocking moviepy clips, not strictly needed if using MagicMock with spec
# For spec, we can use the actual classes if they are imported or use strings
# For simplicity, MagicMock without spec or with spec=True can also work well.
# Let's use spec with the actual classes for better type checking in mocks.
from moviepy.editor import VideoFileClip as MoviePyVideoFileClip, TextClip as MoviePyTextClip, CompositeVideoClip as MoviePyCompositeVideoClip


class TestGifGenerator(unittest.TestCase):

    def setUp(self):
        self.test_output_dir = 'test_temp_output_videos' # Renamed for clarity
        self.test_gif_output_dir = 'test_temp_output_gifs' # Renamed for clarity
        os.makedirs(self.test_output_dir, exist_ok=True)
        os.makedirs(self.test_gif_output_dir, exist_ok=True)

        # Keep track of files created by tests to clean them up
        self.created_files = []

    def tearDown(self):
        for f_path in self.created_files:
            if os.path.exists(f_path):
                os.remove(f_path)
        self.created_files = []

        if os.path.exists(self.test_output_dir):
            # Remove any stray files if tests didn't clean up properly
            for f in os.listdir(self.test_output_dir): os.remove(os.path.join(self.test_output_dir, f))
            os.rmdir(self.test_output_dir)
        if os.path.exists(self.test_gif_output_dir):
            for f in os.listdir(self.test_gif_output_dir): os.remove(os.path.join(self.test_gif_output_dir, f))
            os.rmdir(self.test_gif_output_dir)

    @patch('gif_generator.os.path.exists', return_value=True) # Assume downloaded file exists for find logic
    @patch('gif_generator.os.listdir')
    @patch('gif_generator.yt_dlp.YoutubeDL')
    @patch('gif_generator.os.makedirs') # Keep this to assert it's called for output_dir
    def test_download_video_segment_success(self, mock_os_makedirs_main, mock_youtube_dl, mock_os_listdir, mock_os_path_exists):
        mock_ydl_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_ydl_instance
        
        youtube_url = 'fake_url'
        start_time = 10
        end_time = 20
        
        # Simulate extract_info returning a dictionary that ydl.prepare_filename would use
        # The critical part is that after download, the file is found by os.listdir
        # and matches the naming pattern.
        mock_info_dict = {
            'id': 'test_id',
            'title': 'test_title',
            'ext': 'mp4', # Original extension
            # 'requested_downloads': [{'filepath': expected_filepath}] # Not used by current code
        }
        mock_ydl_instance.extract_info.return_value = mock_info_dict
        
        # This is what prepare_filename would roughly produce before post-processing changes ext to mp4
        # The code looks for files starting with this base and ending in .mp4
        # Example: 'test_temp_output_videos/test_id_test_title.mp4'
        expected_base_filename_part = f"{mock_info_dict['id']}_{mock_info_dict['title']}"
        expected_processed_filename = f"{expected_base_filename_part}.mp4" # After post-processing
        expected_filepath = os.path.join(self.test_output_dir, expected_processed_filename)

        # Mock os.listdir to return the processed file name
        mock_os_listdir.return_value = [expected_processed_filename]
        # Mock ydl.prepare_filename to assist the file search logic
        mock_ydl_instance.prepare_filename.return_value = os.path.join(self.test_output_dir, f"{expected_base_filename_part}.{mock_info_dict['ext']}")


        result_path = download_video_segment(youtube_url, start_time, end_time, output_dir=self.test_output_dir)

        mock_os_makedirs_main.assert_called_with(self.test_output_dir, exist_ok=True)
        mock_youtube_dl.assert_called_once() 
        
        args, kwargs = mock_youtube_dl.call_args
        ydl_opts = args[0]
        self.assertIn('postprocessor_args', ydl_opts)
        # Check for specific postprocessor arguments
        self.assertTrue(any(arg == str(start_time) for sublist in ydl_opts['postprocessor_args'] for arg in sublist if isinstance(sublist, list) and sublist[0] == '-ss'))
        self.assertTrue(any(arg == str(end_time) for sublist in ydl_opts['postprocessor_args'] for arg in sublist if isinstance(sublist, list) and sublist[0] == '-to'))
        self.assertIn(f'{self.test_output_dir}/%(id)s_%(title)s.%(ext)s', ydl_opts['outtmpl'])

        mock_ydl_instance.extract_info.assert_called_once_with(youtube_url, download=True)
        mock_os_listdir.assert_called_with(self.test_output_dir) # Verify it lists the correct directory
        self.assertEqual(result_path, expected_filepath)


    @patch('gif_generator.yt_dlp.YoutubeDL')
    @patch('gif_generator.os.makedirs')
    def test_download_video_segment_download_error(self, mock_os_makedirs, mock_youtube_dl):
        mock_ydl_instance = MagicMock()
        mock_youtube_dl.return_value.__enter__.return_value = mock_ydl_instance
        # Simulate DownloadError during the extract_info (which also handles download)
        mock_ydl_instance.extract_info.side_effect = DownloadError("Test download error", "ExtractorError")

        with self.assertRaises(DownloadError):
            download_video_segment('fake_url', 0, 10, output_dir=self.test_output_dir)
        
        mock_os_makedirs.assert_called_with(self.test_output_dir, exist_ok=True)


    @patch('gif_generator.os.path.exists', return_value=True) # To pass the initial video_path check
    @patch('gif_generator.VideoFileClip') # Target where it's used
    @patch('gif_generator.os.makedirs') # To check for output dir creation
    def test_convert_to_gif_success(self, mock_os_makedirs_gif, mock_video_file_clip_constructor, mock_path_exists):
        # Corrected: VideoFileClip is not a context manager in gif_generator.py
        mock_clip_instance = MagicMock(spec=MoviePyVideoFileClip) 
        mock_clip_instance.duration = 5 
        mock_clip_instance.fps = 30 
        mock_video_file_clip_constructor.return_value = mock_clip_instance

        video_path = os.path.join(self.test_output_dir, "dummy_video.mp4") # Use a path within test_output_dir
        # self.created_files.append(video_path) # Not actually creating, just path
        gif_path = os.path.join(self.test_gif_output_dir, "output.gif")
        fps = 15

        # Simulate video_path exists
        # mock_path_exists.return_value = True # Done by patch decorator

        result_path = convert_to_gif(video_path, gif_path, fps=fps)

        mock_path_exists.assert_called_with(video_path) # Check existence check
        mock_os_makedirs_gif.assert_any_call(os.path.dirname(gif_path), exist_ok=True) # gif_generator creates this
        
        mock_video_file_clip_constructor.assert_called_with(video_path)
        mock_clip_instance.write_gif.assert_called_with(gif_path, fps=fps) # logger removed as moviepy changed defaults
        mock_clip_instance.close.assert_called_once() # Ensure clip is closed
        self.assertEqual(result_path, gif_path)

    @patch('gif_generator.os.path.exists', return_value=True)
    @patch('gif_generator.CompositeVideoClip') # Target CompositeVideoClip where it's used
    @patch('gif_generator.TextClip')      # Target TextClip where it's used
    @patch('gif_generator.VideoFileClip') # Target VideoFileClip where it's used
    @patch('gif_generator.os.makedirs')
    def test_add_text_overlay_success(self, mock_os_makedirs_overlay, mock_video_file_clip_constructor, 
                                    mock_text_clip_constructor, mock_composite_video_clip_constructor, mock_path_exists_overlay):
        
        mock_input_gif_clip = MagicMock(spec=MoviePyVideoFileClip)
        mock_input_gif_clip.duration = 10.0
        mock_input_gif_clip.fps = 10
        mock_video_file_clip_constructor.return_value = mock_input_gif_clip # Corrected: not a context manager

        mock_text_clip_instance = MagicMock(spec=MoviePyTextClip)
        # Simulate chaining of set_ methods by returning the mock_text_clip_instance itself
        mock_text_clip_instance.set_position.return_value = mock_text_clip_instance
        mock_text_clip_instance.set_start.return_value = mock_text_clip_instance
        mock_text_clip_instance.set_duration.return_value = mock_text_clip_instance
        mock_text_clip_constructor.return_value = mock_text_clip_instance

        mock_final_composite_clip = MagicMock(spec=MoviePyCompositeVideoClip)
        mock_composite_video_clip_constructor.return_value = mock_final_composite_clip
        
        input_gif_path = os.path.join(self.test_gif_output_dir, "input.gif")
        output_gif_path = os.path.join(self.test_gif_output_dir, "output_with_text.gif")
        text = "HELLO"
        text_start_time = 1.0
        duration_on_screen = 5.0
        font_size = 30
        font_color = 'black'
        position = ('center', 'top')
        font = 'Arial' # Default font in gif_generator

        # mock_path_exists_overlay.return_value = True # Done by patch decorator

        result = add_text_overlay(input_gif_path, output_gif_path, text, text_start_time,
                                  duration_on_screen=duration_on_screen, font_size=font_size,
                                  font_color=font_color, position=position, font=font)

        mock_path_exists_overlay.assert_called_with(input_gif_path)
        mock_os_makedirs_overlay.assert_any_call(os.path.dirname(output_gif_path), exist_ok=True)

        mock_video_file_clip_constructor.assert_called_with(input_gif_path)
        mock_text_clip_constructor.assert_called_with(text, fontsize=font_size, color=font_color, font=font)
        
        mock_text_clip_instance.set_position.assert_called_with(position)
        mock_text_clip_instance.set_start.assert_called_with(text_start_time)
        mock_text_clip_instance.set_duration.assert_called_with(duration_on_screen)
        
        mock_composite_video_clip_constructor.assert_called_with([mock_input_gif_clip, mock_text_clip_instance])
        mock_final_composite_clip.write_gif.assert_called_with(output_gif_path, fps=mock_input_gif_clip.fps)
        
        # Assert all clips are closed
        mock_input_gif_clip.close.assert_called_once()
        mock_text_clip_instance.close.assert_called_once() # TextClip also needs close if it holds resources
        mock_final_composite_clip.close.assert_called_once()

        self.assertEqual(result, output_gif_path)

    @patch('gif_generator.os.path.exists', return_value=True)
    @patch('gif_generator.CompositeVideoClip')
    @patch('gif_generator.TextClip')
    @patch('gif_generator.VideoFileClip')
    @patch('gif_generator.os.makedirs')
    def test_add_text_overlay_text_until_end(self, mock_os_makedirs_overlay_end, mock_video_file_clip_constructor_end, 
                                           mock_text_clip_constructor_end, mock_composite_video_clip_constructor_end, mock_path_exists_overlay_end):
        mock_input_gif_clip = MagicMock(spec=MoviePyVideoFileClip)
        mock_input_gif_clip.duration = 8.0
        mock_input_gif_clip.fps = 12
        mock_video_file_clip_constructor_end.return_value = mock_input_gif_clip

        mock_text_clip_instance = MagicMock(spec=MoviePyTextClip)
        mock_text_clip_instance.set_position.return_value = mock_text_clip_instance
        mock_text_clip_instance.set_start.return_value = mock_text_clip_instance
        mock_text_clip_instance.set_duration.return_value = mock_text_clip_instance
        mock_text_clip_constructor_end.return_value = mock_text_clip_instance
        
        mock_final_composite_clip = MagicMock(spec=MoviePyCompositeVideoClip)
        mock_composite_video_clip_constructor_end.return_value = mock_final_composite_clip

        input_gif_path = os.path.join(self.test_gif_output_dir, "input_end.gif")
        output_gif_path = os.path.join(self.test_gif_output_dir, "output_text_end.gif")
        text = "UNTIL END"
        text_start_time = 2.0
        
        expected_text_duration = mock_input_gif_clip.duration - text_start_time

        # mock_path_exists_overlay_end.return_value = True # Handled by decorator

        result = add_text_overlay(input_gif_path, output_gif_path, text, text_start_time, duration_on_screen=-1)

        mock_text_clip_instance.set_duration.assert_called_with(expected_text_duration)
        mock_final_composite_clip.write_gif.assert_called_with(output_gif_path, fps=mock_input_gif_clip.fps)
        self.assertEqual(result, output_gif_path)

if __name__ == '__main__':
    # This allows running the tests directly from this file
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
```
