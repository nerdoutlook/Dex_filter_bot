import requests
import json
from datetime import datetime, timedelta
from collections import Counter

# Initialize a blacklist from a file
def load_blacklist():
    try:
        with open('blacklist.json', 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_blacklist(blacklist):
    with open('blacklist.json', 'w') as f:
        json.dump(list(blacklist), f)

# Fetch token data from Dexscreener API
def fetch_tokens():
    response = requests.get("https://api.dexscreener.com/token-boosts/latest/v1")
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        return []
    try:
        return response.json()
    except ValueError:
        print("Failed to decode JSON response")
        return []

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

    return trading_volume > volume_threshold or market_cap > market_cap_threshold

def check_supply_distribution(holders):
    balances = [holder['balance'] for holder in holders]
    balance_counter = Counter(balances)
    bundle_threshold = 5  # Example: at least 5 holders having the same balance
    for balance, count in balance_counter.items():
        if count >= bundle_threshold:
            return True
    return False

def filter_tokens(tokens, blacklist):
    filtered = []
    for token in tokens:
        creation_date_raw = token.get('creation_date')
        if isinstance(creation_date_raw, str):
            try:
                creation_date = datetime.fromisoformat(creation_date_raw)
            except ValueError:
                continue

        market_cap = token.get('market_cap', 0)
        trading_volume = token.get('trading_volume_24h', 0)
        holder_count = token.get('holders', 0)
        unpaid_listing = token.get('unpaid_listing', False)
        social_media_links = token.get('social_media_links', [])
        total_supply = token.get('total_supply', 0)
        top_holders = token.get('top_holders', [])
        twitter_account = token.get('twitter_account', '')
        contract_address = token.get('contract_address', '')
        holders = token.get('holders_data', [])
        creator_address = token.get('creator_address', '')

        if creator_address in blacklist:
            continue

        if total_supply > 0:
            top_10_percentage = sum(holder['balance'] for holder in top_holders[:10]) / total_supply
            twitter_score = get_twitter_score(twitter_account)
            rugcheck_status = check_rugcheck_status(contract_address)
            is_fraudulent = detect_fraudulent_activity(token)
            has_bundled_distribution = check_supply_distribution(holders)

            if (market_cap <= 200_000 and
                trading_volume <= 1_000_000 and
                (datetime.now() - creation_date) <= timedelta(hours=2) and
                holder_count <= 10_000 and
                not unpaid_listing and
                social_media_links and
                top_10_percentage <= 40 and
                twitter_score >= 3 and
                rugcheck_status == "Good" and
                not is_fraudulent and
                not has_bundled_distribution):
                filtered.append(token)

    return filtered

def save_to_file(tokens, filename='filtered_tokens_2.json'):
    if not tokens:
        print("No tokens to save.")
        return
    with open(filename, 'w') as file:
        json.dump(tokens, file, indent=4)
    print(f"Saved {len(tokens)} tokens to {filename}.")

def save_ca_to_file():
    try:
        with open("filtered_tokens_2.json", 'r') as json_file:
            data = json.load(json_file)
        contract_addresses = [token.get('tokenAddress', '') for token in data if 'tokenAddress' in token]
        with open("contract_addresses.txt", 'w') as output_file:
            for address in contract_addresses:
                output_file.write(address + '\n')
        print("Contract addresses saved to contract_addresses.txt")
    except Exception as e:
        print(f"Error occurred: {e}")
