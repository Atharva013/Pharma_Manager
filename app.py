from flask import Flask, render_template, request, redirect, jsonify, flash
from db_connection import get_connection 
from datetime import datetime
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for flash messages

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inventory')
def inventory():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch inventory items
        cursor.execute("SELECT * FROM Inventory")
        inventory = cursor.fetchall()

        # Fetch suppliers for dropdown
        cursor.execute("SELECT supplier_id, supplier_name FROM Supplier")
        suppliers = cursor.fetchall()

        return render_template('inventory.html', inventory=inventory, suppliers=suppliers)
    except Exception as e:
        flash(f"Error loading inventory: {str(e)}", 'danger')
        return render_template('inventory.html', inventory=[], suppliers=[])
    finally:
        conn.close()

@app.route('/add_inventory', methods=['POST'])
def add_inventory():
    try:
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
        flash('Medicine added successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error adding medicine: {str(e)}', 'danger')
    finally:
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
        
        # Check if there are any sales records
        cursor.execute("SELECT 1 FROM Sales WHERE item_id = %s LIMIT 1", (item_id,))
        if cursor.fetchone():
            return jsonify({
                'error': 'Cannot delete - this medicine has sales records. Mark as discontinued instead.',
                'has_sales': True
            }), 400
        
        # Delete the item
        cursor.execute("DELETE FROM Inventory WHERE item_id = %s", (item_id,))
        conn.commit()
        return jsonify({'success': True}), 200
        
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'error': str(err)}), 500
    finally:
        conn.close()

@app.route('/update_inventory', methods=['POST'])
def update_inventory():
    try:
        item_id = request.form['item_id']
        item_name = request.form['item_name']
        batch_number = request.form['batch_number']
        expiry_date = request.form['expiry_date']
        quantity = request.form['quantity']
        price = request.form['price']
        supplier_id = request.form['supplier_id']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Inventory SET
            item_name = %s,
            batch_number = %s,
            expiry_date = %s,
            quantity = %s,
            price = %s,
            supplier_id = %s
            WHERE item_id = %s
        """, (item_name, batch_number, expiry_date, quantity, price, supplier_id, item_id))
        
        conn.commit()
        flash('Medicine updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error updating medicine: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect('/inventory')

@app.route('/mark_discontinued/<int:item_id>', methods=['POST'])
def mark_discontinued(item_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Inventory SET is_active = 0 WHERE item_id = %s
        """, (item_id,))
        conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


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