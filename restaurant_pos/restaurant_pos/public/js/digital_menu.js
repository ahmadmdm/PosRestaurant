/**
 * Restaurant POS - Digital Menu
 * Mobile-optimized menu for QR ordering
 */

class DigitalMenu {
    constructor() {
        this.app = document.getElementById('digital-menu-app');
        this.tableId = this.app?.dataset.table || '';
        this.lang = this.app?.dataset.lang || 'en';
        this.cart = [];
        this.menu = [];
        this.categories = [];
        this.currentItem = null;
        this.currentQty = 1;
        this.selectedModifiers = {};
        this.currency = 'SAR';
        this.orderId = null;
        
        this.init();
    }
    
    async init() {
        try {
            // Set document direction
            document.documentElement.dir = this.lang === 'ar' ? 'rtl' : 'ltr';
            
            // Load menu data
            await this.loadMenu();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Setup real-time updates
            this.setupRealtime();
            
            // Hide loading, show app
            document.getElementById('menu-loading').style.display = 'none';
            document.getElementById('menu-container').style.display = 'block';
            
            // Load cart from localStorage
            this.loadCart();
            
        } catch (error) {
            console.error('Failed to initialize menu:', error);
            this.showError('Failed to load menu. Please try again.');
        }
    }
    
    async loadMenu() {
        const response = await frappe.call({
            method: 'restaurant_pos.api.menu.get_menu',
            args: {
                table_id: this.tableId,
                lang: this.lang
            }
        });
        
        if (response.message?.success) {
            const data = response.message.data;
            this.menu = data.items;
            this.categories = data.categories;
            this.currency = data.currency || 'SAR';
            
            if (data.table_info) {
                document.getElementById('table-info').textContent = 
                    `Table ${data.table_info.table_number}`;
            }
            
            this.renderCategories();
            this.renderMenu();
        }
    }
    
    renderCategories() {
        const nav = document.querySelector('.categories-scroll');
        nav.innerHTML = '';
        
        // Add "All" category
        const allBtn = document.createElement('button');
        allBtn.className = 'category-btn active';
        allBtn.dataset.category = 'all';
        allBtn.textContent = this.lang === 'ar' ? 'الكل' : 'All';
        nav.appendChild(allBtn);
        
        // Add categories
        this.categories.forEach(cat => {
            const btn = document.createElement('button');
            btn.className = 'category-btn';
            btn.dataset.category = cat.name;
            btn.textContent = this.lang === 'ar' && cat.name_ar ? cat.name_ar : cat.name;
            nav.appendChild(btn);
        });
    }
    
    renderMenu(filterCategory = 'all') {
        const content = document.getElementById('menu-content');
        content.innerHTML = '';
        
        const categoriesToShow = filterCategory === 'all' 
            ? this.categories 
            : this.categories.filter(c => c.name === filterCategory);
        
        categoriesToShow.forEach(category => {
            const items = this.menu.filter(item => item.category === category.name);
            if (items.length === 0) return;
            
            const section = document.createElement('section');
            section.className = 'category-section';
            section.id = `category-${category.name}`;
            
            const title = document.createElement('h2');
            title.className = 'category-title';
            title.textContent = this.lang === 'ar' && category.name_ar ? category.name_ar : category.name;
            section.appendChild(title);
            
            const grid = document.createElement('div');
            grid.className = 'items-grid';
            
            items.forEach(item => {
                grid.appendChild(this.createItemCard(item));
            });
            
            section.appendChild(grid);
            content.appendChild(section);
        });
    }
    
    createItemCard(item) {
        const card = document.createElement('div');
        card.className = `menu-item-card ${item.is_sold_out ? 'sold-out' : ''}`;
        card.dataset.itemId = item.id;
        
        const name = this.lang === 'ar' && item.name_ar ? item.name_ar : item.name;
        const description = this.lang === 'ar' && item.description_ar ? item.description_ar : item.description;
        
        card.innerHTML = `
            <div class="item-card-image">
                <img src="${item.image || '/assets/restaurant_pos/images/default-food.jpg'}" 
                     alt="${name}" loading="lazy">
                ${item.is_sold_out ? '<span class="item-sold-out-badge">Sold Out</span>' : ''}
            </div>
            <div class="item-card-body">
                <h3 class="item-card-name">${name}</h3>
                ${description ? `<p class="item-card-description">${description}</p>` : ''}
                <div class="item-card-footer">
                    <div class="item-card-price ${item.discounted_price ? 'discounted' : ''}">
                        ${item.discounted_price ? 
                            `<span class="original-price">${this.formatPrice(item.price)}</span>
                             <span>${this.formatPrice(item.discounted_price)}</span>` :
                            this.formatPrice(item.price)
                        }
                    </div>
                    ${!item.is_sold_out ? `
                        <button class="btn-add" data-item-id="${item.id}">
                            <i class="fa fa-plus"></i>
                        </button>
                    ` : ''}
                </div>
                ${this.renderTags(item)}
            </div>
        `;
        
        return card;
    }
    
    renderTags(item) {
        const tags = [];
        
        if (item.spicy_level > 0) {
            tags.push(`<span class="item-tag spicy">${'🌶️'.repeat(Math.min(item.spicy_level, 3))}</span>`);
        }
        
        if (item.dietary_tags) {
            item.dietary_tags.forEach(tag => {
                let className = '';
                if (tag.toLowerCase().includes('vegetarian')) className = 'vegetarian';
                else if (tag.toLowerCase().includes('vegan')) className = 'vegan';
                else if (tag.toLowerCase().includes('halal')) className = 'halal';
                tags.push(`<span class="item-tag ${className}">${tag}</span>`);
            });
        }
        
        return tags.length ? `<div class="item-tags">${tags.join('')}</div>` : '';
    }
    
    async openItemModal(itemId) {
        const item = this.menu.find(i => i.id === itemId);
        if (!item || item.is_sold_out) return;
        
        this.currentItem = item;
        this.currentQty = 1;
        this.selectedModifiers = {};
        
        const modal = document.getElementById('item-modal');
        const name = this.lang === 'ar' && item.name_ar ? item.name_ar : item.name;
        const description = this.lang === 'ar' && item.description_ar ? item.description_ar : item.description;
        
        document.getElementById('modal-item-image').src = item.image || '/assets/restaurant_pos/images/default-food.jpg';
        document.getElementById('modal-item-name').textContent = name;
        document.getElementById('modal-item-description').textContent = description || '';
        document.getElementById('modal-item-price').textContent = this.formatPrice(item.discounted_price || item.price);
        document.getElementById('modal-item-calories').textContent = item.calories ? `${item.calories} cal` : '';
        document.getElementById('qty-value').textContent = '1';
        document.getElementById('special-instructions').value = '';
        
        // Load modifiers
        await this.loadModifiers(item);
        
        // Update add button price
        this.updateAddButtonPrice();
        
        modal.classList.add('open');
    }
    
    async loadModifiers(item) {
        const section = document.getElementById('modifiers-section');
        
        if (!item.allow_customization) {
            section.style.display = 'none';
            return;
        }
        
        try {
            const response = await frappe.call({
                method: 'restaurant_pos.api.menu.get_item_modifiers',
                args: { item_id: item.id }
            });
            
            if (response.message?.success && response.message.data.length > 0) {
                const modifiers = response.message.data;
                section.innerHTML = '';
                section.style.display = 'block';
                
                modifiers.forEach(mod => {
                    const group = this.createModifierGroup(mod);
                    section.appendChild(group);
                });
            } else {
                section.style.display = 'none';
            }
        } catch (error) {
            console.error('Failed to load modifiers:', error);
            section.style.display = 'none';
        }
    }
    
    createModifierGroup(modifier) {
        const group = document.createElement('div');
        group.className = 'modifier-group';
        group.dataset.modifierId = modifier.name;
        
        const title = this.lang === 'ar' && modifier.title_ar ? modifier.title_ar : modifier.title;
        
        group.innerHTML = `
            <div class="modifier-group-title">
                <span>${title}</span>
                ${modifier.required ? `<span class="modifier-required">${this.lang === 'ar' ? 'مطلوب' : 'Required'}</span>` : ''}
            </div>
            <div class="modifier-options">
                ${modifier.options.map(opt => `
                    <label class="modifier-option ${opt.is_default ? 'selected' : ''}" data-option-id="${opt.name}">
                        <input type="${modifier.type === 'Single' ? 'radio' : 'checkbox'}" 
                               name="mod_${modifier.name}" 
                               value="${opt.name}"
                               ${opt.is_default ? 'checked' : ''}>
                        <span class="modifier-option-label">
                            ${this.lang === 'ar' && opt.label_ar ? opt.label_ar : opt.label}
                        </span>
                        ${opt.price > 0 ? `<span class="modifier-option-price">+${this.formatPrice(opt.price)}</span>` : ''}
                    </label>
                `).join('')}
            </div>
        `;
        
        // Initialize default selections
        modifier.options.forEach(opt => {
            if (opt.is_default) {
                if (!this.selectedModifiers[modifier.name]) {
                    this.selectedModifiers[modifier.name] = [];
                }
                this.selectedModifiers[modifier.name].push({
                    id: opt.name,
                    label: opt.label,
                    price: opt.price
                });
            }
        });
        
        return group;
    }
    
    updateAddButtonPrice() {
        if (!this.currentItem) return;
        
        let total = this.currentItem.discounted_price || this.currentItem.price;
        
        // Add modifier prices
        Object.values(this.selectedModifiers).forEach(mods => {
            mods.forEach(mod => {
                total += mod.price || 0;
            });
        });
        
        // Multiply by quantity
        total *= this.currentQty;
        
        document.getElementById('add-total').textContent = this.formatPrice(total);
    }
    
    closeItemModal() {
        document.getElementById('item-modal').classList.remove('open');
        this.currentItem = null;
        this.selectedModifiers = {};
    }
    
    addToCart() {
        if (!this.currentItem) return;
        
        const cartItem = {
            id: Date.now(), // Unique cart item ID
            item_id: this.currentItem.id,
            name: this.currentItem.name,
            name_ar: this.currentItem.name_ar,
            image: this.currentItem.image,
            price: this.currentItem.discounted_price || this.currentItem.price,
            qty: this.currentQty,
            modifiers: Object.values(this.selectedModifiers).flat(),
            special_instructions: document.getElementById('special-instructions').value.trim()
        };
        
        // Calculate total price including modifiers
        let modifierTotal = 0;
        cartItem.modifiers.forEach(mod => {
            modifierTotal += mod.price || 0;
        });
        cartItem.total_price = (cartItem.price + modifierTotal) * cartItem.qty;
        
        this.cart.push(cartItem);
        this.saveCart();
        this.updateCartBadge();
        this.closeItemModal();
        
        // Show toast
        this.showToast(this.lang === 'ar' ? 'تمت الإضافة للسلة' : 'Added to cart');
    }
    
    updateCartBadge() {
        const badge = document.getElementById('cart-badge');
        const count = this.cart.reduce((sum, item) => sum + item.qty, 0);
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    }
    
    openCart() {
        this.renderCart();
        document.getElementById('cart-panel').classList.add('open');
    }
    
    closeCart() {
        document.getElementById('cart-panel').classList.remove('open');
    }
    
    renderCart() {
        const container = document.getElementById('cart-items');
        
        if (this.cart.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon"><i class="fa fa-shopping-cart"></i></div>
                    <h3 class="empty-state-title">${this.lang === 'ar' ? 'السلة فارغة' : 'Your cart is empty'}</h3>
                    <p class="empty-state-text">${this.lang === 'ar' ? 'أضف بعض الأصناف لتبدأ' : 'Add some items to get started'}</p>
                </div>
            `;
            document.getElementById('btn-checkout').disabled = true;
            document.getElementById('cart-subtotal').textContent = this.formatPrice(0);
            document.getElementById('cart-total').textContent = this.formatPrice(0);
            return;
        }
        
        container.innerHTML = this.cart.map(item => {
            const name = this.lang === 'ar' && item.name_ar ? item.name_ar : item.name;
            const modifierText = item.modifiers.map(m => m.label).join(', ');
            
            return `
                <div class="cart-item" data-cart-id="${item.id}">
                    <img src="${item.image || '/assets/restaurant_pos/images/default-food.jpg'}" 
                         alt="${name}" class="cart-item-image">
                    <div class="cart-item-details">
                        <div class="cart-item-name">${name}</div>
                        ${modifierText ? `<div class="cart-item-modifiers">${modifierText}</div>` : ''}
                        ${item.special_instructions ? `<div class="cart-item-modifiers">"${item.special_instructions}"</div>` : ''}
                    </div>
                    <div class="cart-item-controls">
                        <div class="cart-item-price">${this.formatPrice(item.total_price)}</div>
                        <div class="qty-controls">
                            <button class="btn-cart-minus" data-cart-id="${item.id}">
                                <i class="fa fa-minus"></i>
                            </button>
                            <span>${item.qty}</span>
                            <button class="btn-cart-plus" data-cart-id="${item.id}">
                                <i class="fa fa-plus"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Update totals
        const subtotal = this.cart.reduce((sum, item) => sum + item.total_price, 0);
        document.getElementById('cart-subtotal').textContent = this.formatPrice(subtotal);
        document.getElementById('cart-total').textContent = this.formatPrice(subtotal);
        document.getElementById('btn-checkout').disabled = false;
    }
    
    updateCartItemQty(cartId, delta) {
        const item = this.cart.find(i => i.id === parseInt(cartId));
        if (!item) return;
        
        item.qty += delta;
        
        if (item.qty <= 0) {
            this.cart = this.cart.filter(i => i.id !== parseInt(cartId));
        } else {
            // Recalculate total price
            let modifierTotal = 0;
            item.modifiers.forEach(mod => {
                modifierTotal += mod.price || 0;
            });
            item.total_price = (item.price + modifierTotal) * item.qty;
        }
        
        this.saveCart();
        this.updateCartBadge();
        this.renderCart();
    }
    
    async placeOrder() {
        if (this.cart.length === 0) return;
        
        try {
            // Show loading
            document.getElementById('btn-checkout').disabled = true;
            document.getElementById('btn-checkout').innerHTML = '<i class="fa fa-spinner fa-spin"></i>';
            
            const orderItems = this.cart.map(item => ({
                menu_item: item.item_id,
                qty: item.qty,
                modifiers: JSON.stringify(item.modifiers),
                special_instructions: item.special_instructions
            }));
            
            const response = await frappe.call({
                method: 'restaurant_pos.api.order.place_order',
                args: {
                    table_id: this.tableId,
                    items: JSON.stringify(orderItems),
                    lang: this.lang
                }
            });
            
            if (response.message?.success) {
                this.orderId = response.message.data.order_id;
                this.cart = [];
                this.saveCart();
                this.updateCartBadge();
                this.closeCart();
                
                // Show success
                this.showOrderStatus(response.message.data);
                this.showToast(this.lang === 'ar' ? 'تم إرسال طلبك!' : 'Order placed successfully!');
            } else {
                throw new Error(response.message?.message || 'Order failed');
            }
            
        } catch (error) {
            console.error('Order failed:', error);
            this.showToast(this.lang === 'ar' ? 'فشل في إرسال الطلب' : 'Failed to place order', 'error');
        } finally {
            document.getElementById('btn-checkout').disabled = false;
            document.getElementById('btn-checkout').innerHTML = this.lang === 'ar' ? 'تأكيد الطلب' : 'Place Order';
        }
    }
    
    showOrderStatus(orderData) {
        const panel = document.getElementById('order-status-panel');
        const content = document.getElementById('status-content');
        
        content.innerHTML = `
            <div class="status-step active">
                <div class="status-icon"><i class="fa fa-check"></i></div>
                <span>${this.lang === 'ar' ? 'تم استلام الطلب' : 'Order Received'}</span>
            </div>
            <div class="status-step">
                <div class="status-icon"><i class="fa fa-utensils"></i></div>
                <span>${this.lang === 'ar' ? 'قيد التحضير' : 'Preparing'}</span>
            </div>
            <div class="status-step">
                <div class="status-icon"><i class="fa fa-bell"></i></div>
                <span>${this.lang === 'ar' ? 'جاهز' : 'Ready'}</span>
            </div>
        `;
        
        panel.style.display = 'block';
    }
    
    async callWaiter() {
        if (!this.tableId) {
            this.showToast(this.lang === 'ar' ? 'مسح QR code مطلوب' : 'Please scan table QR code', 'warning');
            return;
        }
        
        try {
            const response = await frappe.call({
                method: 'restaurant_pos.api.table.call_waiter',
                args: {
                    table_id: this.tableId,
                    call_type: 'Assistance'
                }
            });
            
            if (response.message?.success) {
                this.showToast(this.lang === 'ar' ? 'تم استدعاء النادل' : 'Waiter has been called');
            }
        } catch (error) {
            console.error('Call waiter failed:', error);
        }
    }
    
    setupEventListeners() {
        // Category buttons
        document.querySelector('.categories-scroll').addEventListener('click', (e) => {
            const btn = e.target.closest('.category-btn');
            if (!btn) return;
            
            document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            this.renderMenu(btn.dataset.category);
        });
        
        // Menu items
        document.getElementById('menu-content').addEventListener('click', (e) => {
            const card = e.target.closest('.menu-item-card');
            const addBtn = e.target.closest('.btn-add');
            
            if (addBtn) {
                e.stopPropagation();
                this.openItemModal(addBtn.dataset.itemId);
            } else if (card) {
                this.openItemModal(card.dataset.itemId);
            }
        });
        
        // Search
        document.getElementById('menu-search').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (query) {
                this.searchMenu(query);
            } else {
                this.renderMenu('all');
            }
        });
        
        // Cart button
        document.getElementById('btn-cart').addEventListener('click', () => this.openCart());
        document.getElementById('btn-close-cart').addEventListener('click', () => this.closeCart());
        
        // Cart item controls
        document.getElementById('cart-items').addEventListener('click', (e) => {
            const minusBtn = e.target.closest('.btn-cart-minus');
            const plusBtn = e.target.closest('.btn-cart-plus');
            
            if (minusBtn) {
                this.updateCartItemQty(minusBtn.dataset.cartId, -1);
            } else if (plusBtn) {
                this.updateCartItemQty(plusBtn.dataset.cartId, 1);
            }
        });
        
        // Checkout
        document.getElementById('btn-checkout').addEventListener('click', () => this.placeOrder());
        
        // Item modal
        document.getElementById('btn-close-modal').addEventListener('click', () => this.closeItemModal());
        document.querySelector('.modal-overlay').addEventListener('click', () => this.closeItemModal());
        
        // Quantity controls in modal
        document.getElementById('btn-qty-minus').addEventListener('click', () => {
            if (this.currentQty > 1) {
                this.currentQty--;
                document.getElementById('qty-value').textContent = this.currentQty;
                this.updateAddButtonPrice();
            }
        });
        
        document.getElementById('btn-qty-plus').addEventListener('click', () => {
            this.currentQty++;
            document.getElementById('qty-value').textContent = this.currentQty;
            this.updateAddButtonPrice();
        });
        
        // Modifier selection
        document.getElementById('modifiers-section').addEventListener('change', (e) => {
            const option = e.target.closest('.modifier-option');
            const group = e.target.closest('.modifier-group');
            if (!option || !group) return;
            
            const modifierId = group.dataset.modifierId;
            const isRadio = e.target.type === 'radio';
            
            if (isRadio) {
                // Single selection - update selected class
                group.querySelectorAll('.modifier-option').forEach(opt => {
                    opt.classList.remove('selected');
                });
                option.classList.add('selected');
                
                // Update selectedModifiers
                const priceText = option.querySelector('.modifier-option-price')?.textContent;
                const price = priceText ? parseFloat(priceText.replace(/[^0-9.]/g, '')) : 0;
                
                this.selectedModifiers[modifierId] = [{
                    id: e.target.value,
                    label: option.querySelector('.modifier-option-label').textContent.trim(),
                    price: price
                }];
            } else {
                // Multiple selection
                option.classList.toggle('selected', e.target.checked);
                
                if (!this.selectedModifiers[modifierId]) {
                    this.selectedModifiers[modifierId] = [];
                }
                
                if (e.target.checked) {
                    const priceText = option.querySelector('.modifier-option-price')?.textContent;
                    const price = priceText ? parseFloat(priceText.replace(/[^0-9.]/g, '')) : 0;
                    
                    this.selectedModifiers[modifierId].push({
                        id: e.target.value,
                        label: option.querySelector('.modifier-option-label').textContent.trim(),
                        price: price
                    });
                } else {
                    this.selectedModifiers[modifierId] = this.selectedModifiers[modifierId]
                        .filter(m => m.id !== e.target.value);
                }
            }
            
            this.updateAddButtonPrice();
        });
        
        // Add to cart
        document.getElementById('btn-add-to-cart').addEventListener('click', () => this.addToCart());
        
        // Call waiter
        document.getElementById('btn-call-waiter').addEventListener('click', () => this.callWaiter());
        
        // Close order status
        document.getElementById('btn-close-status')?.addEventListener('click', () => {
            document.getElementById('order-status-panel').style.display = 'none';
        });
        
        // Language toggle
        document.getElementById('btn-language').addEventListener('click', () => {
            this.lang = this.lang === 'en' ? 'ar' : 'en';
            document.documentElement.dir = this.lang === 'ar' ? 'rtl' : 'ltr';
            this.loadMenu();
        });
    }
    
    searchMenu(query) {
        const filtered = this.menu.filter(item => {
            return item.name.toLowerCase().includes(query) ||
                   (item.name_ar && item.name_ar.includes(query)) ||
                   (item.description && item.description.toLowerCase().includes(query));
        });
        
        const content = document.getElementById('menu-content');
        content.innerHTML = '';
        
        if (filtered.length === 0) {
            content.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon"><i class="fa fa-search"></i></div>
                    <h3 class="empty-state-title">${this.lang === 'ar' ? 'لا توجد نتائج' : 'No results found'}</h3>
                    <p class="empty-state-text">${this.lang === 'ar' ? 'جرب كلمات بحث مختلفة' : 'Try different search terms'}</p>
                </div>
            `;
            return;
        }
        
        const grid = document.createElement('div');
        grid.className = 'items-grid';
        filtered.forEach(item => {
            grid.appendChild(this.createItemCard(item));
        });
        content.appendChild(grid);
    }
    
    setupRealtime() {
        if (!this.orderId) return;
        
        frappe.realtime.on('restaurant:order_status', (data) => {
            if (data.order_id === this.orderId) {
                this.updateOrderStatusUI(data.status);
            }
        });
        
        frappe.realtime.on('restaurant:call_response', (data) => {
            this.showToast(this.lang === 'ar' ? 'النادل في طريقه إليك' : 'Waiter is on the way');
        });
    }
    
    updateOrderStatusUI(status) {
        const steps = document.querySelectorAll('.status-step');
        const statusMap = {
            'Confirmed': 0,
            'Preparing': 1,
            'Ready': 2,
            'Served': 2
        };
        
        const activeIndex = statusMap[status] ?? 0;
        
        steps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (index < activeIndex) {
                step.classList.add('completed');
            } else if (index === activeIndex) {
                step.classList.add('active');
            }
        });
    }
    
    formatPrice(amount) {
        return `${parseFloat(amount || 0).toFixed(2)} ${this.currency}`;
    }
    
    saveCart() {
        localStorage.setItem('restaurant_cart', JSON.stringify(this.cart));
    }
    
    loadCart() {
        try {
            const saved = localStorage.getItem('restaurant_cart');
            if (saved) {
                this.cart = JSON.parse(saved);
                this.updateCartBadge();
            }
        } catch (e) {
            this.cart = [];
        }
    }
    
    showToast(message, type = 'success') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'error' ? '#e74c3c' : type === 'warning' ? '#f39c12' : '#27ae60'};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 9999;
            animation: fadeInUp 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'fadeOutDown 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    showError(message) {
        document.getElementById('menu-loading').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon"><i class="fa fa-exclamation-triangle"></i></div>
                <h3 class="empty-state-title">Error</h3>
                <p class="empty-state-text">${message}</p>
                <button onclick="location.reload()" class="btn-primary" style="margin-top: 16px; width: auto; padding: 12px 24px;">
                    Try Again
                </button>
            </div>
        `;
    }
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeInUp {
        from { opacity: 0; transform: translate(-50%, 20px); }
        to { opacity: 1; transform: translate(-50%, 0); }
    }
    @keyframes fadeOutDown {
        from { opacity: 1; transform: translate(-50%, 0); }
        to { opacity: 0; transform: translate(-50%, 20px); }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.digitalMenu = new DigitalMenu();
});
