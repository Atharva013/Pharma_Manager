from flask import Flask, render_template, request, redirect, jsonify, flash
from db_connection import get_connection 
from datetime import datetime
import mysql.connector
from mysql.connector import Error



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

    try:
        item_id = request.form['item_id']
        qty = int(request.form['quantity_sold'])

        # Get item price
        cursor.execute("SELECT price FROM Inventory WHERE item_id = %s", (item_id,))
        price_data = cursor.fetchone()
        if not price_data:
            flash("Item not found.", "danger")
            return redirect('/billing')

        price = price_data['price']
        total = price * qty

        # Try inserting into Sales (will fail if stock insufficient due to trigger)
        cursor.execute(
            "INSERT INTO Sales (item_id, quantity_sold, total_price) VALUES (%s, %s, %s)",
            (item_id, qty, total)
        )

        conn.commit()
        flash("Sale recorded successfully!", "success")

    except mysql.connector.Error as err:
        if err.errno == 1644:  # Custom signal (SQLSTATE '45000')
            flash("Error: Not enough stock available for sale!", "danger")
        else:
            flash(f"Database error: {str(err)}", "danger")
        conn.rollback()
    except Exception as e:
        flash(f"Unexpected error: {str(e)}", "danger")
        conn.rollback()
    finally:
        conn.close()

    return redirect('/billing')

@app.route('/sales_report')
def sales_report():
    try:
        # Establish a new connection and cursor
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)  # Use dictionary=True for named columns

        # Execute the query
        cursor.execute("""
            SELECT 
                item_name, 
                SUM(quantity_sold) AS total_quantity, 
                DATE(sale_date) AS date, 
                SUM(total_price) AS total_sales 
            FROM sales 
            GROUP BY item_name, DATE(sale_date)
        """)
        
        sales_data = cursor.fetchall()
        
        return render_template('sales_report.html', sales_data=sales_data)

    except Error as e:
        print(f"Database error: {e}")
        return render_template('error.html', error_message="Failed to fetch sales data"), 500

    finally:
        # Ensure resources are freed even if an error occurs
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()



if __name__ == '__main__':
    app.run(debug=True)