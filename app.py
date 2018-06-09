from flask import Flask, jsonify, make_response, request, abort, Response
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


app = Flask(__name__)


win_s = 512                 # fft size
hop_s = win_s // 2          # hop size

images_url = 'https://s3.amazonaws.com/hiphy/images/'
song_url = 'https://s3.amazonaws.com/hiphy/song/jason.wav'
ffmpeg_url = 'https://fe13pn0b30.execute-api.us-west-2.amazonaws.com/dev/v1/convert'

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
    print(images)
    images = [
        i for i in images if i.endswith('.jpg') or i.endswith('.png')
    ]
    random.shuffle(images)
    with open('images.txt', 'w') as image_file:
        before = float(0.000)
        j = 0
        for i, e in enumerate(beats):
            if j >= len(images):
                j = 0
            duration = float(float(e) - before)
            duration = "{0:.2f}".format(duration)
            before = float(e)
            image_file.write('file {}\n'.format(images[j]))
            image_file.write('duration {}\n'.format(duration))
            j = j + 1


def send_to_ffmpeg():
    files = {'instructions': open('images.txt', 'rb')}
    values = {
        'images_s3_url': images_url,
        'song_s3_url': song_url
    }

    requests.post(ffmpeg_url, files=files, json=values)


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


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/')
def audio():
    song = download_song(song_url)
    beats = get_beats(song)
    create_instructions(beats, images_url)
    send_to_ffmpeg()
    response = build_response({'beats': beats}, 200)

    return response



if __name__ == '__main__':
    app.run()
