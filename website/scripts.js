// API base URL
const API_URL = 'https://api.kordis.cloud/visits';

// General utility functions
function initialize() {
    updateVisitorCount()
        .then(fetchCount)
        .catch(error => {
            console.error("Error during initialization:", error);
        });
}

// Function to update the visitor count
async function updateVisitorCount() {
    const response = await fetch(API_URL, { method: 'PUT' });
    if (!response.ok) {
        throw new Error('Network response was not ok: ' + response.statusText);
    }
    const data = await response.json();
    console.log('Visitor count updated:', data);
}

// Fetch visitor count
async function fetchCount() {
    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.statusText);
        }
        const data = await response.json();
        document.getElementById('visitorCount').textContent = data.visitsCount;
    } catch (error) {
        console.error('Error fetching the count:', error);
        document.getElementById('visitorCount').textContent = 'Failed to load visitor count.';
    }
}

window.onload = initialize;
