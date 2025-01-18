function fetchTokens() {
    fetch('/fetch_tokens')
        .then(response => response.json())
        .then(tokens => {
            console.log('Tokens:', tokens);

            const tokensContainer = document.getElementById('tokens-container');
            tokensContainer.innerHTML = ''; // Clear previous content

            if (tokens.length > 0) {
                tokens.forEach(token => {
                    const tokenElement = document.createElement('div');
                    tokenElement.classList.add('token-card');

                    const addressElement = document.createElement('p');
                    addressElement.classList.add('contract-address');
                    addressElement.textContent = `Contract Address: ${token.tokenAddress}`;

                    const copyButton = document.createElement('button');
                    copyButton.textContent = 'Copy';
                    copyButton.classList.add('copy-button');
                    copyButton.onclick = () => {
                        navigator.clipboard.writeText(token.tokenAddress);
                        alert('Contract address copied to clipboard!');
                    };

                    tokenElement.appendChild(addressElement);
                    tokenElement.appendChild(copyButton);
                    tokensContainer.appendChild(tokenElement);
                });
            } else {
                tokensContainer.textContent = 'No tokens found';
            }
        })
        .catch(error => console.error('Error fetching tokens:', error));
}
