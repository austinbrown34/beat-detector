from flask import Flask, jsonify, make_response, request, abort, Response, render_template, flash, redirect, url_for, send_from_directory
from flask_wtf import FlaskForm
from werkzeug import secure_filename
from flask_wtf.file import FileField
from flask_wtf.csrf import CSRFProtect, CSRFError
from tools import s3_uploads, s3_upload
import json
import os
import subprocess
import random
from aubio import source, tempo, onset
from numpy import median, diff
from pydub import AudioSegment
import boto3
import botocore
import requests
from uuid import uuid4
from flask_dropzone import Dropzone


app = Flask(__name__)
app.config.from_object('config')
dropzone = Dropzone(app)
csrf = CSRFProtect(app)

win_s = 512                 # fft size
hop_s = win_s // 2          # hop size

images_url = 'https://s3.amazonaws.com/hiphy/images/'
song_url = 'https://s3.amazonaws.com/hiphy/song/jason.wav'
ffmpeg_url = 'https://fe13pn0b30.execute-api.us-west-2.amazonaws.com/dev/v1/convert'
# ffmpeg_url = 'http://7f5fd0b2.ngrok.io/v1/convert'

session = boto3.Session(
    aws_access_key_id=os.environ.get('AWS_SERVER_PUBLIC_KEY'),
    aws_secret_access_key=os.environ.get('AWS_SERVER_SECRET_KEY'),
)
s3 = session.resource('s3')


def download_song(song_url):
    # download song
    bucket = song_url.split('.com/')[1].split('/')[0]
    song = song_url.split('.com/{}/'.format(bucket))[1]
    file_name = song_url.split('/')[-1]
    try:
        try:
            os.remove('song.wav')
        except OSError:
            pass
        s3.Bucket(bucket).download_file(song, file_name)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
    if not file_name.endswith('.wav'):
        new_file_name = file_name.split('.')[0] + '.wav'
        args = [
            'ffmpeg',
            '-i',
            file_name,
            new_file_name
        ]
        subprocess.call(args)
        file_name = new_file_name
    return file_name


def get_images(images_url):
    # return list of image file names
    bucket = images_url.split('.com/')[1].split('/')[0]
    dist = images_url.split('.com/{}/'.format(bucket))[1]
    images = []
    my_bucket = s3.Bucket(bucket)
    print(bucket)
    print(dist)
    for object_summary in my_bucket.objects.filter(Prefix="{}".format(dist)):
        print(object_summary)
        images.append(object_summary.key)
    return images


def create_instructions(beats, images_url):
    images = get_images(images_url)
    instructions = []
    print(images)
    images = [
        i for i in images if i.endswith('.jpg') or i.endswith('.png')
    ]
    random.shuffle(images)

    before = float(0.000)
    j = 0
    for i, e in enumerate(beats):
        if j >= len(images):
            j = 0
        duration = float(float(e) - before)
        duration = "{0:.2f}".format(duration)
        before = float(e)
        image = images[j]
        if '/' in image:
            image = image.split('/')[-1]
        instructions.append('file {}'.format(image))
        instructions.append('duration {}'.format(duration))
        j = j + 1
    return instructions


def send_to_ffmpeg(images_url, song_url, instructions, email):

    values = {
        "images_s3_url": images_url,
        "song_s3_url": song_url,
        "instructions": instructions,
        "email": email
    }

    requests.post(ffmpeg_url, json=values)


def get_beats(path, params=None):
    """ Calculate the beats per minute (bpm) of a given file.
        path: path to the file
        param: dictionary of parameters
    """
    if params is None:
        params = {}
    samplerate, win_s, hop_s = 44100, 1024, 512
    if 'mode' in params:
        if params.mode in ['super-fast']:
            samplerate, win_s, hop_s = 4000, 128, 64
        elif params.mode in ['fast']:
            samplerate, win_s, hop_s = 8000, 512, 128
        elif params.mode in ['default']:
            pass
        else:
            print("unknown mode")
    if 'samplerate' in params:
        samplerate = params.samplerate
    if 'win_s' in params:
        win_s = params.win_s
    if 'hop_s' in params:
        hop_s = params.hop_s
    s = source(path, samplerate, hop_s)
    samplerate = s.samplerate
    hop_s = int(win_s // 1.001)
    ns = source(path, samplerate, hop_s)
    nsamplerate = ns.samplerate
    o = onset("default", win_s, hop_s, nsamplerate)
    beats = []
    total_frames = 0

    while True:
        nsamples, nread = ns()
        is_beat = o(nsamples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
        total_frames += nread
        if nread < hop_s:
            break
    return beats


def build_response(resp_dict, status_code):
    response = Response(json.dumps(resp_dict), status_code)
    return response


class UploadForm(FlaskForm):
    print("upload form")
    audio = FileField(
        'Example File',)
    example = FileField(
        'Example File',
        render_kw={'multiple': True},
        )


@app.errorhandler(CSRFError)
def csrf_error(e):
    return e.description, 400


@app.route('/', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        hex = uuid4().hex
        # print (request.files)
        # print (request.files.getlist('file'))
        email = request.form['email']
        print ('email:')
        print (email)
        images = []
        for key, f in request.files.items():
            if key.startswith('file'):
                print (f.filename)
                if f.filename.endswith('.wav') or f.filename.endswith('.mp3'):
                    out = s3_upload(f, '{}/{}'.format(app.config["S3_AUDIO_UPLOAD_DIRECTORY"], hex))
                else:
                    images.append(f)

        outputs = s3_uploads(images, '{}/{}'.format(app.config["S3_UPLOAD_DIRECTORY"], hex))
        song_url = 'https://s3.amazonaws.com/{}/{}/{}'.format(app.config["S3_BUCKET"], '{}/{}'.format(app.config["S3_AUDIO_UPLOAD_DIRECTORY"], hex), out)
        song = download_song(song_url)
        beats = get_beats(song)
        images_url = 'https://s3.amazonaws.com/{}/{}/'.format(app.config["S3_BUCKET"], '{}/{}'.format(app.config["S3_UPLOAD_DIRECTORY"], hex))
        instructions = create_instructions(beats, images_url)
        send_to_ffmpeg(images_url, song_url, instructions, email)

    # out = s3_upload(form.audio, '{}/{}'.format(app.config["S3_AUDIO_UPLOAD_DIRECTORY"], hex))
    # outputs = s3_uploads(request.files.getlist("example"), '{}/{}'.format(app.config["S3_UPLOAD_DIRECTORY"], hex))
    # flash('{src} uploaded to S3 as {dst}'.format(src=form.example.data.filename, dst=out))
    # for output in outputs:
    #     flash('{src} uploaded to S3 as {dst}'.format(src=form.example.data.filename, dst=output))
    # song_url = 'https://s3.amazonaws.com/{}/{}/{}'.format(app.config["S3_BUCKET"], '{}/{}'.format(app.config["S3_AUDIO_UPLOAD_DIRECTORY"], hex), out)
    # song = download_song(song_url)
    # beats = get_beats(song)
    # images_url = 'https://s3.amazonaws.com/{}/{}/'.format(app.config["S3_BUCKET"], '{}/{}'.format(app.config["S3_UPLOAD_DIRECTORY"], hex))
    # instructions = create_instructions(beats, images_url)
    # send_to_ffmpeg(images_url, song_url, instructions)


    # print("upload page")
    # form = UploadForm()
    # print("about to validate")
    # if form.validate_on_submit():
    #     print("form validated")
    #     print(form.example.data)
    #     print(request.files.getlist("example"))
    #     # print(request.FILES[form.example].read())
    #     hex = uuid4().hex
    #     out = s3_upload(form.audio, '{}/{}'.format(app.config["S3_AUDIO_UPLOAD_DIRECTORY"], hex))
    #     outputs = s3_uploads(request.files.getlist("example"), '{}/{}'.format(app.config["S3_UPLOAD_DIRECTORY"], hex))
    #     flash('{src} uploaded to S3 as {dst}'.format(src=form.example.data.filename, dst=out))
    #     for output in outputs:
    #         flash('{src} uploaded to S3 as {dst}'.format(src=form.example.data.filename, dst=output))
    #     song_url = 'https://s3.amazonaws.com/{}/{}/{}'.format(app.config["S3_BUCKET"], '{}/{}'.format(app.config["S3_AUDIO_UPLOAD_DIRECTORY"], hex), out)
    #     song = download_song(song_url)
    #     beats = get_beats(song)
    #     images_url = 'https://s3.amazonaws.com/{}/{}/'.format(app.config["S3_BUCKET"], '{}/{}'.format(app.config["S3_UPLOAD_DIRECTORY"], hex))
    #     instructions = create_instructions(beats, images_url)
    #     send_to_ffmpeg(images_url, song_url, instructions)
    return render_template('example.html')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


# @app.route('/')
# def audio():
#     song = download_song(song_url)
#     beats = get_beats(song)
#     instructions = create_instructions(beats, images_url)
#     send_to_ffmpeg(instructions)
#     response = build_response({'beats': beats}, 200)
#
#     return response



if __name__ == '__main__':
    app.run()
    # app.run(host='0.0.0.0', port=5001)
