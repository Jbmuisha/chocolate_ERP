from base64 import b64encode
from calendar import calendar
import csv
import io
import calendar
import os
from PIL import Image

from datetime import date, datetime, time, timedelta
from io import StringIO
from flask import Flask, Response, flash, jsonify, render_template, redirect, url_for, request, session
from sqlalchemy import func  # type: ignore
from models import  Notification, PurchaseOrder, PurchaseOrderItem, Sale, Supplier, SupplierPayment,  db, User, Product, Inventory, ProductBatch
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = '8f3d2c3e1f2b4a6d8e3d4f0a1b2c3d4e'

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/chocolate_erp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ---------------- Home & Authentication ----------------

@app.route('/')
def home():
    if 'role' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username, password=password).first()

    if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['user_image'] = user.image 
            return redirect(url_for('dashboard'))
    else:
        flash('Invalid credentials', 'error')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/layout')
def layout():
    if 'role' not in session:
        return redirect(url_for('dashboard'))
    return render_template('layout.html')

# ---------------- Dashboard ----------------


@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login'))

    today = datetime.today()

    # Set start of periods with time at midnight to be precise
    start_of_week = datetime.combine((today - timedelta(days=today.weekday())).date(), time.min)
    start_of_month = datetime.combine(today.replace(day=1).date(), time.min)

    year = today.year
    month = today.month
    last_day = calendar.monthrange(year, month)[1]
    end_of_month = datetime.combine(datetime(year, month, last_day).date(), time.max)

    start_of_year = datetime.combine(today.replace(month=1, day=1).date(), time.min)
    end_of_year = datetime.combine(today.replace(month=12, day=31).date(), time.max)

    # Fetch sales by period
    daily_sales = Sale.query.filter(func.date(Sale.sale_date) == today.date()).all()
    weekly_sales = Sale.query.filter(Sale.sale_date >= start_of_week).all()
    monthly_sales = Sale.query.filter(
        Sale.sale_date >= start_of_month,
        Sale.sale_date <= end_of_month
    ).all()

    # Quantities
    daily_total = sum(s.quantity for s in daily_sales)
    weekly_total = sum(s.quantity for s in weekly_sales)
    monthly_total = sum(s.quantity for s in monthly_sales)

    # Helper function to calculate income based on product prices
    def calculate_income(sales):
        income = 0
        for s in sales:
            product_obj = Product.query.filter_by(name=s.product).first()
            if product_obj:
                income += s.quantity * product_obj.price
        return income

    # Calculate incomes
    daily_income = calculate_income(daily_sales)
    weekly_income = calculate_income(weekly_sales)
    monthly_income = calculate_income(monthly_sales)

    # Yearly (Admin only)
    yearly_sales = []
    yearly_total = 0
    yearly_income = 0
    if session['role'] == 'admin':
        yearly_sales = Sale.query.filter(
            Sale.sale_date >= start_of_year,
            Sale.sale_date <= end_of_year
        ).all()
        yearly_total = sum(s.quantity for s in yearly_sales)
        yearly_income = calculate_income(yearly_sales)

    # Product sales by period
    def get_product_sales(start_date=None, end_date=None):
        query = db.session.query(
            Sale.product,
            func.sum(Sale.quantity).label('total_quantity')
        )
        if start_date and end_date:
            query = query.filter(Sale.sale_date >= start_date, Sale.sale_date <= end_date)
        elif start_date:
            query = query.filter(Sale.sale_date >= start_date)
        elif end_date:
            query = query.filter(Sale.sale_date <= end_date)
        query = query.group_by(Sale.product).order_by(func.sum(Sale.quantity).desc())
        return query.all()

    daily_product_sales = get_product_sales(
        start_date=datetime.combine(today.date(), time.min),
        end_date=datetime.combine(today.date(), time.max)
    )
    weekly_product_sales = get_product_sales(start_date=start_of_week)
    monthly_product_sales = get_product_sales(start_date=start_of_month, end_date=end_of_month)
    yearly_product_sales = get_product_sales(start_date=start_of_year, end_date=end_of_year) if session['role'] == 'admin' else []

    daily_labels = [p.product for p in daily_product_sales]
    daily_data = [p.total_quantity for p in daily_product_sales]

    weekly_labels = [p.product for p in weekly_product_sales]
    weekly_data = [p.total_quantity for p in weekly_product_sales]

    monthly_labels = [p.product for p in monthly_product_sales]
    monthly_data = [p.total_quantity for p in monthly_product_sales]

    yearly_labels = [p.product for p in yearly_product_sales]
    yearly_data = [p.total_quantity for p in yearly_product_sales]

    # All-time product sales
    product_sales = db.session.query(Sale.product, func.sum(Sale.quantity).label('total_quantity')) \
        .group_by(Sale.product) \
        .order_by(func.sum(Sale.quantity).desc()) \
        .all()

    labels = [sale.product for sale in product_sales]
    data = [sale.total_quantity for sale in product_sales]

    return render_template('dashboard.html',
                           role=session['role'],
                           daily_sales=daily_sales,
                           weekly_sales=weekly_sales,
                           monthly_sales=monthly_sales,
                           yearly_sales=yearly_sales,
                           daily_total=daily_total,
                           weekly_total=weekly_total,
                           monthly_total=monthly_total,
                           yearly_total=yearly_total,
                           daily_income=daily_income,
                           weekly_income=weekly_income,
                           monthly_income=monthly_income,
                           yearly_income=yearly_income,
                           labels=labels,
                           data=data,
                           daily_labels=daily_labels,
                           daily_data=daily_data,
                           weekly_labels=weekly_labels,
                           weekly_data=weekly_data,
                           monthly_labels=monthly_labels,
                           monthly_data=monthly_data,
                           yearly_labels=yearly_labels,
                           yearly_data=yearly_data)
# New API route for AJAX/live update calls
@app.route('/api/dashboard_data')
def api_dashboard_data():
    if 'role' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    daily_sales = Sale.query.filter(func.date(Sale.sale_date) == today.date()).all()
    weekly_sales = Sale.query.filter(Sale.sale_date >= start_of_week).all()
    monthly_sales = Sale.query.filter(Sale.sale_date >= start_of_month).all()

    daily_total = sum(sale.quantity for sale in daily_sales)
    weekly_total = sum(sale.quantity for sale in weekly_sales)
    monthly_total = sum(sale.quantity for sale in monthly_sales)

    yearly_sales = []
    yearly_total = 0
    if session['role'] == 'admin':
        yearly_sales = Sale.query.filter(Sale.sale_date >= start_of_year).all()
        yearly_total = sum(sale.quantity for sale in yearly_sales)

    def get_product_sales(start_date=None, end_date=None):
        query = db.session.query(
            Sale.product,
            func.sum(Sale.quantity).label('total_quantity')
        )
        if start_date and end_date:
            query = query.filter(Sale.sale_date >= start_date, Sale.sale_date <= end_date)
        elif start_date:
            query = query.filter(Sale.sale_date >= start_date)
        elif end_date:
            query = query.filter(Sale.sale_date <= end_date)
        query = query.group_by(Sale.product).order_by(func.sum(Sale.quantity).desc())
        return query.all()

    daily_product_sales = get_product_sales(start_date=today.replace(hour=0, minute=0, second=0, microsecond=0), end_date=today)
    weekly_product_sales = get_product_sales(start_date=start_of_week)
    monthly_product_sales = get_product_sales(start_date=start_of_month)
    yearly_product_sales = get_product_sales(start_date=start_of_year) if session['role'] == 'admin' else []

    # Convert Sale objects to dicts for JSON serialization
    def serialize_sales(sales):
        return [
            {
                'product': sale.product,
                'quantity': sale.quantity,
                'sale_date': sale.sale_date.strftime('%Y-%m-%d %H:%M:%S')
            } for sale in sales
        ]

    return jsonify({
        'daily_total': daily_total,
        'weekly_total': weekly_total,
        'monthly_total': monthly_total,
        'yearly_total': yearly_total,
        'labels': [sale.product for sale in get_product_sales()],
        'data': [sale.total_quantity for sale in get_product_sales()],
        'daily_labels': [p.product for p in daily_product_sales],
        'daily_data': [p.total_quantity for p in daily_product_sales],
        'weekly_labels': [p.product for p in weekly_product_sales],
        'weekly_data': [p.total_quantity for p in weekly_product_sales],
        'monthly_labels': [p.product for p in monthly_product_sales],
        'monthly_data': [p.total_quantity for p in monthly_product_sales],
        'yearly_labels': [p.product for p in yearly_product_sales],
        'yearly_data': [p.total_quantity for p in yearly_product_sales],
        'daily_sales': serialize_sales(daily_sales),
        'weekly_sales': serialize_sales(weekly_sales),
        'monthly_sales': serialize_sales(monthly_sales),
        'yearly_sales': serialize_sales(yearly_sales),
    })


# ---------------- User Management ----------------
ALLOWED_MIMES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
UPLOAD_FOLDER = 'static/uploads/users'

def get_image_mime(image_data):
    try:
        image = Image.open(io.BytesIO(image_data))
        fmt = image.format.lower()
        if fmt == 'jpeg':
            return 'image/jpeg'
        elif fmt == 'png':
            return 'image/png'
        elif fmt == 'gif':
            return 'image/gif'
        elif fmt == 'webp':
            return 'image/webp'
        else:
            return 'application/octet-stream'
    except Exception:
        return 'application/octet-stream'

@app.route('/manage_user')
def manage_users():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('manage_user.html', users=users)

@app.route('/add_user', methods=['POST'])
def add_user():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    image_file = request.files.get('image')
    filename = None

    if image_file:
        image_data = image_file.read()
        mime_type = get_image_mime(image_data)

        if mime_type in ALLOWED_MIMES:
            filename = secure_filename(image_file.filename) # type: ignore
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            with open(file_path, 'wb') as f:
                f.write(image_data)
        else:
            flash('Invalid image format.', 'error')
            return redirect(url_for('manage_users'))

    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
    else:
        user = User(username=username, password=password, role=role, image=filename)
        db.session.add(user)
        db.session.commit()
        flash('User added successfully!', 'success')

    return redirect(url_for('manage_users'))

@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.username = request.form.get('username')
        user.role = request.form.get('role')

        image_file = request.files.get('image')
        if image_file:
            image_data = image_file.read()
            mime_type = get_image_mime(image_data)

            if mime_type in ALLOWED_MIMES:
                filename = secure_filename(image_file.filename) # type: ignore
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                user.image = filename
            else:
                flash('Invalid image format.', 'error')
                return redirect(url_for('manage_users'))

        db.session.commit()
        flash('User updated successfully!', 'success')

    return redirect(url_for('manage_users'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        if user.image:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, user.image))
            except Exception:
                pass
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully!', 'success')

    return redirect(url_for('manage_users'))


@app.route('/sale_report')
def salereport():
     if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
     sales = Sale.query.order_by(Sale.sale_date.desc()).all()
     return render_template('salesreport.html', sales=sales) 
@app.route('/record')
def record():
    if 'role' not in session:
        return redirect(url_for('login'))
    
    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    return render_template('record.html', sales=sales)


@app.route('/submit_sale', methods=['POST'])
def submit_sale():
    if 'role' not in session or session['role'] != 'employee':
        return redirect(url_for('login'))

    product_name = request.form['product_name']
    quantity = int(request.form['quantity'])
    payment_method = request.form['payment_method']
    customer = request.form.get('customer', '')

    # Find inventory item by name
    inventory_item = Inventory.query.filter_by(name=product_name).first()
    if not inventory_item:
        flash(f'Product "{product_name}" not found in inventory.', 'error')
        return redirect(url_for('record'))

    if inventory_item.quantity < quantity:
        flash(f'Not enough stock for "{product_name}". Current stock: {inventory_item.quantity}', 'error')
        return redirect(url_for('record'))

    # Reduce inventory quantity
    inventory_item.quantity -= quantity
    inventory_item.updated_at = date.today()  # update the date

    # Record the sale
    sale = Sale(
        product=product_name,
        quantity=quantity,
        payment_method=payment_method,
        customer=customer
    )

    try:
        db.session.add(sale)
        db.session.commit()
        flash('Sale recorded and inventory updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording sale: {str(e)}', 'error')

    return redirect(url_for('record'))

@app.route('/edit_sale/<int:sale_id>', methods=['GET', 'POST'])
def edit_sale(sale_id):
    if 'role' not in session or session['role'] != 'employee':
        return redirect(url_for('login'))

    sale = Sale.query.get_or_404(sale_id)

    if request.method == 'POST':
        sale.product = request.form['product_name']
        sale.quantity = int(request.form['quantity'])
        sale.payment_method = request.form['payment_method']
        sale.customer = request.form.get('customer', '')
        db.session.commit()
        flash('Sale updated successfully!', 'success')
        return redirect(url_for('record'))

    # GET request: Render form prefilled with existing data for editing
    return render_template('edit_sale.html', sale=sale)


@app.route('/delete_sale/<int:sale_id>', methods=['POST'])
def delete_sale(sale_id):
    if 'role' not in session or session['role'] != 'employee':
        return redirect(url_for('login'))

    sale = Sale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()
    flash('Sale deleted successfully!', 'success')
    return redirect(url_for('record'))

# ---------------- Product List ----------------
def get_image_mime(image_data):
    try:
        image = Image.open(io.BytesIO(image_data))
        fmt = image.format.lower()
        if fmt == 'jpeg':
            return 'image/jpeg'
        elif fmt == 'webp':
            return 'image/webp'
        else:
            return 'application/octet-stream'
    except Exception:
        return 'application/octet-stream'

@app.route('/product-list', methods=['GET'])
def product_list():
    category = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'name')

    query = Product.query
    if category != 'all':
        query = query.filter(Product.category == category)

    if sort_by == 'price':
        query = query.order_by(Product.price)
    else:
        query = query.order_by(Product.name)

    products = query.all()

    for product in products:
        if product.image_data:
            product.image_mime = get_image_mime(product.image_data)
            product.image_base64 = b64encode(product.image_data).decode('utf-8')
        else:
            product.image_mime = None
            product.image_base64 = None

    return render_template('chocolate.html', products=products, category=category, sort_by=sort_by)


@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        price = request.form.get('price')
        image_file = request.files.get('image')

        if not name or not category or not price:
            flash('Please fill all required fields.', 'error')
            return redirect(url_for('add_product'))

        try:
            price = float(price)
        except ValueError:
            flash('Price must be a number.', 'error')
            return redirect(url_for('add_product'))

        image_data = None
        if image_file:
            if image_file.mimetype not in ['image/jpeg', 'image/webp']:
                flash('Image must be JPEG or WEBP.', 'error')
                return redirect(url_for('add_product'))
            image_data = image_file.read()

        new_product = Product(
            name=name,
            category=category,
            price=price,
            image_data=image_data
        )
        db.session.add(new_product)
        db.session.flush()  # Get new_product.id if needed before commit

        notification_message = f'New product "{name}" added.'
        notification = Notification(
            message=notification_message,
            for_admin=True,
            url=url_for('product_list')
        )
        db.session.add(notification)
        db.session.commit()

        flash(f'Product "{name}" added successfully!', 'success')
        return redirect(url_for('product_list'))

    return render_template('add_product.html')



    

@app.route('/view_sales_reports')
def view_sales_reports():
    if 'role' not in session or session['role'] != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))

    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    return render_template('view_sales_reports.html', sales=sales)

@app.route('/download_sales_csv')
def download_sales_csv():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    sales = Sale.query.order_by(Sale.sale_date.desc()).all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Product', 'Quantity', 'Payment Method', 'Customer', 'Date'])

    for sale in sales:
        writer.writerow([
            sale.id,
            sale.product,
            sale.quantity,
            sale.payment_method,
            sale.customer or '-',
            sale.sale_date.strftime('%Y-%m-%d %H:%M')
        ])

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=sales_report.csv"}
    )

# ---------------- Inventory Management ----------------




@app.route('/view_inventory')
def view_inventory():
    if 'role' not in session:
        return redirect(url_for('dashboard'))

    inventory_items = Inventory.query.all()
    return render_template("inventory.html", items=inventory_items)

from datetime import date

@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    if 'role' not in session or session['role'] != 'employee':
        flash("Unauthorized access", "error")
        return redirect('/')

    if request.method == 'POST':
        item_id = request.form.get('item_id')
        name = request.form['product_name']
        category = request.form['category']
        quantity = int(request.form['quantity'])
        price = float(request.form['price'])
        location = request.form['location']
        notes = request.form['notes']

        if item_id:
            # Update existing inventory item
            item = Inventory.query.get_or_404(item_id)
            item.name = name
            item.category = category
            item.quantity = quantity
            item.price = price
            item.location = location
            item.notes = notes
            item.updated_at = date.today()
            flash("Inventory updated successfully", "success")

            # Notification message for update
            notif_message = f'Inventory item "{name}" updated by employee.'
        else:
            # Add new inventory item
            item = Inventory(
                name=name,
                category=category,
                quantity=quantity,
                price=price,
                location=location,
                notes=notes,
                updated_at=date.today()
            )
            db.session.add(item)
            flash("Inventory added successfully", "success")

            # Notification message for addition
            notif_message = f'New inventory item "{name}" added by employee.'

        # Add notification entry with URL to view_inventory
        notification = Notification(
            message=notif_message,
            for_admin=True,
            url=url_for('view_inventory')
        )
        db.session.add(notification)

        # Commit inventory and notification together
        db.session.commit()

        return redirect(url_for('add_inventory'))

    inventory = Inventory.query.order_by(Inventory.updated_at.desc()).all()
    return render_template('add_inventory.html', inventory=inventory)

@app.route('/delete_inventory/<int:item_id>', methods=['POST'])
def delete_inventory(item_id):
    item = Inventory.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Inventory deleted successfully", "success")
    return redirect(url_for('add_inventory'))

@app.route('/edit_inventory/<int:item_id>')
def edit_inventory(item_id):
    item_to_edit = Inventory.query.get_or_404(item_id)
    inventory = Inventory.query.order_by(Inventory.updated_at.desc()).all()
    return render_template('add_inventory.html', inventory=inventory, item_to_edit=item_to_edit)

# ---------------- Product Batch Management ----------------

@app.route('/product_batches', methods=['GET', 'POST'])
def product_batches():
    edit_id = request.args.get('edit_id')
    batch_to_edit = ProductBatch.query.get_or_404(edit_id) if edit_id else None

    if request.method == 'POST':
        if request.form.get('edit_id'):
            batch = ProductBatch.query.get_or_404(request.form['edit_id'])
            batch.batch_code = request.form['batch_code']
            batch.product_name = request.form['product_name']
            batch.production_date = request.form['production_date']
            batch.expiry_date = request.form['expiry_date']
            batch.quantity = request.form['quantity']
            db.session.commit()
            flash('Batch updated successfully!', 'success')
        else:
            new_batch = ProductBatch(
                batch_code=request.form['batch_code'],
                product_name=request.form['product_name'],
                production_date=request.form['production_date'],
                expiry_date=request.form['expiry_date'],
                quantity=request.form['quantity'],
                created_at=date.today()
            )
            db.session.add(new_batch)
            db.session.commit()
            flash('New batch added successfully!', 'success')

        return redirect(url_for('product_batches'))

    batches = ProductBatch.query.order_by(ProductBatch.created_at.desc()).all()
    return render_template('product_batches.html', batches=batches, batch_to_edit=batch_to_edit)

@app.route('/delete-batch/<int:batch_id>', methods=['GET'])
def delete_batch(batch_id):
    batch = ProductBatch.query.get_or_404(batch_id)
    db.session.delete(batch)
    db.session.commit()
    flash('Batch deleted successfully!', 'success')
    return redirect(url_for('product_batches'))

# ---------------- Supplier Management ----------------

@app.route('/supplier', methods=['GET', 'POST'])
def manage_supplier():
    if 'role' not in session or session['role'] != 'admin':
        flash('You must be an admin to access this page.', 'error')
        return redirect(url_for('home'))

    edit_supplier = None
    if 'supplier_id' in request.args:
        edit_supplier = Supplier.query.get(request.args.get('supplier_id'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        email = request.form['email']
        supplier_id = request.form.get('supplier_id')

        if supplier_id:
            supplier = Supplier.query.get(supplier_id)
            supplier.name = name
            supplier.address = address
            supplier.phone = phone
            supplier.email = email
        else:
            supplier = Supplier(name=name, address=address, phone=phone, email=email)
            db.session.add(supplier)

        db.session.commit()
        flash('Supplier updated successfully!' if supplier_id else 'Supplier added successfully!', 'success')
        return redirect(url_for('manage_supplier'))

    suppliers = Supplier.query.all()
 
    return render_template('supplier.html', suppliers=suppliers, edit_supplier=edit_supplier)

@app.route('/purchase_orders', methods=['GET', 'POST'])
def purchase_orders():
    if request.method == 'POST':
        supplier_id = request.form['supplier_id']
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')

        if not product_ids or not quantities or not unit_prices:
            flash('Please add at least one purchase order item.', 'error')
            return redirect(url_for('purchase_orders'))

        purchase_order = PurchaseOrder(supplier_id=supplier_id, total_amount=0)
        db.session.add(purchase_order)
        db.session.flush()  # To get purchase_order.id before commit

        total_amount = 0
        for pid, qty, price in zip(product_ids, quantities, unit_prices):
            try:
                qty = int(qty)
                price = float(price)
            except ValueError:
                flash('Quantity and unit price must be numbers.', 'error')
                return redirect(url_for('purchase_orders'))

            total_amount += qty * price
            item = PurchaseOrderItem(
                purchase_order_id=purchase_order.id,
                product_id=pid,
                quantity=qty,
                unit_price=price
            )
            db.session.add(item)

        purchase_order.total_amount = total_amount

        # Create notification with URL pointing to purchase_orders page
        notification_message = f"New purchase order #{purchase_order.id} created."
        notification = Notification(
            message=notification_message,
            for_admin=True,
            url=url_for('purchase_orders')
        )
        db.session.add(notification)

        db.session.commit()  # commit purchase order, items, and notification at once

        flash('Purchase order created successfully', 'success')
        return redirect(url_for('purchase_orders'))


    suppliers = Supplier.query.all()
    products = Product.query.all()
    purchase_orders = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()
    return render_template(
        'purchase_order.html',
        suppliers=suppliers,
        products=products,
        purchase_orders=purchase_orders
    )
@app.route('/supplier_payments', methods=['GET', 'POST'])
def supplier_payments():
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes')

        if not supplier_id or not amount:
            flash("Supplier and amount are required", "error")
            return redirect('/supplier_payments')

        try:
            amount = float(amount)
            new_payment = SupplierPayment(
                supplier_id=int(supplier_id),
                amount=amount,
                payment_method=payment_method.strip() if payment_method else None,
                notes=notes.strip() if notes else None,
                payment_date=datetime.utcnow()
            )
            db.session.add(new_payment)
            db.session.commit()
            flash("Supplier payment recorded successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving payment: {str(e)}", "error")

        return redirect('/supplier_payments')

    suppliers = Supplier.query.order_by(Supplier.name).all()
    supplier_payments = SupplierPayment.query.order_by(SupplierPayment.payment_date.desc()).all()
    return render_template('supplier_payments.html', suppliers=suppliers, supplier_payments=supplier_payments)
@app.route('/pur_orders')
def purchase_orders_view():
    purchase_orders = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()
    return render_template('purchase_orders_view.html', purchase_orders=purchase_orders)

@app.route('/s_payments')
def supplier_payments_view():
    supplier_payments = SupplierPayment.query.order_by(SupplierPayment.payment_date.desc()).all()
    return render_template('supplier_payments_view.html', supplier_payments=supplier_payments)

@app.route('/inventory_report', methods=['GET', 'POST'])
def inventory_report():
    if 'role' not in session:
        flash("Please login to access reports.", "error")
        return redirect(url_for('login'))

    filters = {
        'category': request.form.get('category'),
        'location': request.form.get('location'),
        'from_date': request.form.get('from_date'),
        'to_date': request.form.get('to_date'),
        'report_type': request.form.get('report_type')
    }

    query = Inventory.query

    if filters['category']:
        query = query.filter_by(category=filters['category'])

    if filters['location']:
        query = query.filter_by(location=filters['location'])

    if filters['from_date'] and filters['to_date']:
        try:
            from_date = datetime.strptime(filters['from_date'], '%Y-%m-%d').date()
            to_date = datetime.strptime(filters['to_date'], '%Y-%m-%d').date()
            query = query.filter(Inventory.updated_at.between(from_date, to_date))
        except ValueError:
            flash("Invalid date format", "error")

    if filters['report_type'] == 'low_stock':
        query = query.filter(Inventory.quantity <= 10)

    inventory_items = query.order_by(Inventory.updated_at.desc()).all()

    # Unique categories and locations
    categories = [c[0] for c in db.session.query(Inventory.category).distinct().all()]
    locations = [l[0] for l in db.session.query(Inventory.location).distinct().all()]

    return render_template("inventory_report.html",
                           items=inventory_items,
                           filters=filters,
                           categories=categories,
                           locations=locations)
FAQs = [
    {"question": "How do I record a sale?", "answer": "Navigate to the 'Record Sale' page and fill out the form with product and payment details."},
    {"question": "How to add new products?", "answer": "Use the 'Add Product' option in the sidebar to create new product entries."},
    {"question": "How can I view reports?", "answer": "Admins can generate reports from the 'Generate Reports' section in the sidebar."},
    {"question": "How do I manage users?", "answer": "Admins can add, edit, or delete users from the 'Manage Users' page accessible via the sidebar."},
    {"question": "How do I update inventory quantities?", "answer": "Go to 'Add Inventory' or 'View Inventory' to update stock levels for your products."},
    {"question": "What roles are available and what permissions do they have?", "answer": "There are two roles: Admins who have full access, and Employees who have limited access such as recording sales and managing batches."},
    {"question": "How do I switch between light and dark mode?", "answer": "Click the moon icon in the top navigation bar to toggle between light and dark themes."},
    {"question": "Can I access the system from a mobile device?", "answer": "Yes, the interface is responsive and the sidebar can be toggled with the menu button on smaller screens."},
    {"question": "How do I log out securely?", "answer": "Use the 'Logout' link in the sidebar to safely end your session."},
    {"question": "Who do I contact for technical support?", "answer": "You can submit a question here in the Help & Support section or contact your system administrator."},
]

@app.route('/help_support', methods=['GET', 'POST'])
def help_support():
    if request.method == 'POST':
    
        name = request.form.get('name')
        email = request.form.get('email')
        question = request.form.get('question')

        
        if not name or not email or not question:
            flash("Please fill in all fields.", "error")
            return redirect(url_for('help_support'))

        
        flash("Your question has been received! We'll get back to you soon.", "success")
        return redirect(url_for('help_support'))

    return render_template('help_support.html', faqs=FAQs)
@app.route('/delete_supplier/<int:supplier_id>')
def delete_supplier(supplier_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('You must be an admin to access this page.', 'error')
        return redirect(url_for('home'))

    supplier = Supplier.query.get(supplier_id)
    if supplier:
        db.session.delete(supplier)
        db.session.commit()
        flash('Supplier deleted successfully!', 'success')
    return redirect(url_for('manage_supplier'))

@app.context_processor
def inject_notifications():
    notifications = []
    user_role = session.get('role')

    if user_role == 'admin':
        notifications = Notification.query.filter_by(
            for_admin=True, is_read=False
        ).order_by(Notification.created_at.desc()).all()
    elif user_role == 'employee':
        notifications = Notification.query.filter_by(
            for_employee=True, is_read=False
        ).order_by(Notification.created_at.desc()).all()

    return dict(notifications=notifications)


# Example notification structure (unchanged)
def get_notifications():
    return [
        {
            "message": "New purchase order created",
            "created_at": datetime.utcnow(),
            "url": url_for('purchase_orders')
        },
        {
            "message": "New inventory has been added",
            "created_at": datetime.utcnow(),
            "url": url_for('view_inventory')
        },
        {
            "message": "New product has been  added",
            "created_at": datetime.utcnow(),
            "url": url_for('product-list')
        },
    ]


@app.route('/notifications/mark_read/<int:notif_id>', methods=['POST'])
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    notif.is_read = True
    db.session.commit()
    return jsonify(success=True)

# ---------------- Run the App ----------------
if __name__ == '__main__':
    app.run(debug=True)
