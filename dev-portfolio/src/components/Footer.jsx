import React from 'react';

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

const Footer = () => (
  <div style={styles.footerContainer}>
    Visitors: 14
  </div>
);

export default Footer;
