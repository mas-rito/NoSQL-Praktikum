import redis
import time

# Koneksi ke Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

print("=== SIMULASI SHOPPING CART & SESSION ===\n")

# 1. SESSION USER
user_id = "user:1001"
r.hset(user_id, mapping={
    "name": "Budi",
    "last_active": time.time(),
    "cart_total": 0
})
print("✅ Session user Budi dibuat!")

# 2. SHOPPING CART
cart_key = f"cart:{user_id}"
r.hset(cart_key, "laptop", "1")
r.hset(cart_key, "mouse", "2")

print("\n🛒 Shopping Cart Budi:")
items = r.hgetall(cart_key)
for product, qty in items.items():
    print(f"  - {product}: {qty} pcs")

# 3. UPDATE CART
r.hincrby(cart_key, "mouse", 1)
print("\n✏️ Mouse ditambah 1, cart sekarang:")
print(r.hgetall(cart_key))

# 4. SIMPAN HARGA PRODUK
r.set("product:laptop:price", 15000000)
r.set("product:mouse:price", 250000)
print(f"\n💰 Harga Laptop: Rp{r.get('product:laptop:price')}")
print(f"💰 Harga Mouse: Rp{r.get('product:mouse:price')}")

# 5. COUNTER - hitung pengunjung
r.set("visitor:count", 0)
r.incr("visitor:count")
r.incr("visitor:count")
r.incr("visitor:count")
print(f"\n👥 Total pengunjung: {r.get('visitor:count')}")

# 6. LEADERBOARD
r.zadd("produk:terlaris", {"Laptop": 100, "Mouse": 250, "Keyboard": 75})
print("\n🏆 Top 3 Produk Terlaris:")
top3 = r.zrevrange("produk:terlaris", 0, 2, withscores=True)
for i, (product, score) in enumerate(top3, 1):
    print(f"  {i}. {product} - terjual {int(score)} pcs")

# 7. TTL - Session expire
r.expire(cart_key, 3600)
ttl = r.ttl(cart_key)
print(f"\n⏰ Cart akan expired dalam: {ttl} detik (1 jam)")

print("\n=== SELESAI ===")