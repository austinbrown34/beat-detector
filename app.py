from flask import Flask, jsonify, make_response, request, abort, Response
import json
import os
import subprocess
import random
from aubio import source, tempo, onset
from numpy import median, diff
from pydub import AudioSegment


app = Flask(__name__)


win_s = 512                 # fft size
hop_s = win_s // 2          # hop size



def get_beats(path, params=None):
    """ Calculate the beats per minute (bpm) of a given file.
        path: path to the file
        param: dictionary of parameters
    """
    if params is None:
        params = {}
    # default:
    samplerate, win_s, hop_s = 44100, 1024, 512
    if 'mode' in params:
        if params.mode in ['super-fast']:
            # super fast
            samplerate, win_s, hop_s = 4000, 128, 64
        elif params.mode in ['fast']:
            # fast
            samplerate, win_s, hop_s = 8000, 512, 128
        elif params.mode in ['default']:
            pass
        else:
            print("unknown mode")
            # print("unknown mode {:s}".format(params.mode))
    # manual settings
    if 'samplerate' in params:
        samplerate = params.samplerate
    if 'win_s' in params:
        win_s = params.win_s
    if 'hop_s' in params:
        hop_s = params.hop_s

    # song = AudioSegment.from_wav(path)
    # new = song.low_pass_filter(.5)
    # new.export("mashup.wav", format="wav")
    s = source(path, samplerate, hop_s)
    samplerate = s.samplerate
    tem = tempo("specdiff", win_s, hop_s, samplerate)
    hop_s = int(win_s // 1.001)
    ns = source(path, samplerate, hop_s)

    nsamplerate = ns.samplerate


    o = onset("default", win_s, hop_s, nsamplerate)

    # List of beats, in samples
    beats = []
    # Total number of frames read
    total_frames = 0

    while True:
        nsamples, nread = ns()
        is_beat = o(nsamples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
        # if is_beat:
        #     this_beat = o.get_last_s()
        #     samples, read = s()
        #     is_actual_beat = tem(samples)
        #     if is_actual_beat:
        #     # print("BEAT!")
        #         print(this_beat)
        #         print("BEAT!")
        #         print(this_beat)
        #         beats.append(this_beat)
            # print(o.get_confidence())
            # if o.get_confidence() > 0:
            #     print("BEAT!")
            #     print(this_beat)
            #     beats.append(this_beat)
            #     outstr = "read %.2fs" % (total_frames / float(samplerate))
            #     print ("seconds:")
            #     print (outstr)
            # beats.append(this_beat)
            #if o.get_confidence() > .2 and len(beats) > 2.:
            #    break
        total_frames += nread
        if nread < hop_s:
            break
    return beats


def get_file_bpm(path, params=None):
    """ Calculate the beats per minute (bpm) of a given file.
        path: path to the file
        param: dictionary of parameters
    """
    if params is None:
        params = {}
    # default:
    samplerate, win_s, hop_s = 44100, 1024, 512
    if 'mode' in params:
        if params.mode in ['super-fast']:
            # super fast
            samplerate, win_s, hop_s = 4000, 128, 64
        elif params.mode in ['fast']:
            # fast
            samplerate, win_s, hop_s = 8000, 512, 128
        elif params.mode in ['default']:
            pass
        else:
            print("unknown mode")
            # print("unknown mode {:s}".format(params.mode))
    # manual settings
    if 'samplerate' in params:
        samplerate = params.samplerate
    if 'win_s' in params:
        win_s = params.win_s
    if 'hop_s' in params:
        hop_s = params.hop_s

    s = source(path, samplerate, hop_s)
    samplerate = s.samplerate
    o = tempo("specdiff", win_s, hop_s, samplerate)
    # List of beats, in samples
    beats = []
    # Total number of frames read
    total_frames = 0

    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_s()


            print(o.get_confidence())
            if o.get_confidence() > .5:
                print("BEAT!")
                print(this_beat)
                beats.append(this_beat)

            #if o.get_confidence() > .2 and len(beats) > 2.:
            #    break
        total_frames += read
        if read < hop_s:
            break

    def beats_to_bpm(beats, path):
        # if enough beats are found, convert to periods then to bpm
        if len(beats) > 1:
            if len(beats) < 4:
                print("few beats found in {:s}".format(path))
            bpms = 60./diff(beats)
            return median(bpms)
        else:
            print("not enough beats found in {:s}".format(path))
            return 0

    return beats_to_bpm(beats, path)


def build_response(resp_dict, status_code):
    response = Response(json.dumps(resp_dict), status_code)
    return response


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/')
def audio():
    beats = get_beats('jason.wav')
    response = build_response({'beats': beats}, 200)

    return response



if __name__ == '__main__':
    app.run()
