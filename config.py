import os

S3_LOCATION = 'http://your-amazon-site.amazonaws.com/'
S3_KEY = os.environ.get('AWS_SERVER_PUBLIC_KEY')
S3_SECRET = os.environ.get('AWS_SERVER_SECRET_KEY')
S3_UPLOAD_DIRECTORY = 'myimages'
S3_AUDIO_UPLOAD_DIRECTORY = 'myaudio'
S3_BUCKET = 'hiphy'

SECRET_KEY = "FLASK_SECRET_KEY"
DEBUG = True
PORT = 5000
DROPZONE_ALLOWED_FILE_TYPE = 'image, audio'
# DROPZONE_MAX_FILE_SIZE = 3
DROPZONE_MAX_FILES = 30
DROPZONE_ENABLE_CSRF = True  # enable CSRF protection
DROPZONE_PARALLEL_UPLOADS = 30  # set parallel amount
DROPZONE_UPLOAD_MULTIPLE = True  # enable upload multiple
