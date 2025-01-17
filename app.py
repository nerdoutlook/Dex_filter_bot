from flask import Flask, render_template, jsonify
import requests
from apebot_v2 import fetch_tokens, save_ca_to_file, filter_tokens

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_tokens')
def fetch_tokens_route():
    tokens = fetch_tokens()
    print(tokens)
    filtered_tokens = filter_tokens(tokens)
    
    # Check if the filtered tokens list is empty or not
    if not filtered_tokens:
        print("No tokens after filtering.")
    
    # Return the filtered tokens to the frontend
    return jsonify(filtered_tokens)


if __name__ == '__main__':
    app.run(debug=True)
