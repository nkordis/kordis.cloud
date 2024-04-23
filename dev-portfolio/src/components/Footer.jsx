import React, { useState, useEffect } from 'react';

const API_URL = 'https://i1nk81bamc.execute-api.us-east-1.amazonaws.com/Prod/visits';

const styles = {
  footerContainer: {
    width: '100%',
    padding: '10px 0',
    backgroundColor: '#343a40',
    color: '#ffffff',
    textAlign: 'center',
    position: 'fixed',
    bottom: 0,
    left: 0,
    right: 0,
  },
};

const Footer = () => {
  const [visitorCount, setVisitorCount] = useState('Loading...');

  useEffect(() => {
    const fetchAndUpdateVisitorCount = async () => {
      try {
        // Update visitor count first
        await fetch(API_URL, { method: 'PUT' });
        // Then fetch the updated count
        const response = await fetch(API_URL);
        if (!response.ok) {
          throw new Error('Failed to fetch visitor count');
        }
        const data = await response.json();
        setVisitorCount(data.visitsCount ?? 'Unavailable'); // Use nullish coalescing to handle undefined counts
      } catch (error) {
        setVisitorCount('Failed to load');
      }
    };

    fetchAndUpdateVisitorCount(); // Initialize visitor count update and fetch on mount
  }, []);

  return (
    <div style={styles.footerContainer}>
      Visitors:
      {' '}
      {visitorCount}
    </div>
  );
};

export default Footer;
