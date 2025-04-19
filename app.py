from flask import Flask, render_template, request, redirect, jsonify
from db_connection import get_connection

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inventory')
def inventory():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch inventory items
    cursor.execute("SELECT * FROM Inventory")
    inventory = cursor.fetchall()

    # Fetch suppliers for dropdown
    cursor.execute("SELECT supplier_id, supplier_name FROM Supplier")
    suppliers = cursor.fetchall()

    conn.close()
    return render_template('inventory.html', inventory=inventory, suppliers=suppliers)

@app.route('/add_inventory', methods=['POST'])
def add_inventory():
    item_name = request.form['item_name']
    batch_number = request.form['batch_number']
    expiry_date = request.form['expiry_date']
    quantity = request.form['quantity']
    price = request.form['price']
    supplier_id = request.form['supplier_id']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Inventory 
        (item_name, batch_number, expiry_date, quantity, price, supplier_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (item_name, batch_number, expiry_date, quantity, price, supplier_id))
    
    conn.commit()
    conn.close()
    return redirect('/inventory')

@app.route('/inventory/<int:item_id>', methods=['DELETE'])
def delete_inventory(item_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # First check if the item exists
        cursor.execute("SELECT 1 FROM Inventory WHERE item_id = %s", (item_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Item not found'}), 404
        
        # Delete the item
        cursor.execute("DELETE FROM Inventory WHERE item_id = %s", (item_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/billing')
def billing():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Inventory for dropdown selection
    cursor.execute("SELECT * FROM Inventory")
    inventory = cursor.fetchall()

    # Sales history
    cursor.execute("""
        SELECT S.sale_id, I.item_name, S.quantity_sold, S.total_price, S.sale_date
        FROM Sales S
        JOIN Inventory I ON S.item_id = I.item_id
        ORDER BY S.sale_date DESC
    """)
    sales = cursor.fetchall()

    conn.close()
    return render_template('billing.html', inventory=inventory, sales=sales)

@app.route('/sell_item', methods=['POST'])
def sell_item():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    item_id = request.form['item_id']
    qty = int(request.form['quantity_sold'])

    # Get item price
    cursor.execute("SELECT price FROM Inventory WHERE item_id = %s", (item_id,))
    price = cursor.fetchone()['price']
    total = price * qty

    # Record sale
    cursor.execute(
        "INSERT INTO Sales (item_id, quantity_sold, total_price) VALUES (%s, %s, %s)",
        (item_id, qty, total)
    )

    conn.commit()
    conn.close()
    return redirect('/billing')

if __name__ == '__main__':
    app.run(debug=True)