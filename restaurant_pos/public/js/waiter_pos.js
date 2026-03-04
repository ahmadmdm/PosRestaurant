/**
 * Waiter POS JavaScript
 * Mobile-friendly POS interface for restaurant waiters
 */

(function() {
    'use strict';
    
    // State
    const State = {
        tables: [],
        orders: [],
        calls: [],
        categories: [],
        items: [],
        cart: [],
        settings: {},
        currentTable: null,
        currentItem: null,
        modifierSelections: {},
        itemQty: 1
    };
    
    // DOM cache
    const DOM = {};
    
    // Initialize
    function init() {
        cacheDOMElements();
        bindEvents();
        loadData();
    }
    
    function cacheDOMElements() {
        DOM.waiterName = document.getElementById('waiter-name');
        DOM.notificationBadge = document.getElementById('notification-badge');
        DOM.ordersBadge = document.getElementById('orders-badge');
        DOM.callsBadge = document.getElementById('calls-badge');
        
        DOM.tablesView = document.getElementById('tables-view');
        DOM.ordersView = document.getElementById('orders-view');
        DOM.callsView = document.getElementById('calls-view');
        DOM.tablesGrid = document.getElementById('tables-grid');
        DOM.ordersList = document.getElementById('waiter-orders-list');
        DOM.callsList = document.getElementById('calls-list');
        
        DOM.actionSheet = document.getElementById('table-action-sheet');
        DOM.quickOrderPanel = document.getElementById('quick-order-panel');
        DOM.cartPanel = document.getElementById('cart-panel');
        
        DOM.quickCategories = document.getElementById('quick-categories');
        DOM.quickItemsGrid = document.getElementById('quick-items-grid');
        DOM.quickCartBadge = document.getElementById('quick-cart-badge');
        DOM.cartSummaryBar = document.getElementById('cart-summary-bar');
        DOM.barCartCount = document.getElementById('bar-cart-count');
        DOM.barCartTotal = document.getElementById('bar-cart-total');
        
        DOM.waiterCartItems = document.getElementById('waiter-cart-items');
        DOM.waiterSubtotal = document.getElementById('waiter-subtotal');
        DOM.waiterService = document.getElementById('waiter-service');
        DOM.waiterVat = document.getElementById('waiter-vat');
        DOM.waiterTotal = document.getElementById('waiter-total');
        
        DOM.toastContainer = document.getElementById('toast-container');
        DOM.loadingOverlay = document.getElementById('loading-overlay');
    }
    
    function bindEvents() {
        // View switching
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', () => switchView(btn.dataset.view));
        });
        
        // Table filter
        document.querySelectorAll('#tables-view .filter-tab').forEach(tab => {
            tab.addEventListener('click', () => filterTables(tab.dataset.filter));
        });
        
        // Order filter
        document.querySelectorAll('#orders-view .filter-tab').forEach(tab => {
            tab.addEventListener('click', () => filterOrders(tab.dataset.status));
        });
        
        // Back button
        document.getElementById('btn-back').addEventListener('click', goBack);
        
        // Refresh
        document.getElementById('btn-refresh').addEventListener('click', loadData);
        
        // Notifications
        document.getElementById('btn-notifications').addEventListener('click', () => switchView('calls'));
        
        // Table grid click
        DOM.tablesGrid.addEventListener('click', handleTableClick);
        
        // Order click
        DOM.ordersList.addEventListener('click', handleOrderClick);
        
        // Call respond
        DOM.callsList.addEventListener('click', handleCallClick);
        
        // Action sheet
        document.getElementById('close-action-sheet').addEventListener('click', closeActionSheet);
        document.querySelector('#table-action-sheet .sheet-overlay').addEventListener('click', closeActionSheet);
        document.getElementById('btn-new-order').addEventListener('click', startNewOrder);
        document.getElementById('btn-view-order').addEventListener('click', viewCurrentOrder);
        document.getElementById('btn-add-items').addEventListener('click', addMoreItems);
        document.getElementById('btn-request-bill').addEventListener('click', requestBill);
        
        // Quick order panel
        document.getElementById('close-quick-order').addEventListener('click', closeQuickOrder);
        document.getElementById('btn-show-cart').addEventListener('click', openCartPanel);
        DOM.quickCategories.addEventListener('click', handleCategoryClick);
        DOM.quickItemsGrid.addEventListener('click', handleItemClick);
        document.getElementById('quick-search').addEventListener('input', debounce(filterItems, 300));
        document.getElementById('btn-send-order').addEventListener('click', submitOrder);
        
        // Cart panel
        document.getElementById('close-cart-panel').addEventListener('click', closeCartPanel);
        document.getElementById('btn-clear-waiter-cart').addEventListener('click', clearCart);
        document.getElementById('btn-submit-waiter-order').addEventListener('click', submitOrder);
        document.getElementById('btn-hold-waiter-order').addEventListener('click', holdOrder);
        DOM.waiterCartItems.addEventListener('click', handleCartAction);
        
        // Item modal
        document.getElementById('close-waiter-item-modal').addEventListener('click', closeItemModal);
        document.getElementById('cancel-waiter-item').addEventListener('click', closeItemModal);
        document.getElementById('add-waiter-item').addEventListener('click', addItemToCart);
        document.getElementById('waiter-qty-minus').addEventListener('click', () => changeItemQty(-1));
        document.getElementById('waiter-qty-plus').addEventListener('click', () => changeItemQty(1));
        
        // Order detail modal
        document.getElementById('close-order-detail').addEventListener('click', closeOrderDetail);
        document.getElementById('btn-add-more-items').addEventListener('click', addMoreItems);
        document.getElementById('btn-mark-served').addEventListener('click', markOrderServed);
    }
    
    // Load data from server
    function loadData() {
        showLoading();
        
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.get_waiter_data',
            callback: function(r) {
                hideLoading();
                
                if (r.message && r.message.success) {
                    const data = r.message.data;
                    
                    State.tables = data.tables || [];
                    State.orders = data.orders || [];
                    State.calls = data.calls || [];
                    State.categories = data.categories || [];
                    State.items = data.items || [];
                    State.settings = data.settings || {};
                    
                    DOM.waiterName.textContent = data.waiter_name || '';
                    
                    renderTables();
                    renderOrders();
                    renderCalls();
                    updateBadges();
                } else {
                    showToast(__('Error loading data'), 'error');
                }
            },
            error: function() {
                hideLoading();
                showToast(__('Connection error'), 'error');
            }
        });
    }
    
    // Render tables
    function renderTables() {
        if (State.tables.length === 0) {
            DOM.tablesGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fa fa-chair"></i>
                    <p>${__('No tables available')}</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        State.tables.forEach(table => {
            const hasOrder = table.current_order;
            const needsAttention = table.status === 'Occupied' && table.current_order?.status === 'Ready';
            
            let statusClass = table.status.toLowerCase().replace(' ', '-');
            if (needsAttention) statusClass = 'needs-attention';
            
            html += `
                <div class="table-tile ${statusClass}" data-table="${table.name}">
                    <i class="fa fa-utensils table-icon"></i>
                    <div class="table-num">${table.table_number}</div>
                    <div class="table-guests"><i class="fa fa-users"></i> ${table.capacity}</div>
                    ${hasOrder ? `<div class="table-amount">${formatCurrency(table.current_order.grand_total)}</div>` : ''}
                    ${hasOrder ? `<div class="table-time">${getTimeAgo(table.current_order.creation)}</div>` : ''}
                </div>
            `;
        });
        
        DOM.tablesGrid.innerHTML = html;
    }
    
    // Render orders
    function renderOrders() {
        if (State.orders.length === 0) {
            DOM.ordersList.innerHTML = `
                <div class="empty-state">
                    <i class="fa fa-clipboard-list"></i>
                    <p>${__('No orders yet')}</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        State.orders.forEach(order => {
            html += `
                <div class="order-card" data-order="${order.name}">
                    <div class="order-top">
                        <div class="order-info">
                            <h4>#${order.name}</h4>
                            <div class="order-table">
                                <i class="fa fa-chair"></i>
                                ${order.table_number ? __('Table') + ' ' + order.table_number : order.order_type}
                            </div>
                        </div>
                        <span class="status-badge ${order.status.toLowerCase()}">${order.status}</span>
                    </div>
                    <div class="order-bottom">
                        <span class="order-time">
                            <i class="fa fa-clock"></i>
                            ${getTimeAgo(order.creation)}
                        </span>
                        <span class="order-amount">${formatCurrency(order.grand_total)}</span>
                    </div>
                </div>
            `;
        });
        
        DOM.ordersList.innerHTML = html;
    }
    
    // Render calls
    function renderCalls() {
        if (State.calls.length === 0) {
            DOM.callsList.innerHTML = `
                <div class="empty-state">
                    <i class="fa fa-bell"></i>
                    <p>${__('No pending calls')}</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        State.calls.forEach(call => {
            html += `
                <div class="call-card" data-call="${call.name}">
                    <div class="call-icon">
                        <i class="fa fa-bell"></i>
                    </div>
                    <div class="call-info">
                        <div class="call-table">${__('Table')} ${call.table_number}</div>
                        <div class="call-type">${call.call_type || __('Customer needs assistance')}</div>
                        <div class="call-time">${getTimeAgo(call.creation)}</div>
                    </div>
                    <button class="btn-respond">${__('Respond')}</button>
                </div>
            `;
        });
        
        DOM.callsList.innerHTML = html;
    }
    
    // Update badges
    function updateBadges() {
        const activeOrders = State.orders.filter(o => !['Paid', 'Completed', 'Cancelled'].includes(o.status)).length;
        const pendingCalls = State.calls.length;
        
        DOM.ordersBadge.textContent = activeOrders;
        DOM.callsBadge.textContent = pendingCalls;
        DOM.notificationBadge.textContent = pendingCalls;
        
        DOM.callsBadge.style.display = pendingCalls > 0 ? 'inline' : 'none';
        DOM.notificationBadge.style.display = pendingCalls > 0 ? 'inline' : 'none';
    }
    
    // Switch view
    function switchView(view) {
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        
        DOM.tablesView.style.display = view === 'tables' ? 'block' : 'none';
        DOM.ordersView.style.display = view === 'orders' ? 'block' : 'none';
        DOM.callsView.style.display = view === 'calls' ? 'block' : 'none';
    }
    
    // Filter tables
    function filterTables(filter) {
        document.querySelectorAll('#tables-view .filter-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.filter === filter);
        });
        
        // TODO: Implement actual filtering by waiter assignment
        renderTables();
    }
    
    // Filter orders
    function filterOrders(status) {
        document.querySelectorAll('#orders-view .filter-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.status === status);
        });
        
        // TODO: Filter orders by status
        renderOrders();
    }
    
    // Handle table click
    function handleTableClick(e) {
        const tile = e.target.closest('.table-tile');
        if (!tile) return;
        
        const tableName = tile.dataset.table;
        const table = State.tables.find(t => t.name === tableName);
        if (!table) return;
        
        State.currentTable = table;
        openActionSheet(table);
    }
    
    // Open action sheet
    function openActionSheet(table) {
        document.getElementById('sheet-table-name').textContent = __('Table') + ' #' + table.table_number;
        
        const statusText = {
            'Available': __('Available'),
            'Occupied': __('Occupied'),
            'Reserved': __('Reserved')
        };
        
        const statusEl = document.getElementById('sheet-table-status');
        statusEl.textContent = statusText[table.status] || table.status;
        statusEl.className = 'table-status ' + table.status.toLowerCase();
        
        // Show/hide buttons based on table status
        const hasOrder = table.current_order;
        document.getElementById('btn-new-order').style.display = table.status === 'Available' ? 'flex' : 'none';
        document.getElementById('btn-view-order').style.display = hasOrder ? 'flex' : 'none';
        document.getElementById('btn-add-items').style.display = hasOrder ? 'flex' : 'none';
        document.getElementById('btn-request-bill').style.display = hasOrder ? 'flex' : 'none';
        document.getElementById('btn-transfer-table').style.display = hasOrder ? 'flex' : 'none';
        
        // Update info
        if (hasOrder) {
            document.getElementById('sheet-guests').textContent = table.current_order.guest_count || '-';
            document.getElementById('sheet-time').textContent = getTimeAgo(table.current_order.creation);
            document.getElementById('sheet-total').textContent = formatCurrency(table.current_order.grand_total);
        } else {
            document.getElementById('sheet-guests').textContent = '-';
            document.getElementById('sheet-time').textContent = '-';
            document.getElementById('sheet-total').textContent = '0.00';
        }
        
        DOM.actionSheet.classList.add('show');
    }
    
    function closeActionSheet() {
        DOM.actionSheet.classList.remove('show');
    }
    
    // Start new order
    function startNewOrder() {
        closeActionSheet();
        State.cart = [];
        openQuickOrderPanel();
    }
    
    // View current order
    function viewCurrentOrder() {
        closeActionSheet();
        if (State.currentTable?.current_order) {
            openOrderDetail(State.currentTable.current_order.name);
        }
    }
    
    // Add more items
    function addMoreItems() {
        closeActionSheet();
        closeOrderDetail();
        openQuickOrderPanel();
    }
    
    // Request bill
    function requestBill() {
        // TODO: Implement bill request
        closeActionSheet();
        showToast(__('Bill requested'), 'success');
    }
    
    // Open quick order panel
    function openQuickOrderPanel() {
        document.getElementById('quick-order-table').textContent = 
            __('Table') + ' #' + (State.currentTable?.table_number || '-');
        
        renderQuickCategories();
        renderQuickItems();
        updateCartBar();
        
        DOM.quickOrderPanel.classList.add('show');
    }
    
    function closeQuickOrder() {
        if (State.cart.length > 0) {
            if (!confirm(__('Discard order?'))) return;
        }
        State.cart = [];
        DOM.quickOrderPanel.classList.remove('show');
    }
    
    // Render quick categories
    function renderQuickCategories() {
        let html = `
            <button class="cat-btn active" data-category="all">
                <span class="cat-icon"><i class="fa fa-th"></i></span>
                <span class="cat-name">${__('All')}</span>
            </button>
        `;
        
        State.categories.forEach(cat => {
            html += `
                <button class="cat-btn" data-category="${cat.name}">
                    <span class="cat-icon">${cat.icon ? `<i class="${cat.icon}"></i>` : '<i class="fa fa-folder"></i>'}</span>
                    <span class="cat-name">${cat.category_name_ar || cat.category_name}</span>
                </button>
            `;
        });
        
        DOM.quickCategories.innerHTML = html;
    }
    
    // Render quick items
    function renderQuickItems(items = null) {
        const itemsToRender = items || State.items;
        
        if (itemsToRender.length === 0) {
            DOM.quickItemsGrid.innerHTML = `
                <div class="empty-state" style="grid-column: span 3;">
                    <i class="fa fa-search"></i>
                    <p>${__('No items found')}</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        itemsToRender.forEach(item => {
            const price = item.discounted_price || item.price;
            
            html += `
                <div class="quick-item" data-item="${item.name}">
                    ${item.thumbnail || item.image ? 
                        `<img src="${item.thumbnail || item.image}" class="quick-item-image" alt="">` :
                        `<div class="quick-item-image" style="display:flex;align-items:center;justify-content:center;color:#ccc;font-size:1.5rem;"><i class="fa fa-utensils"></i></div>`
                    }
                    <div class="quick-item-info">
                        <div class="quick-item-name">${item.item_name_ar || item.item_name}</div>
                        <div class="quick-item-price">${formatCurrency(price)}</div>
                    </div>
                </div>
            `;
        });
        
        DOM.quickItemsGrid.innerHTML = html;
    }
    
    // Handle category click
    function handleCategoryClick(e) {
        const btn = e.target.closest('.cat-btn');
        if (!btn) return;
        
        document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        const category = btn.dataset.category;
        if (category === 'all') {
            renderQuickItems();
        } else {
            const filtered = State.items.filter(i => i.category === category);
            renderQuickItems(filtered);
        }
    }
    
    // Filter items by search
    function filterItems() {
        const search = document.getElementById('quick-search').value.toLowerCase().trim();
        
        if (!search) {
            renderQuickItems();
            return;
        }
        
        const filtered = State.items.filter(item => 
            (item.item_name || '').toLowerCase().includes(search) ||
            (item.item_name_ar || '').toLowerCase().includes(search) ||
            (item.item_code || '').toLowerCase().includes(search)
        );
        
        renderQuickItems(filtered);
    }
    
    // Handle item click
    function handleItemClick(e) {
        const card = e.target.closest('.quick-item');
        if (!card) return;
        
        const itemName = card.dataset.item;
        const item = State.items.find(i => i.name === itemName);
        if (!item) return;
        
        if (item.allow_customization && item.modifiers && item.modifiers.length > 0) {
            openItemModal(item);
        } else {
            // Add directly to cart
            addToCart({
                menu_item: item.name,
                item_name: item.item_name,
                item_name_ar: item.item_name_ar,
                rate: item.discounted_price || item.price,
                qty: 1,
                modifiers: [],
                note: '',
                kitchen_station: item.kitchen_station,
                total: item.discounted_price || item.price
            });
        }
    }
    
    // Open item modal for customization
    function openItemModal(item) {
        State.currentItem = item;
        State.modifierSelections = {};
        State.itemQty = 1;
        
        document.getElementById('waiter-modal-item-name').textContent = item.item_name_ar || item.item_name;
        document.getElementById('waiter-modal-item-price').textContent = formatCurrency(item.discounted_price || item.price);
        document.getElementById('waiter-qty').textContent = '1';
        document.getElementById('waiter-item-notes').value = '';
        
        // Set image
        const imageEl = document.getElementById('waiter-modal-item-image');
        if (item.image) {
            imageEl.style.backgroundImage = `url(${item.image})`;
        } else {
            imageEl.style.backgroundImage = 'none';
        }
        
        // Render modifiers
        let modHtml = '';
        if (item.modifiers && item.modifiers.length > 0) {
            item.modifiers.forEach(mod => {
                modHtml += `
                    <div class="modifier-group" data-modifier="${mod.name}">
                        <div class="modifier-title">
                            ${mod.title_ar || mod.title}
                            ${mod.required ? '<span class="required-badge">*</span>' : ''}
                        </div>
                        <div class="modifier-options" data-type="${mod.type}">
                            ${mod.options.map(opt => `
                                <button class="mod-option" data-option="${opt.name}" data-price="${opt.price || 0}">
                                    ${opt.name_ar || opt.name}
                                    ${opt.price ? ` (+${formatCurrency(opt.price)})` : ''}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `;
            });
        }
        
        document.getElementById('waiter-modifiers').innerHTML = modHtml;
        
        // Bind modifier clicks
        document.querySelectorAll('#waiter-modifiers .mod-option').forEach(btn => {
            btn.addEventListener('click', () => toggleModifier(btn));
        });
        
        updateItemTotal();
        document.getElementById('waiter-item-modal').classList.add('show');
    }
    
    function closeItemModal() {
        document.getElementById('waiter-item-modal').classList.remove('show');
    }
    
    // Toggle modifier
    function toggleModifier(btn) {
        const group = btn.closest('.modifier-group');
        const modifierName = group.dataset.modifier;
        const optionsContainer = group.querySelector('.modifier-options');
        const isSingle = optionsContainer.dataset.type === 'Single';
        
        if (isSingle) {
            group.querySelectorAll('.mod-option').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            State.modifierSelections[modifierName] = [{
                name: btn.dataset.option,
                price: parseFloat(btn.dataset.price) || 0
            }];
        } else {
            btn.classList.toggle('selected');
            
            if (!State.modifierSelections[modifierName]) {
                State.modifierSelections[modifierName] = [];
            }
            
            if (btn.classList.contains('selected')) {
                State.modifierSelections[modifierName].push({
                    name: btn.dataset.option,
                    price: parseFloat(btn.dataset.price) || 0
                });
            } else {
                State.modifierSelections[modifierName] = State.modifierSelections[modifierName]
                    .filter(o => o.name !== btn.dataset.option);
            }
        }
        
        updateItemTotal();
    }
    
    // Change item qty
    function changeItemQty(delta) {
        State.itemQty = Math.max(1, State.itemQty + delta);
        document.getElementById('waiter-qty').textContent = State.itemQty;
        updateItemTotal();
    }
    
    // Update item total
    function updateItemTotal() {
        const item = State.currentItem;
        if (!item) return;
        
        let basePrice = item.discounted_price || item.price;
        let modifiersPrice = 0;
        
        Object.values(State.modifierSelections).forEach(options => {
            options.forEach(opt => {
                modifiersPrice += opt.price || 0;
            });
        });
        
        const total = (basePrice + modifiersPrice) * State.itemQty;
        document.getElementById('waiter-item-total').textContent = formatCurrency(total);
    }
    
    // Add item to cart
    function addItemToCart() {
        const item = State.currentItem;
        if (!item) return;
        
        // Check required modifiers
        if (item.modifiers) {
            for (const mod of item.modifiers) {
                if (mod.required && !State.modifierSelections[mod.name]?.length) {
                    showToast(__('Please select') + ' ' + (mod.title_ar || mod.title), 'warning');
                    return;
                }
            }
        }
        
        // Calculate total
        let basePrice = item.discounted_price || item.price;
        let modifiersPrice = 0;
        const modifiers = [];
        
        Object.entries(State.modifierSelections).forEach(([modName, options]) => {
            options.forEach(opt => {
                modifiersPrice += opt.price || 0;
                modifiers.push({
                    modifier: modName,
                    option: opt.name,
                    price: opt.price
                });
            });
        });
        
        const total = (basePrice + modifiersPrice) * State.itemQty;
        
        addToCart({
            menu_item: item.name,
            item_name: item.item_name,
            item_name_ar: item.item_name_ar,
            rate: basePrice + modifiersPrice,
            qty: State.itemQty,
            modifiers: modifiers,
            note: document.getElementById('waiter-item-notes').value,
            kitchen_station: item.kitchen_station,
            total: total
        });
        
        closeItemModal();
    }
    
    // Add to cart
    function addToCart(item) {
        // Check if similar item exists
        const existingIndex = State.cart.findIndex(ci => 
            ci.menu_item === item.menu_item && 
            JSON.stringify(ci.modifiers) === JSON.stringify(item.modifiers) &&
            ci.note === item.note
        );
        
        if (existingIndex > -1) {
            State.cart[existingIndex].qty += item.qty;
            State.cart[existingIndex].total = State.cart[existingIndex].rate * State.cart[existingIndex].qty;
        } else {
            item.id = Date.now();
            State.cart.push(item);
        }
        
        updateCartBar();
        showToast(__('Added to cart'), 'success');
    }
    
    // Update cart bar
    function updateCartBar() {
        const itemCount = State.cart.reduce((sum, item) => sum + item.qty, 0);
        const total = State.cart.reduce((sum, item) => sum + item.total, 0);
        
        DOM.quickCartBadge.textContent = itemCount;
        DOM.barCartCount.textContent = itemCount + ' ' + __('items');
        DOM.barCartTotal.textContent = formatCurrency(total);
        
        DOM.cartSummaryBar.style.display = itemCount > 0 ? 'flex' : 'none';
    }
    
    // Open cart panel
    function openCartPanel() {
        renderCartItems();
        updateCartTotals();
        DOM.cartPanel.classList.add('show');
    }
    
    function closeCartPanel() {
        DOM.cartPanel.classList.remove('show');
    }
    
    // Render cart items
    function renderCartItems() {
        if (State.cart.length === 0) {
            DOM.waiterCartItems.innerHTML = `
                <div class="empty-state">
                    <i class="fa fa-shopping-cart"></i>
                    <p>${__('Cart is empty')}</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        State.cart.forEach((item, index) => {
            const modsText = item.modifiers.map(m => m.option).join(', ');
            
            html += `
                <div class="cart-item" data-index="${index}">
                    <div class="cart-item-details">
                        <div class="cart-item-name">${item.item_name_ar || item.item_name}</div>
                        ${modsText ? `<div class="cart-item-mods">${modsText}</div>` : ''}
                        ${item.note ? `<div class="cart-item-mods">${item.note}</div>` : ''}
                        <div class="cart-item-price">${formatCurrency(item.total)}</div>
                    </div>
                    <div class="cart-item-qty">
                        <button data-action="decrease"><i class="fa fa-minus"></i></button>
                        <span>${item.qty}</span>
                        <button data-action="increase"><i class="fa fa-plus"></i></button>
                    </div>
                    <button class="cart-item-remove" data-action="remove">
                        <i class="fa fa-trash"></i>
                    </button>
                </div>
            `;
        });
        
        DOM.waiterCartItems.innerHTML = html;
    }
    
    // Update cart totals
    function updateCartTotals() {
        const subtotal = State.cart.reduce((sum, item) => sum + item.total, 0);
        const servicePercent = State.settings.service_charge_percent || 0;
        const vatPercent = State.settings.vat_percent || 15;
        
        const service = subtotal * servicePercent / 100;
        const vat = (subtotal + service) * vatPercent / 100;
        const total = subtotal + service + vat;
        
        DOM.waiterSubtotal.textContent = formatCurrency(subtotal);
        DOM.waiterService.textContent = formatCurrency(service);
        DOM.waiterVat.textContent = formatCurrency(vat);
        DOM.waiterTotal.textContent = formatCurrency(total);
    }
    
    // Handle cart action
    function handleCartAction(e) {
        const btn = e.target.closest('button');
        if (!btn) return;
        
        const cartItem = btn.closest('.cart-item');
        if (!cartItem) return;
        
        const index = parseInt(cartItem.dataset.index);
        const action = btn.dataset.action;
        
        if (action === 'increase') {
            State.cart[index].qty++;
            State.cart[index].total = State.cart[index].rate * State.cart[index].qty;
        } else if (action === 'decrease') {
            if (State.cart[index].qty > 1) {
                State.cart[index].qty--;
                State.cart[index].total = State.cart[index].rate * State.cart[index].qty;
            } else {
                State.cart.splice(index, 1);
            }
        } else if (action === 'remove') {
            State.cart.splice(index, 1);
        }
        
        renderCartItems();
        updateCartTotals();
        updateCartBar();
    }
    
    // Clear cart
    function clearCart() {
        if (State.cart.length === 0) return;
        
        if (confirm(__('Clear all items?'))) {
            State.cart = [];
            renderCartItems();
            updateCartTotals();
            updateCartBar();
        }
    }
    
    // Hold order
    function holdOrder() {
        // TODO: Implement hold functionality
        showToast(__('Order held'), 'success');
        closeCartPanel();
        closeQuickOrder();
    }
    
    // Submit order
    function submitOrder() {
        if (State.cart.length === 0) {
            showToast(__('Cart is empty'), 'warning');
            return;
        }
        
        showLoading();
        
        const notes = document.getElementById('waiter-order-notes')?.value || '';
        
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.create_order',
            args: {
                order_data: {
                    order_type: 'Dine In',
                    table: State.currentTable?.name,
                    guest_count: 1,
                    items: State.cart,
                    notes: notes
                }
            },
            callback: function(r) {
                hideLoading();
                
                if (r.message && r.message.success) {
                    showToast(__('Order submitted!'), 'success');
                    State.cart = [];
                    closeCartPanel();
                    closeQuickOrder();
                    loadData();
                } else {
                    showToast(r.message?.message || __('Error submitting order'), 'error');
                }
            },
            error: function() {
                hideLoading();
                showToast(__('Connection error'), 'error');
            }
        });
    }
    
    // Handle order click
    function handleOrderClick(e) {
        const card = e.target.closest('.order-card');
        if (!card) return;
        
        openOrderDetail(card.dataset.order);
    }
    
    // Open order detail
    function openOrderDetail(orderId) {
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.get_order_details',
            args: { order_id: orderId },
            callback: function(r) {
                if (r.message && r.message.success) {
                    const order = r.message.order;
                    
                    document.getElementById('detail-order-id').textContent = order.name;
                    document.getElementById('detail-order-status').textContent = order.status;
                    document.getElementById('detail-order-status').className = 'order-status-badge ' + order.status.toLowerCase();
                    
                    document.getElementById('detail-table').textContent = 
                        order.table_number ? __('Table') + ' ' + order.table_number : order.order_type;
                    document.getElementById('detail-time').textContent = getTimeAgo(order.creation);
                    document.getElementById('detail-guests').textContent = order.guest_count + ' ' + __('guests');
                    
                    // Items
                    let itemsHtml = '';
                    order.items.forEach(item => {
                        const modsText = item.modifiers?.map(m => m.option).join(', ') || '';
                        itemsHtml += `
                            <div class="detail-item">
                                <div>
                                    <div class="detail-item-name">${item.qty}x ${item.item_name_ar || item.item_name}</div>
                                    ${modsText ? `<div class="detail-item-mods">${modsText}</div>` : ''}
                                </div>
                                <div>${formatCurrency(item.amount)}</div>
                            </div>
                        `;
                    });
                    document.getElementById('detail-items').innerHTML = itemsHtml;
                    
                    // Totals
                    document.getElementById('detail-subtotal').textContent = formatCurrency(order.subtotal);
                    document.getElementById('detail-service').textContent = formatCurrency(order.service_charge);
                    document.getElementById('detail-vat').textContent = formatCurrency(order.tax_amount);
                    document.getElementById('detail-total').textContent = formatCurrency(order.grand_total);
                    
                    // Store for later use
                    State.currentOrderDetail = order;
                    
                    document.getElementById('order-detail-modal').classList.add('show');
                }
            }
        });
    }
    
    function closeOrderDetail() {
        document.getElementById('order-detail-modal').classList.remove('show');
    }
    
    // Mark order served
    function markOrderServed() {
        if (!State.currentOrderDetail) return;
        
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.update_order_status',
            args: {
                order_id: State.currentOrderDetail.name,
                status: 'Served'
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    showToast(__('Order marked as served'), 'success');
                    closeOrderDetail();
                    loadData();
                } else {
                    showToast(r.message?.message || __('Error updating order'), 'error');
                }
            }
        });
    }
    
    // Handle call click
    function handleCallClick(e) {
        const btn = e.target.closest('.btn-respond');
        if (!btn) return;
        
        const card = btn.closest('.call-card');
        if (!card) return;
        
        respondToCall(card.dataset.call);
    }
    
    // Respond to call
    function respondToCall(callId) {
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.respond_to_call',
            args: {
                call_id: callId,
                response: 'completed'
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    showToast(__('Call responded'), 'success');
                    loadData();
                }
            }
        });
    }
    
    // Go back
    function goBack() {
        if (DOM.quickOrderPanel.classList.contains('show')) {
            closeQuickOrder();
        } else {
            window.history.back();
        }
    }
    
    // Utility functions
    function showLoading() {
        DOM.loadingOverlay.style.display = 'flex';
    }
    
    function hideLoading() {
        DOM.loadingOverlay.style.display = 'none';
    }
    
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fa fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}"></i>
            <span>${message}</span>
        `;
        
        DOM.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    function formatCurrency(amount) {
        return parseFloat(amount || 0).toFixed(2);
    }
    
    function getTimeAgo(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return __('Just now');
        if (diffMins < 60) return diffMins + 'm';
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return diffHours + 'h';
        
        return Math.floor(diffHours / 24) + 'd';
    }
    
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
    
    function __(text) {
        return frappe._ ? frappe._(text) : text;
    }
    
    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();
