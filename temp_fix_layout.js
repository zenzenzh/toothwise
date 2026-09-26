const fs = require('fs');
let s = fs.readFileSync('frontend/src/components/Layout.jsx', 'utf8');
s = s.replace(' <div style={styles.liveDot} /> Clinic workspace</div>', '</div>');
s = s.replace('<div style={styles.liveDot} /> Clinic workspace', '');
fs.writeFileSync('frontend/src/components/Layout.jsx', s);
console.log('Clinic workspace removed:', !s.includes('Clinic workspace'));
