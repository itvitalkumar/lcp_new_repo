// ============================================================
// CAMPUS CENTRAL - MASTER CONFIGURATION FILE (FIXED)
// ============================================================

// ========== ENVIRONMENT SWITCH (Change this ONE line) ==========
const ENVIRONMENT = 'local';  // 'local' OR 'production'

// ========== DO NOT EDIT BELOW THIS LINE ==========
const CONFIG = {
    local: {
        // FIXED: Use localhost consistently
        API_BASE_URL: 'http://localhost:8000/api',
        APP_URL: 'http://localhost:5500',
        ENV_NAME: '🔧 LOCAL DEVELOPMENT',
    },
    production: {
        API_BASE_URL: 'https://campus-central-api.azurewebsites.net/api',
        APP_URL: 'https://campus-central.azurestaticapps.net',
        ENV_NAME: '☁️ PRODUCTION (Azure)',
    }
};

const ACTIVE_CONFIG = CONFIG[ENVIRONMENT];

// Display which environment is active
console.log(`%c🚀 Campus Central - ${ACTIVE_CONFIG.ENV_NAME}`, 'color: #2ecc71; font-size: 14px; font-weight: bold;');
console.log(`📍 API URL: ${ACTIVE_CONFIG.API_BASE_URL}`);

// Also make it available globally
window.ACTIVE_CONFIG = ACTIVE_CONFIG;