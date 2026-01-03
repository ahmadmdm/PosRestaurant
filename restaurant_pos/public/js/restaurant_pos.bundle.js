/**
 * Restaurant POS - Main JavaScript Bundle
 * Core functionality for desk/admin interface
 */

// Restaurant POS Namespace
frappe.provide("restaurant_pos");

/**
 * Restaurant POS Main Controller
 */
restaurant_pos.RestaurantPOS = class {
    constructor() {
        this.init();
    }

    init() {
        this.setupRealtime();
        this.setupNotifications();
        this.bindEvents();
    }

    /**
     * Setup real-time event listeners
     */
    setupRealtime() {
        // New order notification
        frappe.realtime.on("restaurant_new_order", (data) => {
            this.handleNewOrder(data);
        });

        // Order status update
        frappe.realtime.on("restaurant_order_update", (data) => {
            this.handleOrderUpdate(data);
        });

        // Kitchen order ready
        frappe.realtime.on("order_ready", (data) => {
            this.handleOrderReady(data);
        });

        // Waiter call
        frappe.realtime.on("waiter_call", (data) => {
            this.handleWaiterCall(data);
        });

        // Table status update
        frappe.realtime.on("table_status_update", (data) => {
            this.handleTableUpdate(data);
        });

        // Payment update
        frappe.realtime.on("restaurant_payment_update", (data) => {
            this.handlePaymentUpdate(data);
        });
    }

    /**
     * Setup notification system
     */
    setupNotifications() {
        // Check for notification permission
        if ("Notification" in window && Notification.permission === "default") {
            Notification.requestPermission();
        }
    }

    /**
     * Bind global events
     */
    bindEvents() {
        // Keyboard shortcuts
        $(document).on("keydown", (e) => {
            // Ctrl+Shift+O - Open new order
            if (e.ctrlKey && e.shiftKey && e.key === "O") {
                e.preventDefault();
                this.newOrder();
            }
            // Ctrl+Shift+K - Open kitchen display
            if (e.ctrlKey && e.shiftKey && e.key === "K") {
                e.preventDefault();
                window.open("/kitchen", "_blank");
            }
        });
    }

    /**
     * Handle new order notification
     */
    handleNewOrder(data) {
        this.showNotification({
            title: __("New Order"),
            message: __("New order {0} from Table {1}", [data.order, data.table || "N/A"]),
            indicator: "green"
        });

        this.playSound("new_order");
        this.refreshListViews(["Restaurant Order", "Kitchen Order"]);
    }

    /**
     * Handle order status update
     */
    handleOrderUpdate(data) {
        if (data.status === "Cancelled") {
            this.showNotification({
                title: __("Order Cancelled"),
                message: __("Order {0} has been cancelled", [data.order_name]),
                indicator: "red"
            });
        }

        this.refreshListViews(["Restaurant Order", "Kitchen Order"]);
    }

    /**
     * Handle order ready notification
     */
    handleOrderReady(data) {
        this.showNotification({
            title: __("Order Ready"),
            message: __("Order for Table {0} is ready to serve", [data.table]),
            indicator: "green"
        });

        this.playSound("order_ready");
        this.sendBrowserNotification(__("Order Ready"), __("Order for Table {0} is ready", [data.table]));
    }

    /**
     * Handle waiter call
     */
    handleWaiterCall(data) {
        this.showNotification({
            title: __("Waiter Called"),
            message: __("Table {0} is calling for service: {1}", [data.table, data.call_type]),
            indicator: "orange"
        });

        this.playSound("waiter_call");
        this.sendBrowserNotification(__("Waiter Called"), __("Table {0} needs attention", [data.table]));
    }

    /**
     * Handle table status update
     */
    handleTableUpdate(data) {
        this.refreshListViews(["Restaurant Table"]);
        
        // Update floor plan if open
        if (restaurant_pos.floor_plan) {
            restaurant_pos.floor_plan.updateTable(data.table, data.status);
        }
    }

    /**
     * Handle payment update
     */
    handlePaymentUpdate(data) {
        if (data.status === "Paid") {
            this.showNotification({
                title: __("Payment Received"),
                message: __("Order {0} has been paid", [data.order]),
                indicator: "green"
            });
        }

        this.refreshListViews(["Restaurant Order"]);
    }

    /**
     * Show in-app notification
     */
    showNotification(options) {
        frappe.show_alert({
            message: options.message,
            indicator: options.indicator || "blue"
        }, 5);
    }

    /**
     * Send browser notification
     */
    sendBrowserNotification(title, body) {
        if ("Notification" in window && Notification.permission === "granted") {
            new Notification(title, {
                body: body,
                icon: "/assets/restaurant_pos/images/notification-icon.png",
                tag: "restaurant-pos"
            });
        }
    }

    /**
     * Play notification sound
     */
    playSound(type) {
        const sounds = {
            new_order: "/assets/restaurant_pos/sounds/new_order.mp3",
            order_ready: "/assets/restaurant_pos/sounds/order_ready.mp3",
            waiter_call: "/assets/restaurant_pos/sounds/waiter_call.mp3"
        };

        if (sounds[type]) {
            try {
                const audio = new Audio(sounds[type]);
                audio.volume = 0.5;
                audio.play().catch(() => {}); // Ignore autoplay restrictions
            } catch (e) {
                // Sound playback failed
            }
        }
    }

    /**
     * Refresh list views
     */
    refreshListViews(doctypes) {
        doctypes.forEach(doctype => {
            if (cur_list && cur_list.doctype === doctype) {
                cur_list.refresh();
            }
        });
    }

    /**
     * Create new order
     */
    newOrder() {
        frappe.new_doc("Restaurant Order");
    }
};

/**
 * Floor Plan Controller
 */
restaurant_pos.FloorPlan = class {
    constructor(container) {
        this.container = container;
        this.tables = {};
        this.init();
    }

    init() {
        this.loadTables();
    }

    async loadTables() {
        const tables = await frappe.call({
            method: "restaurant_pos.restaurant_pos.api.table.get_all_tables",
            args: {}
        });

        if (tables.message) {
            this.renderTables(tables.message);
        }
    }

    renderTables(tables) {
        const grid = $('<div class="restaurant-floor-plan"></div>');

        tables.forEach(table => {
            this.tables[table.name] = table;
            
            const tableEl = $(`
                <div class="floor-plan-table ${table.status.toLowerCase()}" data-table="${table.name}">
                    <div class="table-number">${table.table_number}</div>
                    <div class="table-capacity">${table.current_guests || 0}/${table.capacity}</div>
                </div>
            `);

            tableEl.on("click", () => this.onTableClick(table));
            grid.append(tableEl);
        });

        $(this.container).html(grid);
    }

    updateTable(tableName, status) {
        const tableEl = $(`.floor-plan-table[data-table="${tableName}"]`);
        tableEl.removeClass("available occupied reserved cleaning");
        tableEl.addClass(status.toLowerCase());
    }

    onTableClick(table) {
        if (table.status === "Available") {
            this.seatGuests(table);
        } else if (table.status === "Occupied") {
            this.showTableActions(table);
        }
    }

    seatGuests(table) {
        const dialog = new frappe.ui.Dialog({
            title: __("Seat Guests at Table {0}", [table.table_number]),
            fields: [
                {
                    label: __("Number of Guests"),
                    fieldname: "guests",
                    fieldtype: "Int",
                    reqd: 1,
                    default: 2
                },
                {
                    label: __("Customer"),
                    fieldname: "customer",
                    fieldtype: "Link",
                    options: "Customer"
                },
                {
                    label: __("Notes"),
                    fieldname: "notes",
                    fieldtype: "Small Text"
                }
            ],
            primary_action_label: __("Seat"),
            primary_action: async (values) => {
                const result = await frappe.call({
                    method: "restaurant_pos.restaurant_pos.api.waiter.seat_guests",
                    args: {
                        table_name: table.name,
                        guests_count: values.guests,
                        customer: values.customer,
                        notes: values.notes
                    }
                });

                if (result.message) {
                    dialog.hide();
                    this.loadTables();
                    frappe.show_alert(__("Guests seated at Table {0}", [table.table_number]));
                }
            }
        });

        dialog.show();
    }

    showTableActions(table) {
        const actions = [
            {
                label: __("View Orders"),
                action: () => {
                    frappe.set_route("List", "Restaurant Order", {table: table.name});
                }
            },
            {
                label: __("New Order"),
                action: () => {
                    frappe.new_doc("Restaurant Order", {table: table.name});
                }
            },
            {
                label: __("Transfer Table"),
                action: () => this.transferTable(table)
            },
            {
                label: __("Close Table"),
                action: () => this.closeTable(table)
            }
        ];

        const menu = actions.map(a => `<li><a href="#">${a.label}</a></li>`).join("");
        
        // Show context menu
        frappe.ui.toolbar.show_context_menu(
            $(`.floor-plan-table[data-table="${table.name}"]`),
            actions
        );
    }

    async transferTable(fromTable) {
        const dialog = new frappe.ui.Dialog({
            title: __("Transfer to Table"),
            fields: [
                {
                    label: __("New Table"),
                    fieldname: "to_table",
                    fieldtype: "Link",
                    options: "Restaurant Table",
                    reqd: 1,
                    get_query: () => ({
                        filters: {status: "Available"}
                    })
                }
            ],
            primary_action_label: __("Transfer"),
            primary_action: async (values) => {
                await frappe.call({
                    method: "restaurant_pos.restaurant_pos.api.waiter.transfer_table",
                    args: {
                        from_table: fromTable.name,
                        to_table: values.to_table
                    }
                });

                dialog.hide();
                this.loadTables();
            }
        });

        dialog.show();
    }

    async closeTable(table) {
        frappe.confirm(
            __("Close Table {0}? This will mark it for cleaning.", [table.table_number]),
            async () => {
                await frappe.call({
                    method: "restaurant_pos.restaurant_pos.api.waiter.close_table",
                    args: {table_name: table.name}
                });

                this.loadTables();
            }
        );
    }
};

/**
 * Order Quick Entry
 */
restaurant_pos.OrderQuickEntry = class {
    constructor(table, callback) {
        this.table = table;
        this.callback = callback;
        this.items = [];
        this.show();
    }

    async show() {
        const categories = await this.loadCategories();
        const menuItems = await this.loadMenuItems();

        this.dialog = new frappe.ui.Dialog({
            title: __("Quick Order - Table {0}", [this.table]),
            size: "extra-large",
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "order_content"
                }
            ]
        });

        this.renderOrderUI(categories, menuItems);
        this.dialog.show();
    }

    async loadCategories() {
        const result = await frappe.call({
            method: "restaurant_pos.restaurant_pos.api.menu.get_menu_categories"
        });
        return result.message || [];
    }

    async loadMenuItems() {
        const result = await frappe.call({
            method: "restaurant_pos.restaurant_pos.api.menu.get_menu"
        });
        return result.message || [];
    }

    renderOrderUI(categories, items) {
        // Implementation for quick order UI
        const html = `
            <div class="quick-order-container">
                <div class="categories-sidebar">
                    ${categories.map(c => `
                        <button class="category-btn" data-category="${c.name}">
                            ${c.category_name}
                        </button>
                    `).join("")}
                </div>
                <div class="items-grid">
                    ${items.map(i => `
                        <div class="menu-item-quick" data-item="${i.name}">
                            <div class="item-name">${i.item_name}</div>
                            <div class="item-price">${i.price}</div>
                        </div>
                    `).join("")}
                </div>
                <div class="order-summary">
                    <div class="order-items"></div>
                    <div class="order-total"></div>
                    <button class="btn btn-primary btn-block submit-order">
                        ${__("Place Order")}
                    </button>
                </div>
            </div>
        `;

        this.dialog.fields_dict.order_content.$wrapper.html(html);
        this.bindItemEvents();
    }

    bindItemEvents() {
        this.dialog.$wrapper.find(".menu-item-quick").on("click", (e) => {
            const itemName = $(e.currentTarget).data("item");
            this.addItem(itemName);
        });

        this.dialog.$wrapper.find(".submit-order").on("click", () => {
            this.submitOrder();
        });
    }

    addItem(itemName) {
        const existing = this.items.find(i => i.name === itemName);
        if (existing) {
            existing.qty++;
        } else {
            this.items.push({name: itemName, qty: 1});
        }
        this.updateSummary();
    }

    updateSummary() {
        // Update order summary display
    }

    async submitOrder() {
        if (!this.items.length) {
            frappe.throw(__("Please add items to the order"));
            return;
        }

        const result = await frappe.call({
            method: "restaurant_pos.restaurant_pos.api.order.place_order",
            args: {
                table: this.table,
                items: this.items.map(i => ({
                    menu_item: i.name,
                    qty: i.qty
                }))
            }
        });

        if (result.message) {
            this.dialog.hide();
            frappe.show_alert(__("Order placed successfully"));
            if (this.callback) this.callback(result.message);
        }
    }
};

// Initialize on page load
$(document).ready(() => {
    restaurant_pos.main = new restaurant_pos.RestaurantPOS();
});

// Export for external use
window.RestaurantPOS = restaurant_pos;
