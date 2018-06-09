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
