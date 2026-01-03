/**
 * Restaurant POS - Digital Menu Bundle
 * Frontend JavaScript for customer-facing menu
 */

// This bundle file imports the main digital_menu.js
// It's structured this way for Frappe's asset bundling

// The main DigitalMenu class is defined in digital_menu.js
// This file provides additional utilities and initialization

(function() {
    'use strict';

    /**
     * Utility functions for the digital menu
     */
    window.MenuUtils = {
        /**
         * Format price with currency
         */
        formatPrice(amount, currency = 'SAR') {
            return `${currency} ${parseFloat(amount).toFixed(2)}`;
        },

        /**
         * Get current language
         */
        getLanguage() {
            return localStorage.getItem('menu_language') || 
                   document.documentElement.lang || 
                   'en';
        },

        /**
         * Set language
         */
        setLanguage(lang) {
            localStorage.setItem('menu_language', lang);
            document.documentElement.lang = lang;
            document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
        },

        /**
         * Get text in current language
         */
        getText(textEn, textAr) {
            const lang = this.getLanguage();
            return (lang === 'ar' && textAr) ? textAr : (textEn || '');
        },

        /**
         * Debounce function
         */
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        /**
         * Generate UUID
         */
        generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        },

        /**
         * Get cart from local storage
         */
        getStoredCart() {
            try {
                return JSON.parse(localStorage.getItem('restaurant_cart')) || [];
            } catch {
                return [];
            }
        },

        /**
         * Save cart to local storage
         */
        saveCart(cart) {
            localStorage.setItem('restaurant_cart', JSON.stringify(cart));
        },

        /**
         * Clear stored cart
         */
        clearStoredCart() {
            localStorage.removeItem('restaurant_cart');
        },

        /**
         * Show loading spinner
         */
        showLoading(container) {
            const spinner = document.createElement('div');
            spinner.className = 'loading-spinner';
            spinner.innerHTML = '<div class="spinner"></div>';
            container.appendChild(spinner);
        },

        /**
         * Hide loading spinner
         */
        hideLoading(container) {
            const spinner = container.querySelector('.loading-spinner');
            if (spinner) spinner.remove();
        },

        /**
         * Show toast notification
         */
        showToast(message, type = 'info', duration = 3000) {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            
            document.body.appendChild(toast);
            
            // Trigger animation
            requestAnimationFrame(() => {
                toast.classList.add('show');
            });
            
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        },

        /**
         * Vibrate device (if supported)
         */
        vibrate(pattern = 50) {
            if ('vibrate' in navigator) {
                navigator.vibrate(pattern);
            }
        },

        /**
         * Check if online
         */
        isOnline() {
            return navigator.onLine;
        },

        /**
         * Format time elapsed
         */
        formatTimeElapsed(minutes) {
            if (minutes < 1) return 'Just now';
            if (minutes === 1) return '1 min';
            if (minutes < 60) return `${minutes} mins`;
            const hours = Math.floor(minutes / 60);
            return hours === 1 ? '1 hour' : `${hours} hours`;
        }
    };

    /**
     * Offline support manager
     */
    window.OfflineManager = {
        db: null,

        async init() {
            if (!('indexedDB' in window)) return;

            return new Promise((resolve, reject) => {
                const request = indexedDB.open('RestaurantMenuDB', 1);
                
                request.onerror = () => reject(request.error);
                request.onsuccess = () => {
                    this.db = request.result;
                    resolve();
                };
                
                request.onupgradeneeded = (event) => {
                    const db = event.target.result;
                    
                    if (!db.objectStoreNames.contains('menu_items')) {
                        db.createObjectStore('menu_items', { keyPath: 'name' });
                    }
                    if (!db.objectStoreNames.contains('categories')) {
                        db.createObjectStore('categories', { keyPath: 'name' });
                    }
                    if (!db.objectStoreNames.contains('pending_orders')) {
                        db.createObjectStore('pending_orders', { keyPath: 'id', autoIncrement: true });
                    }
                };
            });
        },

        async cacheMenuData(categories, items) {
            if (!this.db) return;

            const categoryTx = this.db.transaction('categories', 'readwrite');
            const categoryStore = categoryTx.objectStore('categories');
            categories.forEach(cat => categoryStore.put(cat));

            const itemTx = this.db.transaction('menu_items', 'readwrite');
            const itemStore = itemTx.objectStore('menu_items');
            items.forEach(item => itemStore.put(item));
        },

        async getCachedMenu() {
            if (!this.db) return { categories: [], items: [] };

            const categories = await this.getAllFromStore('categories');
            const items = await this.getAllFromStore('menu_items');

            return { categories, items };
        },

        async savePendingOrder(order) {
            if (!this.db) return;

            const tx = this.db.transaction('pending_orders', 'readwrite');
            const store = tx.objectStore('pending_orders');
            store.add(order);
        },

        async getPendingOrders() {
            return this.getAllFromStore('pending_orders');
        },

        async removePendingOrder(id) {
            if (!this.db) return;

            const tx = this.db.transaction('pending_orders', 'readwrite');
            const store = tx.objectStore('pending_orders');
            store.delete(id);
        },

        getAllFromStore(storeName) {
            return new Promise((resolve, reject) => {
                const tx = this.db.transaction(storeName, 'readonly');
                const store = tx.objectStore(storeName);
                const request = store.getAll();
                
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        }
    };

    /**
     * Service worker registration for PWA support
     */
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/assets/restaurant_pos/sw.js')
                .then(registration => {
                    console.log('SW registered:', registration);
                })
                .catch(error => {
                    console.log('SW registration failed:', error);
                });
        });
    }

    /**
     * Handle online/offline status
     */
    window.addEventListener('online', () => {
        MenuUtils.showToast('Back online!', 'success');
        // Sync pending orders
        syncPendingOrders();
    });

    window.addEventListener('offline', () => {
        MenuUtils.showToast('You are offline. Orders will be synced when back online.', 'warning', 5000);
    });

    async function syncPendingOrders() {
        const pendingOrders = await OfflineManager.getPendingOrders();
        
        for (const order of pendingOrders) {
            try {
                const response = await fetch('/api/method/restaurant_pos.restaurant_pos.api.order.place_order', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(order)
                });
                
                if (response.ok) {
                    await OfflineManager.removePendingOrder(order.id);
                    MenuUtils.showToast('Order synced successfully!', 'success');
                }
            } catch (error) {
                console.error('Failed to sync order:', error);
            }
        }
    }

    // Initialize offline support
    OfflineManager.init().catch(console.error);

})();
