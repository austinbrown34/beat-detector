from flask import Flask, jsonify, make_response, request, abort, Response
import json
import os
import subprocess
import random
from aubio import source, tempo, onset
from numpy import median, diff
from pydub import AudioSegment


app = Flask(__name__)


def build_response(resp_dict, status_code):
    response = Response(json.dumps(resp_dict), status_code)
    return response


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/')
def audio():


    return "Beat Finder"



if __name__ == '__main__':
    app.run()
