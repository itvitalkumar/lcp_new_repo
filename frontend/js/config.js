// ============================================================
// CAMPUS CENTRAL - MASTER CONFIGURATION (DUPLICATE SAFE)
// ============================================================
//
// PHASE 1 (June 18, 2026):
//   - Initial deployment with local + production config.
//   - Production pointed to old Azure backend URL.
//
// PHASE 2 (June 19, 2026):
//   - Updated production API_BASE_URL to current backend.
//   - Updated production APP_URL to current frontend URL.
//   - Added docstrings and environment notes.
//   - Default environment changed to 'production' for live usage.
// ============================================================

if (typeof window.__CONFIG_LOADED === 'undefined') {
    
    // ============================================================
    // ENVIRONMENT SELECTION
    // ============================================================
    // Change this to 'local' for local development,
    // or 'production' for Azure live deployment.
    // ============================================================
    let ENVIRONMENT = 'production';  // 'local' OR 'production'
    
    // ============================================================
    // CONFIGURATION OBJECT
    // ============================================================
    let CONFIG = {
        /**
         * LOCAL DEVELOPMENT SETTINGS
         * Used when running frontend locally via Live Server / localhost.
         */
        local: {
            /**
             * Backend API URL for local development.
             * Assumes backend is running on port 8000.
             */
            API_BASE_URL: 'http://localhost:8000/api',
            
            /**
             * Frontend app URL for local development.
             * Typically Live Server or similar.
             */
            APP_URL: 'http://localhost:5500',
            
            /**
             * Display name for environment identification.
             */
            ENV_NAME: '🔧 LOCAL DEVELOPMENT',
        },
        
        /**
         * PRODUCTION SETTINGS (Azure)
         * Used when frontend is deployed to Azure Static Web Apps.
         */
        production: {
            /**
             * Backend API URL for production.
             * Points to the live FastAPI backend on Azure App Service.
             */
            API_BASE_URL: 'https://lcp-backend-app.azurewebsites.net/api',
            
            /**
             * Frontend app URL for production.
             * Points to the live Azure Static Web App.
             */
            APP_URL: 'https://agreeable-pond-0372cb110.7.azurestaticapps.net',
            
            /**
             * Display name for environment identification.
             */
            ENV_NAME: '☁️ PRODUCTION (Azure)',
        }
    };
    
    // ============================================================
    // ACTIVATE THE SELECTED ENVIRONMENT
    // ============================================================
    let ACTIVE_CONFIG = CONFIG[ENVIRONMENT];
    
    // ============================================================
    // CONSOLE LOGGING FOR DEBUGGING
    // ============================================================
    // Logs the active environment and API URL to the browser console.
    // Helpful for verifying which backend the frontend is calling.
    // ============================================================
    console.log(
        `%c🚀 Campus Central - ${ACTIVE_CONFIG.ENV_NAME}`,
        'color: #2ecc71; font-size: 14px; font-weight: bold;'
    );
    console.log(`📍 API URL: ${ACTIVE_CONFIG.API_BASE_URL}`);
    
    // ============================================================
    // GLOBAL EXPOSURE
    // ============================================================
    // Makes the active config available globally so other scripts
    // can access it via window.ACTIVE_CONFIG.
    // ============================================================
    window.ACTIVE_CONFIG = ACTIVE_CONFIG;
    window.__CONFIG_LOADED = true;
}