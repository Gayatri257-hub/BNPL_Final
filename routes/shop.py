from flask import (Blueprint, abort, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_login import login_required

shop_bp = Blueprint('shop', __name__)

PRODUCTS = [
    # ── Electronics (10) ──
    {'id': 1,  'name': 'OnePlus Buds Pro',           'category': 'Electronics',    'price': 4999,  'original_price': 7999,  'rating': 4.5, 'image_seed': 'tech1',    'description': 'Premium wireless earbuds with Active Noise Cancellation and 28hr battery'},
    {'id': 2,  'name': 'realme Smart TV 32"',         'category': 'Electronics',    'price': 15999, 'original_price': 19999, 'rating': 4.3, 'image_seed': 'tech2',    'description': 'Full HD Android TV with bezel-less display and Dolby Audio'},
    {'id': 3,  'name': 'boAt Rockerz 450 Headphones', 'category': 'Electronics',   'price': 1299,  'original_price': 2999,  'rating': 4.2, 'image_seed': 'tech3',    'description': 'Wireless headphones with 15hr playback and powerful 40mm drivers'},
    {'id': 4,  'name': 'Portronics Power Bank',       'category': 'Electronics',    'price': 999,   'original_price': 1999,  'rating': 4.1, 'image_seed': 'tech4',    'description': '20000mAh fast-charging power bank with dual USB output'},
    {'id': 5,  'name': 'JBL Flip 6 Speaker',          'category': 'Electronics',    'price': 8499,  'original_price': 11999, 'rating': 4.6, 'image_seed': 'tech5',    'description': 'Portable waterproof Bluetooth speaker with 12hr playtime'},
    {'id': 6,  'name': 'Logitech MX Master Mouse',    'category': 'Electronics',    'price': 6499,  'original_price': 9999,  'rating': 4.7, 'image_seed': 'tech6',    'description': 'Advanced wireless mouse with ultra-fast scrolling for professionals'},
    {'id': 7,  'name': 'HP Wireless Keyboard',        'category': 'Electronics',    'price': 1799,  'original_price': 2999,  'rating': 4.2, 'image_seed': 'tech7',    'description': 'Slim quiet-key wireless keyboard with 2-year battery life'},
    {'id': 8,  'name': 'Anker USB-C Hub',              'category': 'Electronics',   'price': 2499,  'original_price': 3999,  'rating': 4.4, 'image_seed': 'tech8',    'description': '7-in-1 USB-C hub with HDMI 4K, 100W PD, and SD card reader'},
    {'id': 9,  'name': 'Samsung 25W Charger',          'category': 'Electronics',   'price': 1299,  'original_price': 1999,  'rating': 4.3, 'image_seed': 'tech9',    'description': 'Super Fast 25W USB-C charger compatible with Samsung Galaxy series'},
    {'id': 10, 'name': 'MI Smart Band 8',              'category': 'Electronics',   'price': 2999,  'original_price': 4999,  'rating': 4.5, 'image_seed': 'tech10',   'description': 'AMOLED fitness tracker with SpO2, heart rate, and 16-day battery'},
    # ── Fashion (10) ──
    {'id': 11, 'name': "Levi's 511 Slim Jeans",       'category': 'Fashion',        'price': 3499,  'original_price': 5999,  'rating': 4.4, 'image_seed': 'fashion1', 'description': 'Classic slim-fit stretch denim jeans in indigo wash'},
    {'id': 12, 'name': 'Puma Running Shoes',           'category': 'Fashion',        'price': 2799,  'original_price': 4499,  'rating': 4.3, 'image_seed': 'fashion2', 'description': 'Lightweight mesh running shoes with SoftFoam+ cushioning'},
    {'id': 13, 'name': 'H&M Summer Dress',             'category': 'Fashion',        'price': 1599,  'original_price': 2499,  'rating': 4.0, 'image_seed': 'fashion3', 'description': 'Flowy printed summer dress in breathable cotton blend'},
    {'id': 14, 'name': 'Ray-Ban Aviator Sunglasses',   'category': 'Fashion',        'price': 5499,  'original_price': 8999,  'rating': 4.7, 'image_seed': 'fashion4', 'description': 'Classic polarized aviator sunglasses with UV400 protection'},
    {'id': 15, 'name': 'Fossil Gen 6 Smartwatch',      'category': 'Fashion',        'price': 12999, 'original_price': 19999, 'rating': 4.4, 'image_seed': 'fashion5', 'description': 'Wear OS smartwatch with heart rate, GPS, and speaker'},
    {'id': 16, 'name': 'Nike Air Max Sneakers',        'category': 'Fashion',        'price': 7999,  'original_price': 12999, 'rating': 4.6, 'image_seed': 'fashion6', 'description': 'Iconic Air Max cushioning sneakers with breathable upper'},
    {'id': 17, 'name': 'Zara Casual Shirt',            'category': 'Fashion',        'price': 1999,  'original_price': 3499,  'rating': 4.1, 'image_seed': 'fashion7', 'description': 'Premium cotton relaxed-fit casual shirt for everyday wear'},
    {'id': 18, 'name': 'Titan Edge Watch',             'category': 'Fashion',        'price': 8499,  'original_price': 12999, 'rating': 4.5, 'image_seed': 'fashion8', 'description': "World's slimmest watch with sapphire crystal and leather strap"},
    {'id': 19, 'name': 'UCB Leather Belt',             'category': 'Fashion',        'price': 1299,  'original_price': 2499,  'rating': 4.2, 'image_seed': 'fashion9', 'description': 'Premium genuine leather belt with silver-tone buckle'},
    {'id': 20, 'name': 'Adidas Backpack',              'category': 'Fashion',        'price': 2999,  'original_price': 4999,  'rating': 4.3, 'image_seed': 'fashion10','description': 'Sporty 30L backpack with laptop compartment and water resistance'},
    # ── Books (5) ──
    {'id': 21, 'name': 'Atomic Habits',                'category': 'Books',          'price': 499,   'original_price': 799,   'rating': 4.9, 'image_seed': 'book1',    'description': "James Clear's guide to building great habits and breaking bad ones"},
    {'id': 22, 'name': 'Rich Dad Poor Dad',            'category': 'Books',          'price': 399,   'original_price': 599,   'rating': 4.7, 'image_seed': 'book2',    'description': 'Robert Kiyosaki on financial literacy and wealth building'},
    {'id': 23, 'name': 'The Alchemist',                'category': 'Books',          'price': 299,   'original_price': 499,   'rating': 4.8, 'image_seed': 'book3',    'description': "Paulo Coelho's timeless story of following your personal legend"},
    {'id': 24, 'name': 'Wings of Fire',                'category': 'Books',          'price': 349,   'original_price': 499,   'rating': 4.9, 'image_seed': 'book4',    'description': 'Autobiography of APJ Abdul Kalam — a story of vision and perseverance'},
    {'id': 25, 'name': 'Zero to One',                  'category': 'Books',          'price': 599,   'original_price': 899,   'rating': 4.7, 'image_seed': 'book5',    'description': "Peter Thiel's notes on startups and how to build the future"},
    # ── Home & Kitchen (8) ──
    {'id': 26, 'name': 'Philips Air Purifier',         'category': 'Home & Kitchen', 'price': 8999,  'original_price': 12999, 'rating': 4.3, 'image_seed': 'home1',    'description': 'True HEPA air purifier removing 99.97% pollutants for rooms up to 333 sq ft'},
    {'id': 27, 'name': 'Prestige Induction Cooktop',   'category': 'Home & Kitchen', 'price': 2199,  'original_price': 3499,  'rating': 4.2, 'image_seed': 'home2',    'description': 'Smart induction cooktop with 8 preset menus and anti-magnetic wall'},
    {'id': 28, 'name': 'Wonderchef Nutri-blend',       'category': 'Home & Kitchen', 'price': 3499,  'original_price': 4999,  'rating': 4.4, 'image_seed': 'home3',    'description': '400W powerful blender with stainless steel blades and travel bottle'},
    {'id': 29, 'name': 'Milton Water Bottle Set',      'category': 'Home & Kitchen', 'price': 899,   'original_price': 1499,  'rating': 4.2, 'image_seed': 'home4',    'description': 'Set of 3 insulated stainless steel water bottles (500ml, 750ml, 1L)'},
    {'id': 30, 'name': 'Pigeon Electric Kettle',       'category': 'Home & Kitchen', 'price': 799,   'original_price': 1299,  'rating': 4.3, 'image_seed': 'home5',    'description': '1.5L BPA-free electric kettle with auto shut-off and boil-dry protection'},
    {'id': 31, 'name': 'Cello Bedsheet Set',           'category': 'Home & Kitchen', 'price': 1299,  'original_price': 2199,  'rating': 4.1, 'image_seed': 'home6',    'description': 'Premium 300TC cotton bedsheet set with 2 pillow covers'},
    {'id': 32, 'name': 'Bajaj Room Heater',            'category': 'Home & Kitchen', 'price': 2499,  'original_price': 3999,  'rating': 4.2, 'image_seed': 'home7',    'description': '2000W fan room heater with 2 heat settings and overheat protection'},
    {'id': 33, 'name': 'Havells Table Fan',            'category': 'Home & Kitchen', 'price': 1799,  'original_price': 2999,  'rating': 4.3, 'image_seed': 'home8',    'description': '400mm table fan with 3-speed control and oscillation feature'},
    # ── Sports (7) ──
    {'id': 34, 'name': 'Nivia Football Size 5',        'category': 'Sports',         'price': 699,   'original_price': 1199,  'rating': 4.1, 'image_seed': 'sport1',   'description': 'FIFA-approved PU leather football for professional and training use'},
    {'id': 35, 'name': 'Boldfit Yoga Mat',             'category': 'Sports',         'price': 899,   'original_price': 1599,  'rating': 4.3, 'image_seed': 'sport2',   'description': '6mm thick anti-skid TPE yoga mat with alignment lines'},
    {'id': 36, 'name': 'Cosco Badminton Set',          'category': 'Sports',         'price': 1499,  'original_price': 2499,  'rating': 4.2, 'image_seed': 'sport3',   'description': 'Professional badminton set with 2 rackets, 3 shuttlecocks and carry bag'},
    {'id': 37, 'name': 'Decathlon Cycling Gloves',     'category': 'Sports',         'price': 599,   'original_price': 999,   'rating': 4.0, 'image_seed': 'sport4',   'description': 'Padded gel cycling gloves with anti-slip grip and breathable mesh'},
    {'id': 38, 'name': 'Vector X Cricket Bat',         'category': 'Sports',         'price': 2499,  'original_price': 3999,  'rating': 4.2, 'image_seed': 'sport5',   'description': 'English willow cricket bat Grade 3 with full cane handle'},
    {'id': 39, 'name': 'Adidas Football Shoes',        'category': 'Sports',         'price': 3999,  'original_price': 6499,  'rating': 4.4, 'image_seed': 'sport6',   'description': 'FG football boots with conical studs for natural grass performance'},
    {'id': 40, 'name': 'Cosco Volleyball',             'category': 'Sports',         'price': 799,   'original_price': 1299,  'rating': 4.1, 'image_seed': 'sport7',   'description': 'Rubber volleyball with 18-panel design for indoor and outdoor play'},
]


@shop_bp.route('/')
@login_required
def index():
    category = request.args.get('category', 'All')
    search_q  = request.args.get('q', '').strip().lower()
    sort_by   = request.args.get('sort', 'default')

    categories = ['All'] + sorted(set(p['category'] for p in PRODUCTS))
    products = PRODUCTS if category == 'All' else [p for p in PRODUCTS if p['category'] == category]
    if search_q:
        products = [p for p in products if search_q in p['name'].lower() or search_q in p['category'].lower()]

    if sort_by == 'price_asc':
        products = sorted(products, key=lambda p: p['price'])
    elif sort_by == 'price_desc':
        products = sorted(products, key=lambda p: p['price'], reverse=True)
    elif sort_by == 'rating':
        products = sorted(products, key=lambda p: p['rating'], reverse=True)
    elif sort_by == 'discount':
        products = sorted(products, key=lambda p: p['original_price'] - p['price'], reverse=True)

    trending = sorted(PRODUCTS, key=lambda p: p['rating'], reverse=True)[:4]
    return render_template('shop/index.html', products=products, categories=categories,
                           selected_category=category, trending=trending,
                           search_q=search_q, sort_by=sort_by)


@shop_bp.route('/product/<int:product_id>')
@login_required
def product(product_id):
    prod = next((p for p in PRODUCTS if p['id'] == product_id), None)
    if not prod:
        abort(404)
    related = [p for p in PRODUCTS if p['category'] == prod['category'] and p['id'] != product_id][:4]
    return render_template('shop/product.html', product=prod, related=related)


@shop_bp.route('/cart')
@login_required
def cart():
    cart_items = session.get('cart', [])
    enriched = []
    for item in cart_items:
        prod = next((p for p in PRODUCTS if p['id'] == item['id']), None)
        if prod:
            enriched.append({**prod, 'quantity': item['quantity']})
    subtotal = sum(p['price'] * p['quantity'] for p in enriched)
    savings  = sum((p['original_price'] - p['price']) * p['quantity'] for p in enriched)
    gst      = round(subtotal * 0.18, 2)
    total    = round(subtotal + gst, 2)
    return render_template('shop/cart.html', cart_items=enriched, subtotal=subtotal,
                           gst=gst, total=total, savings=savings)


@shop_bp.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = int(data.get('product_id'))
    quantity   = int(data.get('quantity', 1))
    cart = session.get('cart', [])
    existing = next((item for item in cart if item['id'] == product_id), None)
    if existing:
        existing['quantity'] += quantity
    else:
        cart.append({'id': product_id, 'quantity': quantity})
    session['cart'] = cart
    session.modified = True
    return jsonify({'success': True, 'cart_count': sum(i['quantity'] for i in cart)})


@shop_bp.route('/remove-from-cart', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.get_json()
    product_id = int(data.get('product_id'))
    cart = session.get('cart', [])
    session['cart'] = [item for item in cart if item['id'] != product_id]
    session.modified = True
    return jsonify({'success': True})


@shop_bp.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    product_id = int(data.get('product_id'))
    quantity   = int(data.get('quantity', 1))
    cart = session.get('cart', [])
    for item in cart:
        if item['id'] == product_id:
            item['quantity'] = max(1, quantity)
            break
    session['cart'] = cart
    session.modified = True
    return jsonify({'success': True})
