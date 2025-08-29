// Theme Management System
class ThemeManager {
    constructor() {
        this.currentTheme = 'dark';
        this.init();
    }

    init() {
        this.loadSavedTheme();
        this.setupEventListeners();
        this.updateThemePreview();
        this.updateSystemInfo();
    }

    loadSavedTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            this.setTheme(savedTheme);
        } else {
            // Default to dark theme
            this.setTheme('dark');
        }
    }

    setTheme(theme) {
        this.currentTheme = theme;
        document.documentElement.setAttribute('data-theme', theme);

        // Update radio buttons
        const radioButtons = document.querySelectorAll('input[name="theme"]');
        radioButtons.forEach(radio => {
            radio.checked = radio.value === theme;
        });

        // Save to localStorage
        if (document.getElementById('autoSaveTheme')?.checked) {
            localStorage.setItem('theme', theme);
        }

        this.updateThemePreview();
        this.updateSystemInfo();
        this.showThemeChangeNotification();
    }

    setupEventListeners() {
        // Theme radio buttons
        const themeRadios = document.querySelectorAll('input[name="theme"]');
        themeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.setTheme(e.target.value);
            });
        });

        // Other settings
        this.setupOtherSettings();
    }

    setupOtherSettings() {
        // Language selector
        const languageSelect = document.getElementById('languageSelect');
        if (languageSelect) {
            languageSelect.addEventListener('change', (e) => {
                this.saveSetting('language', e.target.value);
            });
        }

        // Items per page
        const itemsPerPage = document.getElementById('itemsPerPage');
        if (itemsPerPage) {
            itemsPerPage.addEventListener('change', (e) => {
                this.saveSetting('itemsPerPage', e.target.value);
            });
        }

        // Animation speed
        const animationSpeed = document.getElementById('animationSpeed');
        if (animationSpeed) {
            animationSpeed.addEventListener('input', (e) => {
                this.saveSetting('animationSpeed', e.target.value);
                this.updateAnimationSpeed(e.target.value);
            });
        }

        // Compact mode
        const compactMode = document.getElementById('compactMode');
        if (compactMode) {
            compactMode.addEventListener('change', (e) => {
                this.saveSetting('compactMode', e.target.checked);
                this.toggleCompactMode(e.target.checked);
            });
        }

        // Notification settings
        const notificationSettings = ['enableNotifications', 'soundEffects', 'autoSaveNotifications'];
        notificationSettings.forEach(setting => {
            const element = document.getElementById(setting);
            if (element) {
                element.addEventListener('change', (e) => {
                    this.saveSetting(setting, e.target.checked);
                });
            }
        });
    }

    saveSetting(key, value) {
        const settings = this.getSettings();
        settings[key] = value;
        localStorage.setItem('appSettings', JSON.stringify(settings));
    }

    getSettings() {
        const saved = localStorage.getItem('appSettings');
        return saved ? JSON.parse(saved) : {};
    }

    updateThemePreview() {
        const previewCard = document.querySelector('.theme-preview-card');
        if (previewCard) {
            previewCard.className = `theme-preview-card ${this.currentTheme}`;
        }
    }

    updateSystemInfo() {
        const currentThemeElement = document.getElementById('currentTheme');
        if (currentThemeElement) {
            currentThemeElement.textContent = this.currentTheme.charAt(0).toUpperCase() + this.currentTheme.slice(1);
        }

        const browserInfoElement = document.getElementById('browserInfo');
        if (browserInfoElement) {
            browserInfoElement.textContent = this.getBrowserInfo();
        }

        const lastUpdatedElement = document.getElementById('lastUpdated');
        if (lastUpdatedElement) {
            lastUpdatedElement.textContent = new Date().toLocaleString();
        }
    }

    getBrowserInfo() {
        const ua = navigator.userAgent;
        if (ua.includes('Chrome')) return 'Chrome';
        if (ua.includes('Firefox')) return 'Firefox';
        if (ua.includes('Safari')) return 'Safari';
        if (ua.includes('Edge')) return 'Edge';
        return 'Unknown';
    }

    updateAnimationSpeed(speed) {
        const root = document.documentElement;
        const duration = (speed / 100) * 0.5 + 0.1; // 0.1s to 0.6s
        root.style.setProperty('--animation-duration', `${duration}s`);
    }

    toggleCompactMode(enabled) {
        document.body.classList.toggle('compact-mode', enabled);
    }

    showThemeChangeNotification() {
        if (document.getElementById('enableNotifications')?.checked) {
            this.showNotification(`Switched to ${this.currentTheme} theme`, 'success');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 3000);
    }
}

// Quick Actions
function resetToDefaults() {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
        localStorage.removeItem('theme');
        localStorage.removeItem('appSettings');

        // Reset to dark theme
        document.documentElement.setAttribute('data-theme', 'dark');
        document.querySelector('input[value="dark"]').checked = true;

        // Reset form elements
        document.getElementById('languageSelect').value = 'vi';
        document.getElementById('itemsPerPage').value = '25';
        document.getElementById('animationSpeed').value = '50';
        document.getElementById('compactMode').checked = false;
        document.getElementById('autoSaveTheme').checked = true;
        document.getElementById('enableNotifications').checked = true;
        document.getElementById('soundEffects').checked = true;
        document.getElementById('autoSaveNotifications').checked = false;

        // Remove compact mode
        document.body.classList.remove('compact-mode');

        themeManager.showNotification('Settings reset to defaults', 'success');
    }
}

function exportSettings() {
    const settings = {
        theme: localStorage.getItem('theme') || 'dark',
        appSettings: JSON.parse(localStorage.getItem('appSettings') || '{}'),
        exportDate: new Date().toISOString()
    };

    const dataStr = JSON.stringify(settings, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});

    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = 'app-settings.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    themeManager.showNotification('Settings exported successfully', 'success');
}

function importSettings() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';

    input.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const settings = JSON.parse(e.target.result);

                    if (settings.theme) {
                        localStorage.setItem('theme', settings.theme);
                        themeManager.setTheme(settings.theme);
                    }

                    if (settings.appSettings) {
                        localStorage.setItem('appSettings', JSON.stringify(settings.appSettings));
                    }

                    themeManager.showNotification('Settings imported successfully', 'success');

                    // Reload page to apply all settings
                    setTimeout(() => location.reload(), 1000);
                } catch (error) {
                    themeManager.showNotification('Invalid settings file', 'danger');
                }
            };
            reader.readAsText(file);
        }
    };

    input.click();
}

// Initialize theme manager when DOM is loaded
let themeManager;
document.addEventListener('DOMContentLoaded', () => {
    themeManager = new ThemeManager();
});