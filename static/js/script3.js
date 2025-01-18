document.getElementById('fetch-tokens-button').addEventListener('click', fetchTokens);

function fetchTokens() {
    const progressBar = document.getElementById('progress-bar');
    const tokensContainer = document.getElementById('tokens-container');

    // Reset UI
    progressBar.style.width = '0%';
    tokensContainer.innerHTML = '';

    // Simulate the progress bar filling up
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        progressBar.style.width = `${progress}%`;
        if (progress >= 100) clearInterval(interval);
    }, 100);

    fetch('/fetch_tokens')
        .then(response => response.json())
        .then(tokens => {
            progressBar.style.width = '100%';

            if (tokens.length > 0) {
                tokens.forEach(token => {
                    const tokenCard = document.createElement('div');
                    tokenCard.classList.add('token-card');

                    // Masked Contract Address
                    const maskedAddress = `${token.tokenAddress.slice(0, 6)}...${token.tokenAddress.slice(-6)}`;
                    const addressElement = document.createElement('p');
                    addressElement.classList.add('contract-address');
                    addressElement.textContent = `Contract Address: ${maskedAddress}`;
                    tokenCard.appendChild(addressElement);

                    // Copy Button
                    const copyButton = document.createElement('button');
                    copyButton.textContent = 'Copy';
                    copyButton.classList.add('copy-button');
                    copyButton.onclick = () => {
                        navigator.clipboard.writeText(token.tokenAddress);
                        copyButton.textContent = 'Copied';
                        setTimeout(() => {
                            copyButton.textContent = 'Copy';
                        }, 2000); // Revert back to "Copy" after 2 seconds
                    };
                    tokenCard.appendChild(copyButton);

                    // Token Icon
                    if (token.icon) {
                        const iconElement = document.createElement('img');
                        iconElement.classList.add('token-icon');
                        iconElement.src = token.icon;
                        tokenCard.appendChild(iconElement);
                    }

                    // Display Chain ID
                    if (token.chainId) {
                        const chainIdElement = document.createElement('p');
                        chainIdElement.textContent = `Chain ID: ${token.chainId}`;
                        tokenCard.appendChild(chainIdElement);
                    }

                    // Hyperlinks
                    if (token.links && typeof token.links === 'object') {
                        for (const [type, url] of Object.entries(token.links)) {
                            const linkElement = document.createElement('a');
                            linkElement.href = url;
                            linkElement.textContent = type;
                            linkElement.classList.add('token-link');
                            linkElement.target = '_blank';
                            tokenCard.appendChild(linkElement);
                        }
                    }

                    tokensContainer.appendChild(tokenCard);
                });
            } else {
                tokensContainer.textContent = 'No tokens found';
            }
        })
        .catch(error => {
            clearInterval(interval);
            progressBar.style.width = '0%';
            console.error('Error fetching tokens:', error);
        });
}
