CREATE DATABASE IF NOT EXISTS pharma_well;
USE pharma_well;

-- Inventory Table
update TABLE Inventory (
  item_id INT AUTO_INCREMENT PRIMARY KEY,
  item_name VARCHAR(100) NOT NULL,
  batch_number VARCHAR(50),
  expiry_date DATE,
  quantity INT NOT NULL,
  price DECIMAL(10, 2) NOT NULL,
  supplier_id INT,
  FOREIGN KEY (supplier_id) REFERENCES Supplier(supplier_id)
);

--customer table 
-- Customer Table
CREATE TABLE Customer (
  customer_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL
);

-- Sales Table
CREATE TABLE Sales (
  sale_id INT AUTO_INCREMENT PRIMARY KEY,
  item_id INT,
  quantity_sold INT NOT NULL,
  sale_date DATETIME DEFAULT CURRENT_TIMESTAMP,
  total_price DECIMAL(10, 2),
  FOREIGN KEY (item_id) REFERENCES Inventory(item_id)
);

-- create supplier table
CREATE TABLE Supplier (
  supplier_id INT AUTO_INCREMENT PRIMARY KEY,
  supplier_name VARCHAR(100) NOT NULL,
  contact_info VARCHAR(100)
);


-- Trigger to auto-update inventory
DELIMITER //
CREATE TRIGGER update_inventory_after_sale
AFTER INSERT ON Sales
FOR EACH ROW
BEGIN
  UPDATE Inventory
  SET quantity = quantity - NEW.quantity_sold
  WHERE item_id = NEW.item_id;
END;
//
DELIMITER ;

//Automatically compute total_price from quantity_sold * price
DELIMITER //
CREATE TRIGGER calc_total_price_before_sale
BEFORE INSERT ON Sales
FOR EACH ROW
BEGIN
  DECLARE unit_price DECIMAL(10,2);
  SELECT price INTO unit_price FROM Inventory WHERE item_id = NEW.item_id;
  
  SET NEW.total_price = NEW.quantity_sold * unit_price;
END;
//
DELIMITER ;


DELIMITER //
CREATE TRIGGER prevent_negative_stock
BEFORE INSERT ON Sales
FOR EACH ROW
BEGIN
  DECLARE available_qty INT;
  SELECT quantity INTO available_qty FROM Inventory WHERE item_id = NEW.item_id;

  IF NEW.quantity_sold > available_qty THEN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Not enough stock available for sale!';
  END IF;
END;
//
DELIMITER ;

