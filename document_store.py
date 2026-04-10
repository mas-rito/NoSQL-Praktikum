from pymongo import MongoClient

# Koneksi ke MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['ecommerce']
products = db['products']

# Hapus data lama (biar bersih tiap run)
products.drop()

# Insert produk
product1 = {
    "name": "Laptop Gaming",
    "price": 15000000,
    "specs": {"ram": "16GB", "storage": "512GB SSD"},
    "tags": ["electronics", "gaming"]
}
product2 = {
    "name": "Mouse Wireless",
    "price": 250000,
    "specs": {"dpi": 3200, "wireless": True},
    "tags": ["electronics", "accessories"]
}
products.insert_many([product1, product2])
print("✅ 2 produk berhasil diinsert!")

# READ - cari produk murah
print("\n🔍 Produk dengan harga < 1 juta:")
cheap = products.find({"price": {"$lt": 1000000}})
for p in cheap:
    print(f"  - {p['name']} : Rp{p['price']}")

# UPDATE
products.update_one({"name": "Laptop Gaming"}, {"$set": {"discount": 10}})
print("\n✏️ Laptop Gaming diupdate, ditambah diskon 10%")

# READ semua
print("\n📋 Semua produk:")
for p in products.find():
    print(f"  - {p['name']} | Rp{p['price']} | Tags: {p['tags']}")

# DELETE
products.delete_one({"name": "Mouse Wireless"})
print("\n🗑️ Mouse Wireless dihapus!")

print("\n📋 Produk tersisa:")
for p in products.find():
   print(f"  - {p['name']}")