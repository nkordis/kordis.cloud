// General utility functions
function initialize() {
    // Initialize functions for the entire site
    fetchCount();  // Call specific functions like fetching counts
}

// Fetch visitor count
function fetchCount() {
    const apiUrl = 'https://i1nk81bamc.execute-api.us-east-1.amazonaws.com/Prod/visits';
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('visitorCount').textContent = data.count;
        })
        .catch(error => {
            console.error('Error fetching the count:', error);
            document.getElementById('visitorCount').textContent = 'Failed to load visitor count.';
        });
}

window.onload = initialize;
