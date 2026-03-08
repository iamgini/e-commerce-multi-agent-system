import sqlite3

conn = sqlite3.connect("./data/mockdata")
cursor = conn.cursor()

cursor.execute("""
               CREATE TABLE IF NOT EXISTS products (
                   product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   product_name TEXT,
                   product_description TEXT,
                   product_category TEXT,
                   product_subcategory TEXT,
                   brand_name TEXT,
                   price REAL NOTE NULL,
                   stock INTEGER NOT NULL DEFAULT 0,
                   rating REAL DEFAULT 0.0 
                   )
                   """)
conn.commit()

products = [
    ("Logitech MX Master 3", "Ergonomic wireless mouse with precision tracking and customizable controls for productivity pros.", "Electronics", "Mouse", "Logitech", 99.99, 150, 4.8),
    ("Razer DeathAdder V2", "High‑precision gaming mouse with optical switches and ergonomic grip for competitive play.", "Electronics", "Mouse", "Razer", 69.99, 120, 4.7),
    ("Apple Magic Mouse 2", "Multi‑touch wireless mouse with rechargeable battery and sleek design for Mac ecosystems.", "Electronics", "Mouse", "Apple", 79.99, 90, 4.6),
    ("Corsair K95 RGB Platinum", "Premium mechanical keyboard with customizable RGB and dedicated macro keys for gamers.", "Electronics", "Keyboard", "Corsair", 199.99, 60, 4.7),
    ("Logitech G915 TKL", "Wireless mechanical keyboard with low‑profile GL switches and LIGHTSYNC RGB lighting.", "Electronics", "Keyboard", "Logitech", 229.99, 70, 4.6),
    ("Razer BlackWidow V3", "Durable gaming keyboard with tactile switches and dynamic RGB lighting effects.", "Electronics", "Keyboard", "Razer", 139.99, 80, 4.5),
    ("Samsung Odyssey G7 27\"", "Curved QHD monitor with 240Hz refresh and deep contrast for immersive gaming.", "Electronics", "Monitor", "Samsung", 699.99, 35, 4.8),
    ("LG UltraGear 27GL850", "QHD IPS gaming monitor with 144Hz refresh rate and rapid response time.", "Electronics", "Monitor", "LG", 449.99, 50, 4.7),
    ("Sony WH‑1000XM4", "Industry‑leading noise‑cancelling headphones with premium audio clarity and comfort.", "Electronics", "Headphones", "Sony", 349.99, 40, 4.9),
    ("Bose QuietComfort 45", "Comfortable wireless noise‑cancelling headphones with up to 24‑hour battery life.", "Electronics", "Headphones", "Bose", 329.99, 45, 4.8),
    ("Apple AirPods Pro (2nd Gen)", "Wireless earbuds with active noise cancellation and adaptive transparency.", "Electronics", "Headphones", "Apple", 249.99, 65, 4.7),
    ("Beats Studio3 Wireless", "High‑performance wireless headphones with pure adaptive noise‑cancelling.", "Electronics", "Headphones", "Beats", 279.99, 55, 4.6),
    ("Google Pixel Buds Pro", "Wireless earbuds with premium sound and seamless Google Assistant integration.", "Electronics", "Headphones", "Google", 199.99, 70, 4.5),
    ("Sony A7 III Mirrorless Camera", "Full‑frame mirrorless camera with excellent low‑light performance and advanced autofocus.", "Electronics", "Camera", "Sony", 1999.99, 20, 4.8),
    ("Canon EOS R6", "Versatile mirrorless camera with fast continuous shooting and 4K video capture.", "Electronics", "Camera", "Canon", 2499.99, 15, 4.7),
    ("Nikon Z6 II", "Mirrorless camera offering excellent image quality and dual‑processor performance.", "Electronics", "Camera", "Nikon", 1996.95, 18, 4.7),
    ("DJI Mavic Air 2", "Compact drone with 4K HDR video and intelligent shooting modes.", "Electronics", "Drone", "DJI", 799.99, 30, 4.8),
    ("Fitbit Charge 5", "Advanced fitness tracker with built‑in GPS, stress management, and heart rate monitoring.", "Electronics", "Wearable", "Fitbit", 149.95, 120, 4.4),
    ("Apple Watch Series 9", "Smartwatch with powerful performance, health tracking, and seamless iPhone integration.", "Electronics", "Wearable", "Apple", 399.99, 80, 4.8),
    ("Samsung Galaxy Watch 6", "Smartwatch with robust fitness features and long battery life.", "Electronics", "Wearable", "Samsung", 349.99, 75, 4.6),
    ("Nike Air Zoom Pegasus 39", "Everyday running shoes with responsive cushioning and breathable mesh.", "Footwear", "Sports Shoes", "Nike", 119.99, 200, 4.6),
    ("Adidas Ultraboost 22", "Boost technology for superior energy return and comfortable long runs.", "Footwear", "Sports Shoes", "Adidas", 179.99, 180, 4.7),
    ("New Balance Fresh Foam 1080v12", "Cushioned running shoes with plush Fresh Foam midsole for daily mileage.", "Footwear", "Sports Shoes", "New Balance", 149.99, 160, 4.5),
    ("Saucony Kinvara 13", "Lightweight road running shoes with springy responsiveness.", "Footwear", "Sports Shoes", "Saucony", 129.99, 140, 4.5),
    ("Timberland 6‑Inch Premium Boot", "Rugged waterproof boots with padded collar for outdoor durability.", "Footwear", "Boots", "Timberland", 198.00, 120, 4.5),
    ("Dr. Martens 1460", "Classic leather boots with air‑cushioned sole and iconic style.", "Footwear", "Boots", "Dr. Martens", 150.00, 90, 4.6),
    ("Columbia Newton Ridge Plus II", "Durable waterproof hiking boots with traction‑ready outsole.", "Footwear", "Boots", "Columbia", 129.99, 130, 4.6),
    ("UGG Classic Short II", "Comfortable sheepskin boots with cozy warmth for cold weather.", "Footwear", "Boots", "UGG", 159.95, 100, 4.7),
    ("Levi's 501 Original Jeans", "Timeless straight‑fit denim with button fly and authentic style.", "Clothing", "Jeans", "Levi's", 59.99, 250, 4.4),
    ("Wrangler Authentics Slim Fit", "Comfortable slim‑fit jeans with everyday style and durable build.", "Clothing", "Jeans", "Wrangler", 49.99, 200, 4.3),
    ("Levi's 511 Slim Fit Jeans", "Modern slim cut denim with stretch for comfort and mobility.", "Clothing", "Jeans", "Levi's", 69.99, 210, 4.5),
    ("Gap Classic Khaki Pants", "Versatile khaki pants with relaxed fit for everyday wear.", "Clothing", "Pants", "Gap", 49.95, 180, 4.2),
    ("Uniqlo Men Supima Cotton T‑Shirt", "Soft Supima cotton tee with breathable comfort and classic design.", "Clothing", "T‑Shirts", "Uniqlo", 14.99, 500, 4.5),
    ("Hanes Men’s Tagless Tee", "Tagless cotton t‑shirt with comfort‑first design for daily wear.", "Clothing", "T‑Shirts", "Hanes", 9.99, 400, 4.2),
    ("Champion Reverse Weave Hoodie", "Warm fleece hoodie with classic logo and durable construction.", "Clothing", "Hoodies", "Champion", 59.99, 150, 4.6),
    ("The North Face Denali Fleece Jacket", "Cozy fleece jacket with reinforced shoulders for outdoor warmth.", "Clothing", "Jackets", "The North Face", 179.00, 80, 4.7),
    ("Patagonia Better Sweater", "Eco‑friendly fleece sweater with full‑zip comfort and rugged durability.", "Clothing", "Sweaters", "Patagonia", 139.00, 100, 4.8),
    ("Dyson V15 Detect", "Cordless vacuum with laser dust detection and powerful suction for deep cleaning.", "Home Appliances", "Vacuum Cleaner", "Dyson", 699.99, 30, 4.8),
    ("iRobot Roomba i7+", "Smart robot vacuum with automatic dirt disposal and smart mapping.", "Home Appliances", "Vacuum Cleaner", "iRobot", 799.99, 25, 4.7),
    ("Ninja Foodi Blender", "High‑speed blender with precision blades for smooth blending and crushing ice.", "Home Appliances", "Blender", "Ninja", 129.99, 60, 4.6),
    ("KitchenAid Artisan Mixer", "Iconic stand mixer with 10 speeds and versatile attachments for baking.", "Home Appliances", "Mixer", "KitchenAid", 379.99, 40, 4.9),
    ("Instant Pot Duo 7‑in‑1", "Multi‑use pressure cooker with customizable programs and reliable performance.", "Home Appliances", "Pressure Cooker", "Instant Pot", 99.95, 70, 4.7),
    ("Samsung Family Hub Refrigerator", "Smart refrigerator with touchscreen display and flexible storage options.", "Home Appliances", "Refrigerator", "Samsung", 2499.99, 10, 4.6),
    ("LG ThinQ Washer", "Smart washer with AI fabric care and energy‑efficient performance.", "Home Appliances", "Washer", "LG", 899.99, 15, 4.5),
    ("Sony X900H 65\" TV", "4K HDR Smart LED TV with immersive picture quality and gaming mode.", "Electronics", "Television", "Sony", 1299.99, 20, 4.7),
    ("Samsung Q80T 55\" QLED", "Vibrant QLED display with impressive contrast and motion handling.", "Electronics", "Television", "Samsung", 1099.99, 18, 4.6),
    ("LG CX 65\" OLED", "Stunning OLED picture with deep blacks and rich colors.", "Electronics", "Television", "LG", 2499.99, 12, 4.8),
    ("Bissell CrossWave Floor Cleaner", "All‑in‑one wet and dry floor cleaner with multi‑surface cleaning.", "Home Appliances", "Floor Cleaner", "Bissell", 299.99, 30, 4.5),
    ("Miele Classic C1 Vacuum", "Reliable canister vacuum with powerful suction and quiet operation.", "Home Appliances", "Vacuum Cleaner", "Miele", 399.99, 25, 4.7),
    ("Sony PlayStation 5", "Next‑gen gaming console with lightning‑fast load times and immersive gaming.", "Electronics", "Gaming Console", "Sony", 499.99, 50, 4.9),
    ("Microsoft Xbox Series X", "Powerful gaming console with 4K gaming and high performance.", "Electronics", "Gaming Console", "Microsoft", 499.99, 45, 4.8),
    ("Nintendo Switch OLED", "Versatile gaming system with vibrant OLED screen and portable play.", "Electronics", "Gaming Console", "Nintendo", 349.99, 60, 4.9), 
]

cursor.executemany("""
                   INSERT INTO products
                   (product_name, product_description, product_category, product_subcategory, brand_name, price, stock, rating)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   """, products)

conn.commit()

cursor.execute("SELECT Count(*) FROM products")
print(cursor.fetchall())

conn.close()
