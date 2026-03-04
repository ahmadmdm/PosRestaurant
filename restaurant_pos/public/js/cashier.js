/**
 * Cashier POS JavaScript
 * Full-featured POS interface for restaurant cashier
 */

(function() {
    'use strict';
    
    // POS State
    const POSState = {
        categories: [],
        items: [],
        tables: [],
        cart: [],
        orderType: 'Dine In',
        selectedTable: null,
        selectedCustomer: null,
        discount: null,
        settings: {},
        heldOrders: [],
        pendingOrders: [],
        currentItem: null,
        modifierSelections: {},
        modifierQty: 1,
        currentOrderId: null
    };
    
    // DOM Elements cache
    const DOM = {};
    
    // Initialize POS
    function init() {
        cacheDOMElements();
        bindEvents();
        loadPOSData();
        startClock();
        hideSplash();
    }
    
    // Cache DOM elements for performance
    function cacheDOMElements() {
        DOM.splash = document.getElementById('splash-screen');
        DOM.clock = document.getElementById('pos-clock');
        DOM.cashierName = document.getElementById('cashier-name');
        DOM.branchName = document.getElementById('branch-name');
        DOM.searchInput = document.getElementById('search-input');
        DOM.categoriesBar = document.getElementById('categories-bar');
        DOM.menuGrid = document.getElementById('menu-items-grid');
        DOM.noItems = document.getElementById('no-items');
        DOM.cartItems = document.getElementById('cart-items');
        DOM.cartEmpty = document.getElementById('cart-empty');
        DOM.cartItemCount = document.getElementById('cart-item-count');
        DOM.subtotal = document.getElementById('subtotal');
        DOM.discountAmount = document.getElementById('discount-amount');
        DOM.discountRow = document.getElementById('discount-row');
        DOM.serviceCharge = document.getElementById('service-charge');
        DOM.servicePercent = document.getElementById('service-percent');
        DOM.vatAmount = document.getElementById('vat-amount');
        DOM.vatPercent = document.getElementById('vat-percent');
        DOM.grandTotal = document.getElementById('grand-total');
        DOM.payAmount = document.getElementById('pay-amount');
        DOM.currency = document.getElementById('currency');
        DOM.btnSendKitchen = document.getElementById('btn-send-kitchen');
        DOM.btnPay = document.getElementById('btn-pay');
        DOM.btnClearCart = document.getElementById('btn-clear-cart');
        DOM.tableSelection = document.getElementById('table-selection');
        DOM.btnSelectTable = document.getElementById('btn-select-table');
        DOM.selectedTableText = document.getElementById('selected-table-text');
        DOM.guestCount = document.getElementById('guest-count');
        DOM.customerInfo = document.getElementById('customer-info');
        DOM.pendingCount = document.getElementById('pending-count');
        DOM.toastContainer = document.getElementById('toast-container');
        
        // Modals
        DOM.modifierModal = document.getElementById('modifier-modal');
        DOM.paymentModal = document.getElementById('payment-modal');
        DOM.customerModal = document.getElementById('customer-modal');
        DOM.tableModal = document.getElementById('table-modal');
        DOM.discountModal = document.getElementById('discount-modal');
        DOM.ordersPanel = document.getElementById('orders-panel');
    }
    
    // Bind event listeners
    function bindEvents() {
        // Order type tabs
        document.querySelectorAll('.order-type-tabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', () => selectOrderType(btn.dataset.type));
        });
        
        // Search
        DOM.searchInput.addEventListener('input', debounce(handleSearch, 300));
        document.getElementById('btn-clear-search').addEventListener('click', () => {
            DOM.searchInput.value = '';
            filterItems();
        });
        
        // Category selection
        DOM.categoriesBar.addEventListener('click', e => {
            const btn = e.target.closest('.category-btn');
            if (btn) selectCategory(btn.dataset.category);
        });
        
        // Menu items
        DOM.menuGrid.addEventListener('click', e => {
            const card = e.target.closest('.menu-item-card');
            if (card) handleItemClick(card.dataset.item);
        });
        
        // Cart actions
        DOM.btnClearCart.addEventListener('click', clearCart);
        DOM.cartItems.addEventListener('click', handleCartAction);
        
        // Table selection
        DOM.btnSelectTable.addEventListener('click', openTableModal);
        
        // Customer
        document.getElementById('btn-add-customer').addEventListener('click', openCustomerModal);
        
        // Action buttons
        document.getElementById('btn-discount').addEventListener('click', openDiscountModal);
        document.getElementById('btn-hold').addEventListener('click', holdOrder);
        document.getElementById('btn-note').addEventListener('click', addOrderNote);
        DOM.btnSendKitchen.addEventListener('click', sendToKitchen);
        DOM.btnPay.addEventListener('click', openPaymentModal);
        
        // Header actions
        document.getElementById('btn-orders').addEventListener('click', toggleOrdersPanel);
        document.getElementById('btn-tables').addEventListener('click', openTableModal);
        document.getElementById('btn-settings').addEventListener('click', openSettingsModal);
        document.getElementById('btn-exit').addEventListener('click', exitPOS);
        
        // Modal close buttons
        document.querySelectorAll('.modal .btn-close, .modal .btn-cancel').forEach(btn => {
            btn.addEventListener('click', () => closeAllModals());
        });
        
        // Modal overlays
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', closeAllModals);
        });
        
        // Modifier modal
        document.getElementById('confirm-modifier').addEventListener('click', confirmModifier);
        document.getElementById('mod-qty-minus').addEventListener('click', () => changeModifierQty(-1));
        document.getElementById('mod-qty-plus').addEventListener('click', () => changeModifierQty(1));
        
        // Payment modal
        bindPaymentEvents();
        
        // Customer modal
        document.getElementById('save-customer').addEventListener('click', saveCustomer);
        
        // Discount modal
        document.getElementById('apply-discount').addEventListener('click', applyDiscount);
        document.getElementById('remove-discount').addEventListener('click', removeDiscount);
        document.querySelectorAll('.discount-tab').forEach(tab => {
            tab.addEventListener('click', () => selectDiscountType(tab.dataset.type));
        });
        
        // Table modal
        document.getElementById('tables-grid').addEventListener('click', e => {
            const card = e.target.closest('.table-card');
            if (card && card.classList.contains('available')) {
                selectTable(card.dataset.table);
            }
        });
        
        // Orders panel
        document.getElementById('close-orders-panel').addEventListener('click', () => {
            DOM.ordersPanel.classList.remove('show');
        });
        document.querySelectorAll('#orders-panel .panel-tab').forEach(tab => {
            tab.addEventListener('click', () => filterOrders(tab.dataset.status));
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboard);
    }
    
    // Load POS data from server
    function loadPOSData() {
        console.log('Loading POS data...');
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.get_pos_data',
            callback: function(r) {
                console.log('POS data response:', r);
                console.log('r.message:', JSON.stringify(r.message, null, 2));
                if (r.message && r.message.success) {
                    const data = r.message.data;
                    console.log('Categories:', data.categories?.length, 'Items:', data.items?.length);
                    
                    POSState.categories = data.categories || [];
                    POSState.items = data.items || [];
                    POSState.tables = data.tables || [];
                    POSState.settings = data.settings || {};
                    
                    // Update UI
                    DOM.cashierName.textContent = data.cashier_name || '';
                    DOM.branchName.textContent = data.branch_name || '';
                    DOM.currency.textContent = data.settings.currency || 'SAR';
                    DOM.servicePercent.textContent = data.settings.service_charge_percent || 0;
                    DOM.vatPercent.textContent = data.settings.vat_percent || 15;
                    
                    renderCategories();
                    renderMenuItems();
                    loadPendingOrders();
                } else {
                    console.error('POS data error:', JSON.stringify(r.message, null, 2));
                    showToast(__('Error loading POS data'), 'error');
                }
            },
            error: function(e) {
                console.error('POS API error:', e);
                showToast(__('Connection error'), 'error');
            }
        });
    }
    
    // Render categories
    function renderCategories() {
        let html = `
            <button class="category-btn active" data-category="all">
                <i class="fa fa-th"></i>
                <span>${__('All')}</span>
            </button>
        `;
        
        POSState.categories.forEach(cat => {
            html += `
                <button class="category-btn" data-category="${cat.name}">
                    ${cat.icon ? `<i class="${cat.icon}"></i>` : '<i class="fa fa-folder"></i>'}
                    <span>${cat.category_name_ar || cat.category_name}</span>
                </button>
            `;
        });
        
        DOM.categoriesBar.innerHTML = html;
    }
    
    // Render menu items
    function renderMenuItems(items = null) {
        const itemsToRender = items || POSState.items;
        
        if (itemsToRender.length === 0) {
            DOM.menuGrid.innerHTML = '';
            DOM.noItems.style.display = 'block';
            return;
        }
        
        DOM.noItems.style.display = 'none';
        
        let html = '';
        itemsToRender.forEach(item => {
            const price = item.discounted_price || item.price;
            const hasDiscount = item.discounted_price && item.discounted_price < item.price;
            
            html += `
                <div class="menu-item-card ${item.is_sold_out ? 'item-sold-out' : ''}" 
                     data-item="${item.name}">
                    ${item.thumbnail || item.image ? 
                        `<img src="${item.thumbnail || item.image}" class="item-image" alt="${item.item_name}">` :
                        `<div class="item-image no-image"><i class="fa fa-utensils"></i></div>`
                    }
                    <div class="item-info">
                        <div class="item-name">${item.item_name_ar || item.item_name}</div>
                        <div class="item-price">
                            ${hasDiscount ? `<span class="old-price">${formatCurrency(item.price)}</span>` : ''}
                            ${formatCurrency(price)}
                        </div>
                    </div>
                    ${item.is_sold_out ? '<div class="sold-out-badge">' + __('Sold Out') + '</div>' : ''}
                </div>
            `;
        });
        
        DOM.menuGrid.innerHTML = html;
    }
    
    // Select order type
    function selectOrderType(type) {
        POSState.orderType = type;
        
        document.querySelectorAll('.order-type-tabs .tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });
        
        // Show/hide table selection
        DOM.tableSelection.style.display = type === 'Dine In' ? 'flex' : 'none';
        
        // Show delivery address field in customer modal
        const addressGroup = document.getElementById('delivery-address-group');
        if (addressGroup) {
            addressGroup.style.display = type === 'Delivery' ? 'block' : 'none';
        }
        
        // Clear table selection if not dine in
        if (type !== 'Dine In') {
            POSState.selectedTable = null;
            DOM.selectedTableText.textContent = __('Select Table');
            DOM.btnSelectTable.classList.remove('selected');
        }
    }
    
    // Select category
    function selectCategory(category) {
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.category === category);
        });
        
        filterItems(category);
    }
    
    // Filter items
    function filterItems(category = 'all') {
        const search = DOM.searchInput.value.toLowerCase().trim();
        
        let filtered = POSState.items;
        
        // Filter by category
        if (category && category !== 'all') {
            filtered = filtered.filter(item => item.category === category);
        }
        
        // Filter by search
        if (search) {
            filtered = filtered.filter(item => 
                (item.item_name || '').toLowerCase().includes(search) ||
                (item.item_name_ar || '').toLowerCase().includes(search) ||
                (item.item_code || '').toLowerCase().includes(search)
            );
        }
        
        renderMenuItems(filtered);
    }
    
    // Handle search
    function handleSearch() {
        const activeCategory = document.querySelector('.category-btn.active');
        filterItems(activeCategory ? activeCategory.dataset.category : 'all');
    }
    
    // Handle item click
    function handleItemClick(itemName) {
        const item = POSState.items.find(i => i.name === itemName);
        if (!item || item.is_sold_out) return;
        
        if (item.allow_customization && item.modifiers && item.modifiers.length > 0) {
            openModifierModal(item);
        } else {
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
    
    // Open modifier modal
    function openModifierModal(item) {
        POSState.currentItem = item;
        POSState.modifierSelections = {};
        POSState.modifierQty = 1;
        
        document.getElementById('modifier-item-name').textContent = item.item_name_ar || item.item_name;
        document.getElementById('mod-qty').textContent = '1';
        document.getElementById('item-note').value = '';
        
        // Render modifiers
        let html = '';
        item.modifiers.forEach(mod => {
            html += `
                <div class="modifier-group" data-modifier="${mod.name}">
                    <div class="modifier-title">
                        ${mod.title_ar || mod.title}
                        ${mod.required ? '<span class="modifier-required">*</span>' : ''}
                    </div>
                    <div class="modifier-options" data-type="${mod.type}">
                        ${mod.options.map(opt => `
                            <button class="modifier-option" 
                                    data-option="${opt.name}" 
                                    data-price="${opt.price || 0}">
                                ${opt.name_ar || opt.name}
                                ${opt.price ? `<span class="price">+${formatCurrency(opt.price)}</span>` : ''}
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        });
        
        document.getElementById('modifier-options').innerHTML = html;
        
        // Bind modifier selection
        document.querySelectorAll('.modifier-option').forEach(btn => {
            btn.addEventListener('click', () => toggleModifier(btn));
        });
        
        updateModifierTotal();
        showModal(DOM.modifierModal);
    }
    
    // Toggle modifier option
    function toggleModifier(btn) {
        const group = btn.closest('.modifier-group');
        const modifierName = group.dataset.modifier;
        const optionsContainer = group.querySelector('.modifier-options');
        const isSingle = optionsContainer.dataset.type === 'Single';
        
        if (isSingle) {
            // Single selection - clear others first
            group.querySelectorAll('.modifier-option').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            POSState.modifierSelections[modifierName] = [{
                name: btn.dataset.option,
                price: parseFloat(btn.dataset.price) || 0
            }];
        } else {
            // Multiple selection
            btn.classList.toggle('selected');
            
            if (!POSState.modifierSelections[modifierName]) {
                POSState.modifierSelections[modifierName] = [];
            }
            
            if (btn.classList.contains('selected')) {
                POSState.modifierSelections[modifierName].push({
                    name: btn.dataset.option,
                    price: parseFloat(btn.dataset.price) || 0
                });
            } else {
                POSState.modifierSelections[modifierName] = POSState.modifierSelections[modifierName]
                    .filter(o => o.name !== btn.dataset.option);
            }
        }
        
        updateModifierTotal();
    }
    
    // Change modifier quantity
    function changeModifierQty(delta) {
        POSState.modifierQty = Math.max(1, POSState.modifierQty + delta);
        document.getElementById('mod-qty').textContent = POSState.modifierQty;
        updateModifierTotal();
    }
    
    // Update modifier total
    function updateModifierTotal() {
        const item = POSState.currentItem;
        if (!item) return;
        
        let basePrice = item.discounted_price || item.price;
        let modifiersPrice = 0;
        
        Object.values(POSState.modifierSelections).forEach(options => {
            options.forEach(opt => {
                modifiersPrice += opt.price || 0;
            });
        });
        
        const total = (basePrice + modifiersPrice) * POSState.modifierQty;
        document.getElementById('modifier-total').textContent = formatCurrency(total);
    }
    
    // Confirm modifier and add to cart
    function confirmModifier() {
        const item = POSState.currentItem;
        if (!item) return;
        
        // Check required modifiers
        for (const mod of item.modifiers) {
            if (mod.required && !POSState.modifierSelections[mod.name]?.length) {
                showToast(__('Please select') + ' ' + (mod.title_ar || mod.title), 'warning');
                return;
            }
        }
        
        // Calculate total with modifiers
        let basePrice = item.discounted_price || item.price;
        let modifiersPrice = 0;
        const modifiers = [];
        
        Object.entries(POSState.modifierSelections).forEach(([modName, options]) => {
            options.forEach(opt => {
                modifiersPrice += opt.price || 0;
                modifiers.push({
                    modifier: modName,
                    option: opt.name,
                    price: opt.price
                });
            });
        });
        
        const total = (basePrice + modifiersPrice) * POSState.modifierQty;
        
        addToCart({
            menu_item: item.name,
            item_name: item.item_name,
            item_name_ar: item.item_name_ar,
            rate: basePrice + modifiersPrice,
            qty: POSState.modifierQty,
            modifiers: modifiers,
            note: document.getElementById('item-note').value,
            kitchen_station: item.kitchen_station,
            total: total
        });
        
        closeAllModals();
    }
    
    // Add item to cart
    function addToCart(item) {
        // Check if similar item exists (same item, same modifiers)
        const existingIndex = POSState.cart.findIndex(cartItem => 
            cartItem.menu_item === item.menu_item && 
            JSON.stringify(cartItem.modifiers) === JSON.stringify(item.modifiers) &&
            cartItem.note === item.note
        );
        
        if (existingIndex > -1) {
            // Update quantity
            POSState.cart[existingIndex].qty += item.qty;
            POSState.cart[existingIndex].total = POSState.cart[existingIndex].rate * POSState.cart[existingIndex].qty;
        } else {
            // Add new item
            item.id = Date.now();
            POSState.cart.push(item);
        }
        
        renderCart();
        updateTotals();
        playSound('success');
        showToast(__('Added to cart'), 'success');
    }
    
    // Render cart
    function renderCart() {
        if (POSState.cart.length === 0) {
            DOM.cartItems.innerHTML = `
                <div class="cart-empty" id="cart-empty">
                    <i class="fa fa-shopping-basket"></i>
                    <p>${__('Cart is empty')}</p>
                    <small>${__('Add items from the menu')}</small>
                </div>
            `;
            DOM.cartItemCount.textContent = '0';
            DOM.btnSendKitchen.disabled = true;
            DOM.btnPay.disabled = true;
            return;
        }
        
        let html = '';
        let totalQty = 0;
        
        POSState.cart.forEach((item, index) => {
            totalQty += item.qty;
            
            const modifiersText = item.modifiers.map(m => m.option).join(', ');
            
            html += `
                <div class="cart-item" data-index="${index}">
                    <div class="cart-item-details">
                        <div class="cart-item-name">${item.item_name_ar || item.item_name}</div>
                        ${modifiersText ? `<div class="cart-item-modifiers">${modifiersText}</div>` : ''}
                        ${item.note ? `<div class="cart-item-modifiers">${item.note}</div>` : ''}
                        <div class="cart-item-price">${formatCurrency(item.total)}</div>
                    </div>
                    <div class="cart-item-qty">
                        <button class="btn-qty-minus" data-action="decrease"><i class="fa fa-minus"></i></button>
                        <span>${item.qty}</span>
                        <button class="btn-qty-plus" data-action="increase"><i class="fa fa-plus"></i></button>
                    </div>
                    <div class="cart-item-actions">
                        <button class="btn-item-action" data-action="remove" title="${__('Remove')}">
                            <i class="fa fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        });
        
        DOM.cartItems.innerHTML = html;
        DOM.cartItemCount.textContent = totalQty;
        DOM.btnSendKitchen.disabled = false;
        DOM.btnPay.disabled = false;
    }
    
    // Handle cart action (qty change, remove)
    function handleCartAction(e) {
        const btn = e.target.closest('button');
        if (!btn) return;
        
        const cartItem = btn.closest('.cart-item');
        if (!cartItem) return;
        
        const index = parseInt(cartItem.dataset.index);
        const action = btn.dataset.action;
        
        if (action === 'increase') {
            POSState.cart[index].qty++;
            POSState.cart[index].total = POSState.cart[index].rate * POSState.cart[index].qty;
        } else if (action === 'decrease') {
            if (POSState.cart[index].qty > 1) {
                POSState.cart[index].qty--;
                POSState.cart[index].total = POSState.cart[index].rate * POSState.cart[index].qty;
            } else {
                POSState.cart.splice(index, 1);
            }
        } else if (action === 'remove') {
            POSState.cart.splice(index, 1);
        }
        
        renderCart();
        updateTotals();
    }
    
    // Clear cart
    function clearCart() {
        if (POSState.cart.length === 0) return;
        
        if (confirm(__('Clear all items from cart?'))) {
            POSState.cart = [];
            POSState.discount = null;
            renderCart();
            updateTotals();
        }
    }
    
    // Update totals
    function updateTotals() {
        const subtotal = POSState.cart.reduce((sum, item) => sum + item.total, 0);
        
        // Discount
        let discountAmount = 0;
        if (POSState.discount) {
            if (POSState.discount.type === 'percent') {
                discountAmount = subtotal * POSState.discount.value / 100;
            } else {
                discountAmount = POSState.discount.value;
            }
            DOM.discountRow.style.display = 'flex';
            DOM.discountAmount.textContent = '-' + formatCurrency(discountAmount);
        } else {
            DOM.discountRow.style.display = 'none';
        }
        
        const afterDiscount = subtotal - discountAmount;
        
        // Service charge
        const servicePercent = POSState.settings.service_charge_percent || 0;
        const serviceCharge = afterDiscount * servicePercent / 100;
        
        // VAT
        const vatPercent = POSState.settings.vat_percent || 15;
        const vatAmount = (afterDiscount + serviceCharge) * vatPercent / 100;
        
        const grandTotal = afterDiscount + serviceCharge + vatAmount;
        
        DOM.subtotal.textContent = formatCurrency(subtotal);
        DOM.serviceCharge.textContent = formatCurrency(serviceCharge);
        DOM.vatAmount.textContent = formatCurrency(vatAmount);
        DOM.grandTotal.textContent = formatCurrency(grandTotal);
        DOM.payAmount.textContent = formatCurrency(grandTotal);
    }
    
    // Table selection
    function openTableModal() {
        renderTables();
        showModal(DOM.tableModal);
    }
    
    function renderTables() {
        let html = '';
        
        POSState.tables.forEach(table => {
            const statusClass = table.status.toLowerCase().replace(' ', '-');
            html += `
                <div class="table-card ${statusClass}" data-table="${table.name}">
                    <div class="table-number">${table.table_number}</div>
                    <div class="table-capacity"><i class="fa fa-users"></i> ${table.capacity}</div>
                </div>
            `;
        });
        
        document.getElementById('tables-grid').innerHTML = html;
    }
    
    function selectTable(tableName) {
        const table = POSState.tables.find(t => t.name === tableName);
        if (!table) return;
        
        POSState.selectedTable = table;
        DOM.selectedTableText.textContent = __('Table') + ' ' + table.table_number;
        DOM.btnSelectTable.classList.add('selected');
        DOM.guestCount.value = table.current_order?.guest_count || 1;
        
        closeAllModals();
    }
    
    // Customer modal
    function openCustomerModal() {
        document.getElementById('cust-name').value = POSState.selectedCustomer?.name || '';
        document.getElementById('cust-phone').value = POSState.selectedCustomer?.phone || '';
        document.getElementById('cust-address').value = POSState.selectedCustomer?.address || '';
        showModal(DOM.customerModal);
    }
    
    function saveCustomer() {
        const name = document.getElementById('cust-name').value.trim();
        const phone = document.getElementById('cust-phone').value.trim();
        const address = document.getElementById('cust-address').value.trim();
        
        if (name || phone) {
            POSState.selectedCustomer = { name, phone, address };
            DOM.customerInfo.innerHTML = `
                <span class="name">${name || __('Customer')}</span>
                ${phone ? `<span class="phone">${phone}</span>` : ''}
            `;
        } else {
            POSState.selectedCustomer = null;
        POSState.currentOrderId = null;
            DOM.customerInfo.innerHTML = `<span class="placeholder">${__('Walk-in Customer')}</span>`;
        }
        
        closeAllModals();
    }
    
    // Discount modal
    function openDiscountModal() {
        if (POSState.cart.length === 0) {
            showToast(__('Add items to cart first'), 'warning');
            return;
        }
        
        document.getElementById('discount-value').value = POSState.discount?.value || '';
        document.getElementById('discount-reason').value = POSState.discount?.reason || '';
        selectDiscountType(POSState.discount?.type || 'percent');
        showModal(DOM.discountModal);
    }
    
    function selectDiscountType(type) {
        document.querySelectorAll('.discount-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.type === type);
        });
        document.getElementById('discount-suffix').textContent = type === 'percent' ? '%' : POSState.settings.currency;
    }
    
    function applyDiscount() {
        const type = document.querySelector('.discount-tab.active').dataset.type;
        const value = parseFloat(document.getElementById('discount-value').value) || 0;
        const reason = document.getElementById('discount-reason').value;
        
        if (value <= 0) {
            showToast(__('Enter valid discount value'), 'warning');
            return;
        }
        
        if (type === 'percent' && value > (POSState.settings.max_discount_percent || 100)) {
            showToast(__('Maximum discount is') + ' ' + POSState.settings.max_discount_percent + '%', 'warning');
            return;
        }
        
        POSState.discount = { type, value, reason };
        updateTotals();
        closeAllModals();
        showToast(__('Discount applied'), 'success');
    }
    
    function removeDiscount() {
        POSState.discount = null;
        updateTotals();
        closeAllModals();
    }
    
    // Hold order
    function holdOrder() {
        if (POSState.cart.length === 0) {
            showToast(__('Cart is empty'), 'warning');
            return;
        }
        
        const holdName = prompt(__('Enter hold name (optional):'));
        
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.hold_order',
            args: {
                order_data: {
                    cart: POSState.cart,
                    orderType: POSState.orderType,
                    table: POSState.selectedTable,
                    customer: POSState.selectedCustomer,
                    discount: POSState.discount
                },
                hold_name: holdName
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    showToast(__('Order held'), 'success');
                    resetOrder();
                }
            }
        });
    }
    
    // Add order note
    function addOrderNote() {
        const note = prompt(__('Enter order note:'));
        if (note) {
            POSState.orderNote = note;
            showToast(__('Note added'), 'success');
        }
    }
    
    // Send to kitchen
    function sendToKitchen() {
        if (POSState.cart.length === 0) {
            showToast(__('Cart is empty'), 'warning');
            return;
        }
        
        if (POSState.orderType === 'Dine In' && !POSState.selectedTable) {
            showToast(__('Please select a table'), 'warning');
            return;
        }
        
        DOM.btnSendKitchen.disabled = true;
        DOM.btnSendKitchen.innerHTML = '<i class="fa fa-spinner fa-spin"></i> ' + __('Sending...');
        
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.create_order',
            args: {
                order_data: {
                    order_type: POSState.orderType,
                    table: POSState.selectedTable?.name,
                    customer_name: POSState.selectedCustomer?.name,
                    customer_phone: POSState.selectedCustomer?.phone,
                    delivery_address: POSState.selectedCustomer?.address,
                    guest_count: parseInt(DOM.guestCount.value) || 1,
                    items: POSState.cart,
                    discount: POSState.discount,
                    notes: POSState.orderNote
                }
            },
            callback: function(r) {
                DOM.btnSendKitchen.disabled = false;
                DOM.btnSendKitchen.innerHTML = '<i class="fa fa-paper-plane"></i> ' + __('Send to Kitchen');
                
                if (r.message && r.message.success) {
                    showToast(__('Order sent to kitchen'), 'success');
                    playSound('success');
                    POSState.currentOrderId = r.message.order_id;
                    loadPendingOrders();
                } else {
                    showToast(r.message?.message || __('Error creating order'), 'error');
                }
            },
            error: function() {
                DOM.btnSendKitchen.disabled = false;
                DOM.btnSendKitchen.innerHTML = '<i class="fa fa-paper-plane"></i> ' + __('Send to Kitchen');
                showToast(__('Connection error'), 'error');
            }
        });
    }
    
    // Payment
    function openPaymentModal() {
        if (POSState.cart.length === 0) {
            showToast(__('Cart is empty'), 'warning');
            return;
        }
        
        // Populate payment summary
        renderPaymentSummary();
        
        // Reset payment state
        document.getElementById('tendered-amount').value = '0.00';
        document.getElementById('change-display').style.display = 'none';
        document.getElementById('complete-payment').disabled = true;
        
        // Select cash by default
        selectPaymentMethod('Cash');
        
        showModal(DOM.paymentModal);
    }
    
    function renderPaymentSummary() {
        let itemsHtml = '';
        POSState.cart.forEach(item => {
            itemsHtml += `
                <div class="summary-item">
                    <span>${item.qty}x ${item.item_name_ar || item.item_name}</span>
                    <span>${formatCurrency(item.total)}</span>
                </div>
            `;
        });
        
        document.getElementById('payment-items').innerHTML = itemsHtml;
        
        // Totals
        const subtotal = POSState.cart.reduce((sum, item) => sum + item.total, 0);
        let discountAmount = 0;
        if (POSState.discount) {
            discountAmount = POSState.discount.type === 'percent' 
                ? subtotal * POSState.discount.value / 100 
                : POSState.discount.value;
        }
        
        const afterDiscount = subtotal - discountAmount;
        const serviceCharge = afterDiscount * (POSState.settings.service_charge_percent || 0) / 100;
        const vatAmount = (afterDiscount + serviceCharge) * (POSState.settings.vat_percent || 15) / 100;
        const grandTotal = afterDiscount + serviceCharge + vatAmount;
        
        document.getElementById('pay-subtotal').textContent = formatCurrency(subtotal);
        
        if (discountAmount > 0) {
            document.getElementById('pay-discount-row').style.display = 'flex';
            document.getElementById('pay-discount').textContent = '-' + formatCurrency(discountAmount);
        } else {
            document.getElementById('pay-discount-row').style.display = 'none';
        }
        
        document.getElementById('pay-service').textContent = formatCurrency(serviceCharge);
        document.getElementById('pay-vat').textContent = formatCurrency(vatAmount);
        document.getElementById('pay-total').textContent = formatCurrency(grandTotal);
        
        // Store for payment processing
        POSState.paymentTotal = grandTotal;
    }
    
    function bindPaymentEvents() {
        // Payment method buttons
        document.querySelectorAll('.method-btn').forEach(btn => {
            btn.addEventListener('click', () => selectPaymentMethod(btn.dataset.method));
        });
        
        // Quick amounts
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.dataset.amount === 'exact') {
                    document.getElementById('tendered-amount').value = POSState.paymentTotal.toFixed(2);
                } else {
                    document.getElementById('tendered-amount').value = btn.dataset.amount + '.00';
                }
                updateChange();
            });
        });
        
        // Numpad
        document.querySelectorAll('.payment-numpad button').forEach(btn => {
            btn.addEventListener('click', () => {
                const input = document.getElementById('tendered-amount');
                if (btn.dataset.action === 'clear') {
                    input.value = '0.00';
                } else {
                    let val = input.value.replace('.', '');
                    if (val === '000') val = '0';
                    val = val + btn.dataset.val;
                    val = parseFloat(val) / 100;
                    input.value = val.toFixed(2);
                }
                updateChange();
            });
        });
        
        // Complete payment
        document.getElementById('complete-payment').addEventListener('click', completePayment);
    }
    
    function selectPaymentMethod(method) {
        POSState.paymentMethod = method;
        
        document.querySelectorAll('.method-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.method === method);
        });
        
        // Show/hide payment sections
        document.getElementById('cash-payment').style.display = method === 'Cash' ? 'block' : 'none';
        document.getElementById('card-payment').style.display = method === 'Card' ? 'block' : 'none';
        
        // Enable complete button for card payments immediately
        if (method === 'Card' || method === 'Mobile') {
            document.getElementById('tendered-amount').value = POSState.paymentTotal.toFixed(2);
            document.getElementById('complete-payment').disabled = false;
        } else {
            updateChange();
        }
    }
    
    function updateChange() {
        const tendered = parseFloat(document.getElementById('tendered-amount').value) || 0;
        const total = POSState.paymentTotal || 0;
        const change = tendered - total;
        
        if (change >= 0 && tendered > 0) {
            document.getElementById('change-display').style.display = 'block';
            document.getElementById('change-amount').textContent = formatCurrency(change);
            document.getElementById('complete-payment').disabled = false;
        } else {
            document.getElementById('change-display').style.display = 'none';
            document.getElementById('complete-payment').disabled = true;
        }
    }
    
    function completePayment() {
        const btn = document.getElementById('complete-payment');
        const paymentMethod = document.querySelector('.payment-method.active')?.dataset.method || 'Cash';
        const amount = parseFloat(document.getElementById('tendered-amount').value) || 0;
        
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> ' + __('Processing...');
        
        const processActualPayment = (order_id) => {
            frappe.call({
                method: 'restaurant_pos.restaurant_pos.api.cashier.process_payment',
                args: {
                    order_id: order_id,
                    payment_data: {
                        method: paymentMethod,
                        amount: amount
                    }
                },
                callback: function(r) {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fa fa-check"></i> ' + __('Complete Payment');
                    
                    if (r.message && r.message.success) {
                        showToast(__('Payment successful! Change: ') + formatCurrency(r.message.change), 'success');
                        playSound('success');
                        
                        // Print receipt if enabled
                        if (document.getElementById('print-receipt').checked) {
                            // Print receipt logic
                        }
                        
                        closeAllModals();
                        resetOrder();
                        loadPendingOrders();
                    } else {
                        showToast(r.message?.message || __('Payment failed'), 'error');
                    }
                }
            });
        };

        if (POSState.currentOrderId) {
            processActualPayment(POSState.currentOrderId);
        } else {
            // Need to create order first since it wasn't sent to kitchen
            frappe.call({
                method: 'restaurant_pos.restaurant_pos.api.cashier.create_order',
                args: {
                    order_data: {
                        order_type: POSState.orderType,
                        table: POSState.selectedTable?.name,
                        customer_name: POSState.selectedCustomer?.name,
                        customer_phone: POSState.selectedCustomer?.phone,
                        delivery_address: POSState.selectedCustomer?.address,
                        guest_count: parseInt(DOM.guestCount.value) || 1,
                        items: POSState.cart,
                        discount: POSState.discount,
                        notes: POSState.orderNote
                    }
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        POSState.currentOrderId = r.message.order_id;
                        processActualPayment(r.message.order_id);
                    } else {
                        btn.disabled = false;
                        btn.innerHTML = '<i class="fa fa-check"></i> ' + __('Complete Payment');
                        showToast(r.message?.message || __('Failed to create order for payment'), 'error');
                    }
                }
            });
        }
    }
    
    // Reset order
    function resetOrder() {
        POSState.cart = [];
        POSState.selectedTable = null;
        POSState.selectedCustomer = null;
        POSState.currentOrderId = null;
        POSState.discount = null;
        POSState.orderNote = null;
        
        DOM.selectedTableText.textContent = __('Select Table');
        DOM.btnSelectTable.classList.remove('selected');
        DOM.guestCount.value = 1;
        DOM.customerInfo.innerHTML = `<span class="placeholder">${__('Walk-in Customer')}</span>`;
        
        renderCart();
        updateTotals();
    }
    
    // Load pending orders
    function loadPendingOrders() {
        frappe.call({
            method: 'restaurant_pos.restaurant_pos.api.cashier.get_pending_orders',
            callback: function(r) {
                if (r.message) {
                    POSState.pendingOrders = r.message;
                    DOM.pendingCount.textContent = r.message.length;
                    renderOrders();
                }
            }
        });
    }
    
    function renderOrders() {
        const container = document.getElementById('orders-list');
        
        if (POSState.pendingOrders.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fa fa-check-circle"></i>
                    <p>${__('No pending orders')}</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        POSState.pendingOrders.forEach(order => {
            html += `
                <div class="order-card" data-order="${order.name}">
                    <div class="order-header">
                        <span class="order-id">#${order.name}</span>
                        <span class="order-time">${order.waiting_minutes}m</span>
                    </div>
                    <div class="order-meta">
                        ${order.table_number ? `<span><i class="fa fa-chair"></i>${order.table_number}</span>` : ''}
                        <span><i class="fa fa-shopping-bag"></i>${order.order_type}</span>
                    </div>
                    <span class="order-status ${order.status.toLowerCase()}">${order.status}</span>
                    <div class="order-total">${formatCurrency(order.grand_total)}</div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
        // Add professional click event to load order into cart for voiding/payment
        container.querySelectorAll('.order-card').forEach(card => {
            card.addEventListener('click', () => {
                const orderId = card.dataset.order;
                
                frappe.call({
                    method: 'restaurant_pos.restaurant_pos.api.cashier.get_order_details',
                    args: { order_id: orderId },
                    callback: function(r) {
                        if (r.message && r.message.success) {
                            const order = r.message.order;
                            POSState.currentOrderId = order.name;
                            POSState.orderType = order.order_type;
                            POSState.cart = order.items.map(i => ({
                                item_name: i.menu_item,
                                name: i.item_name,
                                item_row_name: i.name, // Used for void
                                qty: i.qty,
                                price: i.rate,
                                modifiers: i.modifiers ? JSON.parse(i.modifiers) : [],
                                status: i.status
                            }));
                            
                            // Load table if Dine in
                            if (order.table_number) {
                                POSState.selectedTable = POSState.tables.find(t => t.table_number === order.table_number) || {name: order.restaurant_table, table_number: order.table_number};
                            } else {
                                POSState.selectedTable = null;
                            }
                            
                            renderCart();
                            updateTotals();
                            
                            // Select correct order type tab
                            document.querySelectorAll('.order-type-tabs .tab-btn').forEach(btn => {
                                btn.classList.toggle('active', btn.dataset.type === order.order_type);
                            });
                            
                            toggleOrdersPanel(); // hide panel
                            showToast(__('Order loaded successfully'), 'info');
                            
                            // Add extra buttons dynamically
                            setupProfessionalActionButtons();
                        }
                    }
                });
            });
        });
    }
    
    function toggleOrdersPanel() {
        DOM.ordersPanel.classList.toggle('show');
        if (DOM.ordersPanel.classList.contains('show')) {
            loadPendingOrders();
        }
    }
    
    function filterOrders(status) {
        document.querySelectorAll('#orders-panel .panel-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.status === status);
        });
        
        // Filter logic
        if (status === 'all') {
            renderOrders();
        } else {
            const filtered = POSState.pendingOrders.filter(o => o.status === status);
            // Render filtered
        }
    }
    
    // Utility functions
    function showModal(modal) {
        modal.classList.add('show');
    }
    
    function closeAllModals() {
        document.querySelectorAll('.modal').forEach(m => m.classList.remove('show'));
        DOM.ordersPanel.classList.remove('show');
    }
    
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: 'fa-check',
            error: 'fa-times',
            warning: 'fa-exclamation',
            info: 'fa-info'
        };
        
        toast.innerHTML = `
            <span class="toast-icon"><i class="fa ${icons[type]}"></i></span>
            <span class="toast-message">${message}</span>
        `;
        
        DOM.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    function playSound(type) {
        const audio = document.getElementById(`sound-${type}`);
        if (audio) {
            audio.currentTime = 0;
            audio.play().catch(() => {});
        }
    }
    
    function formatCurrency(amount) {
        return parseFloat(amount || 0).toFixed(2);
    }
    
    function startClock() {
        function updateClock() {
            const now = new Date();
            DOM.clock.textContent = now.toLocaleTimeString('en-US', { hour12: false });
        }
        updateClock();
        setInterval(updateClock, 1000);
    }
    
    function hideSplash() {
        setTimeout(() => {
            DOM.splash.classList.add('hidden');
        }, 1500);
    }
    
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
    
    function handleKeyboard(e) {
        // F2 - Focus search
        if (e.key === 'F2') {
            e.preventDefault();
            DOM.searchInput.focus();
        }
        // F9 - Payment
        if (e.key === 'F9' && POSState.cart.length > 0) {
            e.preventDefault();
            openPaymentModal();
        }
        // Escape - Close modals
        if (e.key === 'Escape') {
            closeAllModals();
        }
    }
    
    function exitPOS() {
        if (POSState.cart.length > 0) {
            if (!confirm(__('You have items in cart. Exit anyway?'))) {
                return;
            }
        }
        window.location.href = '/app';
    }
    
    // Settings modal
    function openSettingsModal() {
        // Open settings in a dialog or navigate to settings
        frappe.msgprint({
            title: __('POS Settings'),
            indicator: 'blue',
            message: `
                <div style="text-align: right; direction: rtl;">
                    <p><strong>${__('Cashier')}:</strong> ${DOM.cashierName.textContent}</p>
                    <p><strong>${__('Branch')}:</strong> ${DOM.branchName.textContent || __('All Branches')}</p>
                    <p><strong>${__('VAT')}:</strong> ${POSState.settings.vat_percent || 15}%</p>
                    <p><strong>${__('Service Charge')}:</strong> ${POSState.settings.service_charge_percent || 0}%</p>
                    <p><strong>${__('Currency')}:</strong> ${POSState.settings.currency || 'SAR'}</p>
                    <hr>
                    <p><a href="/app/restaurant-settings" target="_blank">${__('Open Full Settings')}</a></p>
                </div>
            `
        });
    }
    
    // Translation helper
    function __(text) {
        return frappe._ ? frappe._(text) : text;
    }
    
    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();
