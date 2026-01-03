/**
 * Restaurant POS - Kitchen Display System (KDS)
 * Real-time order management for kitchen staff
 */

class KitchenDisplay {
    constructor() {
        this.app = document.getElementById('kds-app');
        this.station = this.app?.dataset.station || '';
        this.branch = this.app?.dataset.branch || '';
        this.orders = [];
        this.refreshInterval = 5000;
        this.alertTime = 10; // minutes
        this.soundEnabled = true;
        
        this.init();
    }
    
    async init() {
        // Start clock
        this.updateClock();
        setInterval(() => this.updateClock(), 1000);
        
        // Load initial orders
        await this.loadOrders();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Setup real-time updates
        this.setupRealtime();
        
        // Start refresh interval
        this.startAutoRefresh();
        
        // Update elapsed times
        setInterval(() => this.updateElapsedTimes(), 1000);
    }
    
    updateClock() {
        const now = new Date();
        const time = now.toLocaleTimeString('en-US', { hour12: false });
        document.getElementById('clock').textContent = time;
    }
    
    async loadOrders() {
        try {
            const response = await frappe.call({
                method: 'restaurant_pos.api.kitchen.get_kitchen_orders',
                args: {
                    station: this.station,
                    branch: this.branch
                }
            });
            
            if (response.message?.success) {
                this.orders = response.message.data;
                this.renderOrders();
                this.updateStats();
            }
        } catch (error) {
            console.error('Failed to load orders:', error);
        }
    }
    
    renderOrders() {
        const grid = document.getElementById('orders-grid');
        const emptyState = document.getElementById('empty-state');
        
        if (this.orders.length === 0) {
            grid.style.display = 'none';
            emptyState.style.display = 'flex';
            return;
        }
        
        grid.style.display = 'grid';
        emptyState.style.display = 'none';
        
        grid.innerHTML = this.orders.map(order => this.createOrderCard(order)).join('');
    }
    
    createOrderCard(order) {
        const isNew = order.status === 'New';
        const isPreparing = order.status === 'Preparing';
        const isReady = order.status === 'Ready';
        const isRush = order.priority === 'Rush';
        const isAlert = order.elapsed_time > this.alertTime * 60;
        
        const elapsedClass = isAlert ? 'danger' : (order.elapsed_time > this.alertTime * 30 ? 'warning' : '');
        
        return `
            <div class="order-card status-${order.status.toLowerCase()} ${isRush ? 'priority-rush' : ''} ${isAlert ? 'alert' : ''}"
                 data-kot-id="${order.id}">
                ${order.is_additional ? '<span class="badge-additional">+ ADD</span>' : ''}
                
                <div class="card-header">
                    <div class="table-info">
                        <span class="table-number">${order.table_number || 'T/A'}</span>
                        <span class="order-type">${order.order_type}</span>
                    </div>
                    <div class="order-time">
                        <span class="elapsed-time ${elapsedClass}" data-start="${order.created_at}">
                            ${this.formatElapsedTime(order.elapsed_time)}
                        </span>
                        <span class="order-id">#${order.id.split('-').pop()}</span>
                    </div>
                </div>
                
                <div class="card-body">
                    ${order.items.map(item => `
                        <div class="order-item" data-item-id="${item.id}">
                            <span class="item-qty">${item.qty}</span>
                            <div class="item-details">
                                <div class="item-name">${item.name}</div>
                                ${item.modifiers?.length ? 
                                    `<div class="item-modifiers">${item.modifiers.map(m => m.label).join(', ')}</div>` : ''
                                }
                                ${item.notes ? 
                                    `<div class="item-notes"><i class="fa fa-comment"></i> ${item.notes}</div>` : ''
                                }
                            </div>
                            <span class="item-status ${item.status.toLowerCase()}">${item.status}</span>
                        </div>
                    `).join('')}
                </div>
                
                ${order.notes ? `
                    <div class="card-notes">
                        <i class="fa fa-exclamation-circle"></i>
                        ${order.notes}
                    </div>
                ` : ''}
                
                <div class="card-footer">
                    ${isNew ? `
                        <button class="btn-action btn-start" data-action="start" data-kot-id="${order.id}">
                            <i class="fa fa-play"></i> Start
                        </button>
                    ` : ''}
                    ${isPreparing ? `
                        <button class="btn-action btn-ready" data-action="ready" data-kot-id="${order.id}">
                            <i class="fa fa-check"></i> Ready
                        </button>
                    ` : ''}
                    ${isReady ? `
                        <button class="btn-action btn-bump" data-action="bump" data-kot-id="${order.id}">
                            <i class="fa fa-arrow-right"></i> Bump
                        </button>
                    ` : ''}
                    <button class="btn-action btn-priority ${isRush ? 'active' : ''}" 
                            data-action="priority" data-kot-id="${order.id}"
                            title="Toggle Rush">
                        <i class="fa fa-bolt"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    formatElapsedTime(seconds) {
        if (!seconds || seconds < 0) seconds = 0;
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    updateElapsedTimes() {
        document.querySelectorAll('.elapsed-time').forEach(el => {
            const startStr = el.dataset.start;
            if (!startStr) return;
            
            const start = new Date(startStr);
            const now = new Date();
            const elapsed = Math.floor((now - start) / 1000);
            
            el.textContent = this.formatElapsedTime(elapsed);
            
            // Update class based on elapsed time
            el.classList.remove('warning', 'danger');
            if (elapsed > this.alertTime * 60) {
                el.classList.add('danger');
            } else if (elapsed > this.alertTime * 30) {
                el.classList.add('warning');
            }
        });
    }
    
    updateStats() {
        const newCount = this.orders.filter(o => o.status === 'New').length;
        const preparingCount = this.orders.filter(o => o.status === 'Preparing').length;
        const readyCount = this.orders.filter(o => o.status === 'Ready').length;
        
        document.getElementById('stat-new').textContent = newCount;
        document.getElementById('stat-preparing').textContent = preparingCount;
        document.getElementById('stat-ready').textContent = readyCount;
    }
    
    async updateOrderStatus(kotId, status) {
        try {
            const response = await frappe.call({
                method: 'restaurant_pos.api.kitchen.update_order_status',
                args: {
                    kot_id: kotId,
                    status: status
                }
            });
            
            if (response.message?.success) {
                // Refresh orders
                await this.loadOrders();
            }
        } catch (error) {
            console.error('Failed to update order status:', error);
        }
    }
    
    async bumpOrder(kotId) {
        try {
            const response = await frappe.call({
                method: 'restaurant_pos.api.kitchen.bump_order',
                args: { kot_id: kotId }
            });
            
            if (response.message?.success) {
                // Remove from display
                await this.loadOrders();
            }
        } catch (error) {
            console.error('Failed to bump order:', error);
        }
    }
    
    async togglePriority(kotId) {
        const order = this.orders.find(o => o.id === kotId);
        if (!order) return;
        
        const newPriority = order.priority === 'Rush' ? 'Normal' : 'Rush';
        
        try {
            const response = await frappe.call({
                method: 'restaurant_pos.api.kitchen.set_priority',
                args: {
                    kot_id: kotId,
                    priority: newPriority
                }
            });
            
            if (response.message?.success) {
                await this.loadOrders();
            }
        } catch (error) {
            console.error('Failed to set priority:', error);
        }
    }
    
    playSound(type) {
        if (!this.soundEnabled) return;
        
        const audio = document.getElementById(type === 'new' ? 'sound-new-order' : 'sound-alert');
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(() => {});
        }
    }
    
    setupEventListeners() {
        // Action buttons
        document.getElementById('orders-grid').addEventListener('click', async (e) => {
            const btn = e.target.closest('.btn-action');
            if (!btn) return;
            
            const action = btn.dataset.action;
            const kotId = btn.dataset.kotId;
            
            btn.disabled = true;
            btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';
            
            try {
                switch (action) {
                    case 'start':
                        await this.updateOrderStatus(kotId, 'Preparing');
                        break;
                    case 'ready':
                        await this.updateOrderStatus(kotId, 'Ready');
                        break;
                    case 'bump':
                        await this.bumpOrder(kotId);
                        break;
                    case 'priority':
                        await this.togglePriority(kotId);
                        break;
                }
            } finally {
                // Re-enable button (it will be replaced on refresh anyway)
            }
        });
        
        // Fullscreen toggle
        document.getElementById('btn-fullscreen').addEventListener('click', () => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                document.documentElement.requestFullscreen();
            }
        });
        
        // Settings (could open a modal)
        document.getElementById('btn-settings')?.addEventListener('click', () => {
            // Toggle sound for now
            this.soundEnabled = !this.soundEnabled;
            alert(`Sound ${this.soundEnabled ? 'enabled' : 'disabled'}`);
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // R - Refresh
            if (e.key === 'r' || e.key === 'R') {
                this.loadOrders();
            }
            // F - Fullscreen
            if (e.key === 'f' || e.key === 'F') {
                document.getElementById('btn-fullscreen').click();
            }
        });
    }
    
    setupRealtime() {
        // Join kitchen room
        const room = this.station 
            ? `kitchen:${this.station}` 
            : `kitchen:${this.branch}`;
        
        frappe.realtime.on('restaurant:kot_update', (data) => {
            console.log('KOT Update:', data);
            this.loadOrders();
        });
        
        frappe.realtime.on('restaurant:new_order', (data) => {
            console.log('New Order:', data);
            this.playSound('new');
            this.loadOrders();
        });
        
        frappe.realtime.on('restaurant:kot_priority', (data) => {
            if (data.priority === 'Rush') {
                this.playSound('alert');
            }
            this.loadOrders();
        });
        
        frappe.realtime.on('restaurant:kot_recall', (data) => {
            this.playSound('alert');
            this.loadOrders();
        });
    }
    
    startAutoRefresh() {
        setInterval(() => {
            this.loadOrders();
        }, this.refreshInterval);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.kds = new KitchenDisplay();
});
