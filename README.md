# 🍽️ Restaurant POS - نظام نقاط البيع للمطاعم

<div dir="rtl">

## 📋 نظرة عامة

نظام نقاط بيع متكامل للمطاعم مبني على Frappe/ERPNext، يوفر حلاً شاملاً لإدارة المطاعم من الطلب حتى الدفع مع دعم كامل للغة العربية.

</div>

---

## ✨ Key Features | الميزات الرئيسية

### 📱 Digital Menu (القائمة الرقمية)
- QR Code ordering - طلب عبر رمز QR
- Multi-language support (Arabic/English)
- Real-time menu updates
- Item customizations and modifiers
- Allergen and dietary information
- Beautiful responsive design

### 🖥️ Kitchen Display System (نظام عرض المطبخ)
- Real-time order display
- Order prioritization
- Station-based routing
- Timer and alerts
- Order status updates
- Sound notifications

### 🪑 Table Management (إدارة الطاولات)
- Visual table layout
- Table status tracking
- QR code generation
- Session management
- Waiter call system

### 📦 Order Management (إدارة الطلبات)
- Dine-in, Takeaway, Delivery support
- Order modifications
- Split bills
- Discounts and promotions
- Order history

### 🖨️ Printing (الطباعة)
- Kitchen Order Tickets (KOT)
- Customer receipts
- Network printer support
- Multiple printer stations

---

## 🏗️ System Architecture | بنية النظام

```
restaurant_pos/
├── doctype/                    # Data Models
│   ├── restaurant_settings/    # إعدادات المطعم
│   ├── restaurant_table/       # الطاولات
│   ├── restaurant_order/       # الطلبات
│   ├── menu_category/          # فئات القائمة
│   ├── menu_item/              # عناصر القائمة
│   ├── kitchen_order/          # طلبات المطبخ
│   ├── kitchen_station/        # محطات المطبخ
│   ├── waiter_call/            # نداء النادل
│   └── pos_printer/            # الطابعات
├── api/                        # REST APIs
│   ├── menu.py                 # Menu endpoints
│   ├── order.py                # Order endpoints
│   ├── kitchen.py              # Kitchen endpoints
│   ├── table.py                # Table endpoints
│   └── waiter.py               # Waiter endpoints
├── www/                        # Web Pages
│   ├── menu.html/py            # Digital menu page
│   └── kitchen.html/py         # Kitchen display page
├── public/                     # Static Assets
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript
│   └── sounds/                 # Audio files
└── workspace/                  # ERPNext Workspace
```

---

## 📦 DocTypes | أنواع المستندات

### 1. Restaurant Settings (إعدادات المطعم)
Single DocType for global restaurant configuration.

| Field | Type | Description |
|-------|------|-------------|
| restaurant_name | Data | اسم المطعم |
| restaurant_name_ar | Data | اسم المطعم بالعربية |
| logo | Attach Image | شعار المطعم |
| default_currency | Link | العملة الافتراضية |
| tax_rate | Percent | نسبة الضريبة |
| service_charge_rate | Percent | نسبة رسوم الخدمة |
| enable_qr_ordering | Check | تفعيل الطلب بـ QR |
| kot_printer | Link | طابعة تذاكر المطبخ |

### 2. Restaurant Table (الطاولات)
```python
# Fields
- table_number: رقم الطاولة
- table_name: اسم الطاولة
- capacity: السعة
- status: الحالة (Available/Occupied/Reserved)
- qr_code: رمز QR
- qr_code_url: رابط QR
- branch: الفرع
- is_vip: طاولة VIP
```

### 3. Menu Category (فئات القائمة)
```python
# Fields
- category_name: اسم الفئة (English)
- category_name_ar: اسم الفئة (Arabic)
- description: الوصف
- image: الصورة
- display_order: ترتيب العرض
- is_active: مفعلة
- available_days: أيام التوفر
```

### 4. Menu Item (عناصر القائمة)
```python
# Fields
- item_name: اسم العنصر
- item_name_ar: اسم العنصر بالعربية
- category: الفئة
- price: السعر
- discounted_price: سعر التخفيض
- description: الوصف
- image: الصورة
- calories: السعرات الحرارية
- preparation_time: وقت التحضير
- is_active: مفعل
- allow_customization: السماح بالتخصيص
- modifiers: المعدلات
- allergens: مسببات الحساسية
- dietary_tags: العلامات الغذائية
```

### 5. Restaurant Order (الطلبات)
```python
# Fields
- order_number: رقم الطلب
- order_type: نوع الطلب (Dine In/Takeaway/Delivery)
- table: الطاولة
- customer: العميل
- items: العناصر
- subtotal: المجموع الفرعي
- tax_amount: مبلغ الضريبة
- service_charge: رسوم الخدمة
- discount_amount: مبلغ الخصم
- grand_total: المجموع الكلي
- status: الحالة
- payment_status: حالة الدفع
```

### 6. Kitchen Order (طلبات المطبخ)
```python
# Fields
- restaurant_order: الطلب الأصلي
- station: محطة المطبخ
- items: العناصر
- status: الحالة (Pending/Preparing/Ready/Served)
- priority: الأولوية
- started_at: وقت البدء
- completed_at: وقت الإنجاز
```

---

## 🔌 API Reference | مرجع الـ API

### Menu APIs

#### Get Menu
```javascript
// GET /api/method/restaurant_pos.api.menu.get_menu
frappe.call({
    method: 'restaurant_pos.api.menu.get_menu',
    args: {
        table_code: 'TABLE-001',
        language: 'ar'
    },
    callback: function(r) {
        console.log(r.message);
    }
});
```

#### Get Categories
```javascript
// GET /api/method/restaurant_pos.api.menu.get_categories
frappe.call({
    method: 'restaurant_pos.api.menu.get_categories',
    args: { branch: 'Main Branch' }
});
```

### Order APIs

#### Create Order
```javascript
// POST /api/method/restaurant_pos.api.order.create_order
frappe.call({
    method: 'restaurant_pos.api.order.create_order',
    args: {
        table: 'TABLE-001',
        order_type: 'Dine In',
        items: [
            {
                menu_item: 'ITEM-001',
                qty: 2,
                notes: 'No onions'
            }
        ]
    }
});
```

#### Update Order Status
```javascript
// POST /api/method/restaurant_pos.api.order.update_status
frappe.call({
    method: 'restaurant_pos.api.order.update_status',
    args: {
        order: 'ORD-00001',
        status: 'Completed'
    }
});
```

### Kitchen APIs

#### Get Kitchen Orders
```javascript
// GET /api/method/restaurant_pos.api.kitchen.get_orders
frappe.call({
    method: 'restaurant_pos.api.kitchen.get_orders',
    args: {
        station: 'Main Kitchen',
        status: 'Pending'
    }
});
```

#### Update Kitchen Order Status
```javascript
// POST /api/method/restaurant_pos.api.kitchen.update_order_status
frappe.call({
    method: 'restaurant_pos.api.kitchen.update_order_status',
    args: {
        kitchen_order: 'KO-00001',
        status: 'Ready'
    }
});
```

### Table APIs

#### Get Table Status
```javascript
// GET /api/method/restaurant_pos.api.table.get_status
frappe.call({
    method: 'restaurant_pos.api.table.get_status',
    args: { table: 'TABLE-001' }
});
```

#### Generate QR Code
```javascript
// POST /api/method/restaurant_pos.api.table.generate_qr
frappe.call({
    method: 'restaurant_pos.api.table.generate_qr',
    args: { table: 'TABLE-001' }
});
```

### Waiter APIs

#### Create Waiter Call
```javascript
// POST /api/method/restaurant_pos.api.waiter.call_waiter
frappe.call({
    method: 'restaurant_pos.api.waiter.call_waiter',
    args: {
        table: 'TABLE-001',
        call_type: 'Service'
    }
});
```

---

## 🌐 Web Pages | صفحات الويب

### Digital Menu (/menu)
```
http://yoursite.com/menu?table=TABLE-001&lang=ar
```

**Parameters:**
- `table`: Table code or QR identifier
- `lang`: Language (ar/en)

**Features:**
- Category filtering
- Search functionality
- Item details modal
- Add to cart
- Checkout process

### Kitchen Display (/kitchen)
```
http://yoursite.com/kitchen?station=Main%20Kitchen
```

**Parameters:**
- `station`: Kitchen station name
- `branch`: Branch filter (optional)

**Features:**
- Real-time order updates
- Order cards with timers
- Status change buttons
- Priority indicators
- Sound alerts

---

## 🔄 Real-time Events | الأحداث الفورية

The system uses Socket.IO for real-time updates:

```javascript
// Listen for new orders
frappe.realtime.on('new_restaurant_order', function(data) {
    console.log('New order:', data.order);
    refreshOrders();
});

// Listen for order status changes
frappe.realtime.on('order_status_changed', function(data) {
    console.log('Order updated:', data.order, data.status);
    updateOrderCard(data.order);
});

// Listen for waiter calls
frappe.realtime.on('waiter_call', function(data) {
    console.log('Waiter called at table:', data.table);
    showNotification(data);
});
```

---

## 🛠️ Installation | التثبيت

### Prerequisites
- Frappe Bench v15+
- ERPNext v15+
- Python 3.10+
- Node.js 18+
- Redis
- MariaDB/MySQL

### Installation Steps

```bash
# 1. Get the app
bench get-app https://github.com/ahmadmdm/PosRestaurant.git

# 2. Install on your site
bench --site yoursite.com install-app restaurant_pos

# 3. Run migrations
bench --site yoursite.com migrate

# 4. Build assets
bench build --app restaurant_pos

# 5. Clear cache
bench --site yoursite.com clear-cache

# 6. Restart bench
bench restart
```

---

## ⚙️ Configuration | الإعداد

### 1. Restaurant Settings
Navigate to: **Restaurant POS > Restaurant Settings**

Configure:
- Restaurant name (English & Arabic)
- Logo
- Currency
- Tax rate
- Service charge
- Working hours
- QR ordering settings
- Printer settings

### 2. Kitchen Stations
Create stations for different kitchen areas:
- Main Kitchen (المطبخ الرئيسي)
- Grill Station (محطة الشواء)
- Drinks Bar (البار)
- Desserts (الحلويات)

### 3. Menu Setup
1. Create **Menu Categories**
2. Add **Menu Items** to categories
3. Configure **Modifiers** for customization
4. Set **Allergen** information

### 4. Table Setup
1. Create tables with numbers
2. Generate QR codes
3. Print and place on tables

---

## 📱 Usage Guide | دليل الاستخدام

<div dir="rtl">

### للعملاء (For Customers)

1. **امسح رمز QR** - Scan QR Code على الطاولة
2. **تصفح القائمة** - Browse Menu
3. **أضف العناصر للسلة** - Add Items to cart
4. **خصص طلبك** - Customize your order
5. **أرسل الطلب** - Place Order
6. **انتظر التحضير** - Wait for preparation
7. **اطلب النادل عند الحاجة** - Call Waiter if needed

### لموظفي المطبخ (For Kitchen Staff)

1. **شاهد الطلبات الواردة** - View incoming Orders
2. **ابدأ التحضير** - Start Preparing
3. **حدد جاهز للتقديم** - Mark Ready
4. **راقب أوقات الانتظار** - Track waiting Time

### للنادلين (For Waiters)

1. **راقب حالة الطاولات** - Monitor Table status
2. **سجل الطلبات** - Take Orders
3. **قدم الطلبات** - Serve Orders
4. **أتمم الدفع** - Process Payment

### للمدراء (For Managers)

1. **لوحة التحكم** - Dashboard
2. **التقارير** - Reports
3. **الإعدادات** - Settings
4. **إدارة القائمة** - Menu Management

</div>

---

## 🎨 Customization | التخصيص

### Styling
Override CSS in your custom app:
```css
/* Custom colors */
:root {
    --restaurant-primary: #e74c3c;
    --restaurant-secondary: #2ecc71;
}
```

### Adding New Features
```python
# hooks.py - Add custom events
doc_events = {
    "Restaurant Order": {
        "on_submit": "your_app.events.on_order_submit"
    }
}
```

---

## 🔧 Troubleshooting | استكشاف الأخطاء

### Common Issues

**1. QR Code not generating**
```bash
# Install qrcode library
pip install qrcode[pil]
```

**2. Real-time not working**
```bash
# Check socketio
bench --site yoursite.com enable-scheduler
supervisorctl restart all
```

**3. Kitchen display not updating**
- Check browser console for errors
- Verify Socket.IO connection
- Clear browser cache

**4. Printer not working**
- Verify printer IP/Port
- Check network connectivity
- Test with printer utility

---

## 📊 Reports | التقارير

Available reports:
- Daily Sales Report (تقرير المبيعات اليومية)
- Popular Items (العناصر الأكثر مبيعاً)
- Kitchen Performance (أداء المطبخ)
- Table Turnover (معدل دوران الطاولات)
- Waiter Performance (أداء النادلين)

---

## 📸 Screenshots | لقطات الشاشة

### Digital Menu
![Digital Menu](docs/images/digital-menu.png)

### Kitchen Display
![Kitchen Display](docs/images/kitchen-display.png)

### Order Management
![Orders](docs/images/orders.png)

---

## 🤝 Contributing | المساهمة

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License | الترخيص

MIT License - see [LICENSE](license.txt) file.

---

## 👨‍💻 Author | المؤلف

**Ahmad**
- Email: ahmad8@outlook.com
- GitHub: [@ahmadmdm](https://github.com/ahmadmdm)

---

## 🙏 Acknowledgments | شكر وتقدير

- [Frappe Framework](https://frappe.io)
- [ERPNext](https://erpnext.com)
- Open source community

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

Made with ❤️ for the restaurant industry

</div>
