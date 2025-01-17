from flask import Flask, request, jsonify, send_file
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# Function to process tokens (this is your bot functionality)
def extract_and_save_contract_addresses(input_file, output_file):
    try:
        with open(input_file, "r") as f:
            data = json.load(f)
        
        # Extract contract addresses
        token_addresses = [token.get("tokenAddress", "") for token in data if "tokenAddress" in token]
        
        # Save to output file
        with open(output_file, "w") as f:
            for address in token_addresses:
                f.write(f"{address}\n")
        return True
    except Exception as e:
        return str(e)

# API endpoint to trigger the bot
@app.route('/process_tokens', methods=['POST'])
def process_tokens():
    input_file = "filtered_tokens_2.json"  # File containing tokens
    output_file = "contract_addresses.txt"  # File to save results

    # Call the function
    result = extract_and_save_contract_addresses(input_file, output_file)
    
    if result is True:
        return jsonify({"message": "Contract addresses saved successfully"}), 200
    else:
        return jsonify({"error": f"Failed to process tokens: {result}"}), 500

# API endpoint to download the file
@app.route('/download_addresses', methods=['GET'])
def download_addresses():
    file_path = "contract_addresses.txt"
    try:
        return send_file(file_path, as_attachment=True), 200
    except Exception as e:
        return jsonify({"error": f"Failed to download file: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
