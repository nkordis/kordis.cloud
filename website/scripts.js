// API base URL
const API_URL = 'https://api.kordis.cloud/visits';

// General utility functions
function initialize() {
    // The PUT response already carries the count; GET only if the PUT fails
    updateVisitorCount()
        .then(showCount)
        .catch(error => {
            console.error("Error updating the count:", error);
            fetchCount();
        });
}

function showCount(count) {
    document.getElementById('visitorCount').textContent = count;
}

// Function to update the visitor count; resolves to the new count
async function updateVisitorCount() {
    const response = await fetch(API_URL, { method: 'PUT' });
    if (!response.ok) {
        throw new Error('Network response was not ok: ' + response.statusText);
    }
    const data = await response.json();
    return data.visitsCount;
}

// Fetch visitor count
async function fetchCount() {
    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.statusText);
        }
        const data = await response.json();
        showCount(data.visitsCount);
    } catch (error) {
        console.error('Error fetching the count:', error);
        document.getElementById('visitorCount').textContent = 'Failed to load visitor count.';
    }
}

window.onload = initialize;
