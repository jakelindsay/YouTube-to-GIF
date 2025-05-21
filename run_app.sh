#!/bin/bash
# Ensure the script exits on error
set -e

echo "--- Running run_app.sh ---"

# Activate the virtual environment
if [ -f /opt/venv/bin/activate ]; then
  echo "Activating virtual environment from /opt/venv/bin/activate..."
  source /opt/venv/bin/activate
  echo "Virtual environment activated."
else
  echo "Error: Virtual environment activation script not found at /opt/venv/bin/activate"
  exit 1
fi

# Verify python executable and moviepy installation for debugging
echo "Python executable path: $(which python)"
echo "Current PYTHONPATH: '$PYTHONPATH'" # Quoted to see if it's empty

echo "Attempting to import moviepy and moviepy.editor using system call to python:"
python -c "import sys; print(f'Python version: {sys.version}'); print(f'sys.path: {sys.path}'); import moviepy; print(f'moviepy module found at: {moviepy.__file__}'); import moviepy.editor; print('moviepy.editor module imported successfully')"

if [ $? -ne 0 ]; then
  echo "Error: Python script failed to import moviepy.editor. See output above."
  # Attempt to list site-packages content for further diagnosis
  # Assuming Python 3.12 based on previous findings for the site-packages path
  SITE_PACKAGES_MOVIEPY_PATH="/opt/venv/lib/python3.12/site-packages/moviepy"
  SITE_PACKAGES_BASE_PATH="/opt/venv/lib/python3.12/site-packages"

  echo "Checking for existence of $SITE_PACKAGES_BASE_PATH..."
  if [ -d "$SITE_PACKAGES_BASE_PATH" ]; then
    echo "$SITE_PACKAGES_BASE_PATH exists."
    echo "Checking for existence of $SITE_PACKAGES_MOVIEPY_PATH..."
    if [ -d "$SITE_PACKAGES_MOVIEPY_PATH" ]; then
      echo "$SITE_PACKAGES_MOVIEPY_PATH exists. Listing contents:"
      ls -lA "$SITE_PACKAGES_MOVIEPY_PATH"/
    else
      echo "Directory $SITE_PACKAGES_MOVIEPY_PATH does NOT exist."
      echo "Listing contents of $SITE_PACKAGES_BASE_PATH to see if moviepy is present but named differently..."
      ls -lA "$SITE_PACKAGES_BASE_PATH"/
    fi
  else
    echo "Directory $SITE_PACKAGES_BASE_PATH does NOT exist."
    echo "Listing contents of /opt/venv/lib/ to see available python version directories..."
    ls -lA /opt/venv/lib/
  fi
  exit 1 # Exit if the import test fails
fi

# Execute the Flask application
echo "Starting Flask application (app.py)..."
exec python app.py
