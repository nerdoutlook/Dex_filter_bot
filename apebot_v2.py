import requests
import pandas as pd
import json
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from collections import Counter

# Initialize a blacklist
blacklist = set()

#def fetch_tokens():
#    response = requests.get('https://api.dexscreener.com/token-profiles/latest/v1')
#    tokens = response.json()
#    return tokens

def fetch_tokens():
    # Fetch data from the Dexscreener API
    #response = requests.get("https://api.dexscreener.com/token-profiles/latest/v1")
    #Latest boosted tokens
    response = requests.get("https://api.dexscreener.com/token-boosts/latest/v1")
    #Tokens with the most active boosts
    #response = requests.get("https://api.dexscreener.com/token-boosts/top/v1")
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        return []

    try:
        data = response.json()
    except ValueError:
        print("Failed to decode JSON response")
        return []

    # Ensure the data is in the expected structure
#    tokens = data.get('tokens', [])  # Assuming the API returns a 'tokens' key
    tokens = data
    if not tokens:
        print("No tokens found in the response")
    return tokens

def get_twitter_score(account_name):
    response = requests.get(f'https://scoretwitter.com/{account_name}')
    score_data = response.json()
    return score_data.get('score', 0)

def check_rugcheck_status(contract_address):
    response = requests.get(f'https://rugcheck.xyz/api/check/{contract_address}')
    status_data = response.json()
    return status_data.get('status', '')

def detect_fraudulent_activity(token):
    trading_volume = token.get('trading_volume_24h', 0)
    market_cap = token.get('market_cap', 0)
    historical_data = token.get('historical_data', [])

    if len(historical_data) < 10:
        return False

    volumes = [entry['volume'] for entry in historical_data]
    market_caps = [entry['market_cap'] for entry in historical_data]

    avg_volume = sum(volumes) / len(volumes)
    avg_market_cap = sum(market_caps) / len(market_caps)

    volume_std = (sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)) ** 0.5
    market_cap_std = (sum((m - avg_market_cap) ** 2 for m in market_caps) / len(market_caps)) ** 0.5

    volume_threshold = avg_volume + 3 * volume_std
    market_cap_threshold = avg_market_cap + 3 * market_cap_std

    is_volume_spike = trading_volume > volume_threshold
    is_market_cap_spike = market_cap > market_cap_threshold

    return is_volume_spike or is_market_cap_spike

def check_supply_distribution(holders):
    balances = [holder['balance'] for holder in holders]

    # Count occurrences of each balance
    balance_counter = Counter(balances)

    # Bundle threshold
    bundle_threshold = 5  # Example: at least 5 holders having the same balance

    for balance, count in balance_counter.items():
        if count >= bundle_threshold:
            return True  # Indicates suspicious bundled distribution

    return False

def send_to_trading_bot(contract_address):
    # Placeholder for trading bot API call
    trading_bot_api_url = 'YOUR_TRADING_BOT_API_ENDPOINT'
    payload = {'contract_address': contract_address}

    response = requests.post(trading_bot_api_url, json=payload)
    if response.status_code == 200:
        print(f"Successfully sent {contract_address} to trading bot.")
    else:
        print(f"Failed to send {contract_address} to trading bot: {response.content}")

def filter_tokens(tokens):
    filtered = []
    for token in tokens:
        print(token.get('creation_date'))
        market_cap = token.get('market_cap', 0)
        trading_volume = token.get('trading_volume_24h', 0)

        creation_date_raw = token.get('creation_date')
        if isinstance(creation_date_raw, str):
            try:
                creation_date = datetime.fromisoformat(creation_date_raw)
            except ValueError:
                print(f"Invalid ISO format for creation_date: {creation_date_raw}")
                continue
            else:
                  print(f"Missing or invalid creation_date for token: {token}")
            continue

        holder_count = token.get('holders', 0)
        unpaid_listing = token.get('unpaid_listing', False)
        social_media_links = token.get('social_media_links', [])
        total_supply = token.get('total_supply', 0)
        top_holders = token.get('top_holders', [])
        twitter_account = token.get('twitter_account', '')
        contract_address = token.get('contract_address', '')
        holders = token.get('holders_data', [])  # Assuming this field contains the holder data

        # Get the creator's address
        creator_address = token.get('creator_address', '')

        # Check if the creator is in the blacklist
        if creator_address in blacklist:
            continue

        # Calculate the percentage owned by the top 10 holders
        if total_supply > 0:
            top_10_percentage = sum(holder['balance'] for holder in top_holders[:10]
                                    if holder['address'] not in ['LIQUIDITY_POOL_ADDRESS', 'BURN_ADDRESS']) / total_supply

            # Get Twitter score
            twitter_score = get_twitter_score(twitter_account)

            # Check Rugcheck status
            rugcheck_status = check_rugcheck_status(contract_address)

            # Detect fraudulent activity
            is_fraudulent = detect_fraudulent_activity(token)

            # Check supply distribution
            has_bundled_distribution = check_supply_distribution(holders)

            # Exclude based on criteria
            if (market_cap <= 200_000 and
                    trading_volume <= 1_000_000 and
                    (datetime.now() - creation_date) <= timedelta(days=0, hours=2) and
                    holder_count <= 10_000 and
                    not unpaid_listing and
                    social_media_links and
                    top_10_percentage <= 40 and
                    twitter_score >= 3 and
                    rugcheck_status == "Good" and
                    not is_fraudulent and
                    not has_bundled_distribution):  # Exclude if conditions are met
                filtered.append(token)
                # Send to trading bot
                #send_to_trading_bot(contract_address)
            else:
                # Add to blacklist if any condition fails
                blacklist.add(creator_address)

    return filtered

def save_to_file(tokens, filename='filtered_tokens_2.json'):
    if not tokens:
        print("No tokens to save.")
        return
    with open(filename, 'w') as file:
        json.dump(tokens, file, indent=4)
    print(f"Saved {len(tokens)} tokens to {filename}.")

def save_to_db(filtered_tokens):
    if not filtered_tokens:
        print("No tokens to save to DB.")
        return
    
    engine = create_engine('sqlite:///tokens.db')
    clean_tokens = []
    for token in filtered_tokens:
        flat_token = {k: v for k, v in token.items() if not isinstance(v, (list, dict))}
        clean_tokens.append(flat_token)
    
    df = pd.DataFrame(clean_tokens)
    df.to_sql('tokens', con=engine, if_exists='append', index=False)
    print(f"Saved {len(clean_tokens)} tokens to the database.")

import json

def save_ca_to_file():
    """Extracts contract addresses from a JSON file and saves them to a text file."""
    # Define file paths
    json_file_path = "filtered_tokens_2.json"
    output_file_path = "contract_addresses.txt"

    try:
        # Read the JSON file
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

        # Extract contract addresses
        contract_addresses = [
            token.get('tokenAddress', '') for token in data if 'tokenAddress' in token
        ]

        # Save contract addresses to the text file
        with open(output_file_path, 'w') as output_file:
            for address in contract_addresses:
                output_file.write(address + '\n')

        print(f"Contract addresses have been saved to {output_file_path}.")
    except FileNotFoundError:
        print(f"Error: The file {json_file_path} does not exist.")
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON. Please check the file content.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    tokens = fetch_tokens()
    filtered_tokens = filter_tokens(tokens)
    #save_to_db(filtered_tokens)
    save_to_file(tokens)
    #print(len(blacklist))
    save_ca_to_file()

if __name__ == '__main__':
    main()
