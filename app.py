from flask import Flask, render_template, jsonify
import requests
from apebot_v2 import fetch_tokens, save_ca_to_file, filter_tokens, load_blacklist

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index4.html')

@app.route('/fetch_tokens')
def fetch_tokens_route():
    tokens = fetch_tokens()
    return(tokens)

if __name__ == '__main__':
    app.run(debug=True)
