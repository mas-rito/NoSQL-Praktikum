"""
Aplikasi Catatan Populer
Studi Kasus: Integrasi MongoDB (penyimpanan permanen) + Redis (cache)
"""

from pymongo import MongoClient
import redis
import json
import time
import os
from datetime import datetime

# ============================================================
# KONEKSI DATABASE
# ============================================================

def connect_mongodb():
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=3000)
        client.server_info()  # trigger exception jika gagal
        db = client['catatan_app']
        print("✅ MongoDB terhubung")
        return db['catatan']
    except Exception as e:
        print(f"❌ MongoDB gagal terhubung: {e}")
        return None

def connect_redis():
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis terhubung")
        return r
    except Exception as e:
        print(f"❌ Redis gagal terhubung: {e}")
        return None

# ============================================================
# OPERASI MONGODB — penyimpanan permanen
# ============================================================

def buat_catatan(collection, judul, isi, penulis):
    """Simpan catatan baru ke MongoDB"""
    catatan = {
        "judul": judul,
        "isi": isi,
        "penulis": penulis,
        "dibuat_pada": datetime.now().isoformat(),
        "view_count": 0
    }
    result = collection.insert_one(catatan)
    catatan['_id'] = str(result.inserted_id)
    print(f"\n📝 Catatan '{judul}' berhasil disimpan ke MongoDB (id: {catatan['_id']})")
    return catatan

def lihat_catatan(collection, redis_client, catatan_id):
    """
    Lihat catatan berdasarkan ID.
    Setiap kali dilihat, view_count bertambah di MongoDB
    dan Redis mencatat frekuensi akses untuk ranking populer.
    """
    from bson import ObjectId

    catatan = collection.find_one({"_id": ObjectId(catatan_id)})
    if not catatan:
        print(f"❌ Catatan dengan id '{catatan_id}' tidak ditemukan")
        return None

    # Tambah view_count di MongoDB
    collection.update_one(
        {"_id": ObjectId(catatan_id)},
        {"$inc": {"view_count": 1}}
    )

    # Catat akses di Redis (sorted set untuk ranking)
    if redis_client:
        redis_client.zincrby("catatan:populer", 1, catatan_id)
        redis_client.expire("catatan:populer", 3600)  # cache 1 jam

    print(f"\n👁  Membuka catatan: '{catatan['judul']}' oleh {catatan['penulis']}")
    return catatan

def semua_catatan(collection):
    """Ambil semua catatan dari MongoDB"""
    return list(collection.find().sort("dibuat_pada", -1))

# ============================================================
# OPERASI REDIS — cache catatan populer
# ============================================================

def get_catatan_populer(redis_client, collection, top_n=3):
    """
    Ambil top-N catatan paling sering dibuka.
    Data ranking dari Redis (cepat), detail dari MongoDB.
    """
    cache_key = "cache:catatan_populer"

    # Cek apakah sudah ada di cache Redis
    cached = redis_client.get(cache_key)
    if cached:
        print("\n⚡ [CACHE HIT] Data populer diambil dari Redis")
        return json.loads(cached)

    # Cache miss — ambil dari Redis sorted set + MongoDB
    print("\n🔄 [CACHE MISS] Menghitung ulang dari database...")
    from bson import ObjectId

    # Ambil top-N id dari sorted set Redis (skor tertinggi)
    top_ids = redis_client.zrevrange("catatan:populer", 0, top_n - 1, withscores=True)

    if not top_ids:
        print("   (Belum ada data akses tercatat di Redis)")
        return []

    hasil = []
    for catatan_id, score in top_ids:
        try:
            doc = collection.find_one({"_id": ObjectId(catatan_id)})
            if doc:
                hasil.append({
                    "id": catatan_id,
                    "judul": doc["judul"],
                    "penulis": doc["penulis"],
                    "view_count": int(score),
                    "isi_singkat": doc["isi"][:60] + "..." if len(doc["isi"]) > 60 else doc["isi"]
                })
        except Exception:
            continue

    # Simpan hasil ke cache Redis selama 60 detik
    redis_client.setex(cache_key, 60, json.dumps(hasil))
    print("   ✅ Hasil di-cache ke Redis (berlaku 60 detik)")

    return hasil

def invalidate_cache(redis_client):
    """Hapus cache saat data berubah"""
    redis_client.delete("cache:catatan_populer")
    print("🗑  Cache Redis dihapus (akan diperbarui saat diakses berikutnya)")

# ============================================================
# SIMPAN DATA KE JSON (simulasi backup)
# ============================================================

def backup_ke_json(collection):
    """Ekspor semua catatan MongoDB ke file JSON"""
    os.makedirs("database", exist_ok=True)
    catatan_list = semua_catatan(collection)
    for c in catatan_list:
        c['_id'] = str(c['_id'])  # konversi ObjectId ke string
    with open("database/mongodb_data.json", "w", encoding="utf-8") as f:
        json.dump(catatan_list, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Backup {len(catatan_list)} catatan → database/mongodb_data.json")

def backup_redis_ke_json(redis_client):
    """Ekspor data Redis ke file JSON"""
    os.makedirs("database", exist_ok=True)
    populer = redis_client.zrevrange("catatan:populer", 0, -1, withscores=True)
    data = {
        "catatan_populer_ranking": [
            {"id": cid, "score": score} for cid, score in populer
        ],
        "cache_aktif": redis_client.exists("cache:catatan_populer") == 1,
        "diekspor_pada": datetime.now().isoformat()
    }
    with open("database/redis_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Backup data Redis → database/redis_data.json")

# ============================================================
# DEMO UTAMA
# ============================================================

def tampilkan_separator(judul):
    print(f"\n{'='*55}")
    print(f"  {judul}")
    print('='*55)

def main():
    tampilkan_separator("APLIKASI CATATAN POPULER")
    print("Integrasi MongoDB (permanen) + Redis (cache)\n")

    # Koneksi
    collection = connect_mongodb()
    r = connect_redis()

    if collection is None:
        print("\n❌ MongoDB tidak bisa dihubungi. Pastikan mongod berjalan.")
        print("   Jalankan: sudo mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /var/lib/mongodb")
        return

    if r is None:
        print("\n⚠️  Redis tidak bisa dihubungi. Fitur cache tidak aktif.")
        print("   Jalankan: sudo redis-server --daemonize yes")

    # Bersihkan data lama untuk demo bersih
    collection.drop()
    if r:
        r.delete("catatan:populer", "cache:catatan_populer")

    # ----------------------------------------------------------
    # TAHAP 1: Buat beberapa catatan
    # ----------------------------------------------------------
    tampilkan_separator("TAHAP 1: Membuat Catatan (MongoDB)")

    c1 = buat_catatan(collection,
        "Tips Belajar Python",
        "Belajar Python lebih mudah dengan latihan soal setiap hari. "
        "Gunakan project kecil untuk mempraktikkan konsep baru seperti "
        "list comprehension, decorator, dan generator.",
        "Andi")

    c2 = buat_catatan(collection,
        "Perbedaan MongoDB vs Redis",
        "MongoDB adalah document store yang cocok untuk data terstruktur permanen. "
        "Redis adalah in-memory store yang sangat cepat untuk cache dan session.",
        "Budi")

    c3 = buat_catatan(collection,
        "Cara Setup GitHub Codespace",
        "Buat file .devcontainer/devcontainer.json di root project. "
        "Tambahkan postCreateCommand untuk instalasi dependensi otomatis.",
        "Citra")

    c4 = buat_catatan(collection,
        "Resep Nasi Goreng Spesial",
        "Bahan: nasi putih, telur, kecap manis, bawang merah, bawang putih, "
        "cabai, dan garam. Tumis bumbu hingga harum sebelum masukkan nasi.",
        "Dewi")

    # ----------------------------------------------------------
    # TAHAP 2: Simulasi user membuka catatan
    # ----------------------------------------------------------
    tampilkan_separator("TAHAP 2: User Membuka Catatan")
    print("Simulasi pola akses: beberapa catatan lebih sering dibuka\n")

    # c1 dibuka 5x (paling populer)
    for i in range(5):
        lihat_catatan(collection, r, str(c1['_id']))
        time.sleep(0.1)

    # c2 dibuka 3x
    for i in range(3):
        lihat_catatan(collection, r, str(c2['_id']))
        time.sleep(0.1)

    # c3 dibuka 2x
    for i in range(2):
        lihat_catatan(collection, r, str(c3['_id']))
        time.sleep(0.1)

    # c4 dibuka 1x
    lihat_catatan(collection, r, str(c4['_id']))

    # ----------------------------------------------------------
    # TAHAP 3: Ambil catatan populer (cache miss pertama)
    # ----------------------------------------------------------
    tampilkan_separator("TAHAP 3: Lihat Catatan Populer")

    if r:
        print("\n--- Request pertama (cache belum ada) ---")
        populer = get_catatan_populer(r, collection, top_n=3)

        print("\n🏆 Top 3 Catatan Terpopuler:")
        for i, c in enumerate(populer, 1):
            print(f"  {i}. [{c['view_count']}x dibuka] \"{c['judul']}\" — {c['penulis']}")
            print(f"     {c['isi_singkat']}")

        # Request kedua — seharusnya dari cache
        print("\n--- Request kedua (harusnya dari cache) ---")
        populer2 = get_catatan_populer(r, collection, top_n=3)
        print(f"   Data sama, tapi lebih cepat karena dari Redis cache ✅")

    # ----------------------------------------------------------
    # TAHAP 4: Tambah catatan baru → invalidate cache
    # ----------------------------------------------------------
    tampilkan_separator("TAHAP 4: Update Data → Invalidate Cache")

    if r:
        c5 = buat_catatan(collection,
            "Panduan NoSQL untuk Pemula",
            "NoSQL mencakup berbagai jenis database: document (MongoDB), "
            "key-value (Redis), column-family (Cassandra), dan graph (Neo4j).",
            "Eko")
        invalidate_cache(r)

    # ----------------------------------------------------------
    # TAHAP 5: Tampilkan semua catatan dari MongoDB
    # ----------------------------------------------------------
    tampilkan_separator("TAHAP 5: Semua Catatan di MongoDB")

    semua = semua_catatan(collection)
    print(f"\nTotal catatan tersimpan: {len(semua)}\n")
    for c in semua:
        print(f"  📄 \"{c['judul']}\" oleh {c['penulis']}")
        print(f"     👁  {c['view_count']} kali dilihat | 🕒 {c['dibuat_pada'][:19]}")

    # ----------------------------------------------------------
    # TAHAP 6: Backup ke JSON
    # ----------------------------------------------------------
    tampilkan_separator("TAHAP 6: Backup Data ke JSON")
    backup_ke_json(collection)
    if r:
        backup_redis_ke_json(r)

    # ----------------------------------------------------------
    # SELESAI
    # ----------------------------------------------------------
    tampilkan_separator("SELESAI")
    print("\nRingkasan cara kerja sistem:")
    print("  MongoDB → menyimpan semua catatan secara permanen")
    print("  Redis   → mencatat frekuensi akses & meng-cache hasil populer")
    print("  Cache   → mempercepat query populer tanpa beban ke MongoDB")
    print("\nCek file hasil backup:")
    print("  📁 database/mongodb_data.json")
    print("  📁 database/redis_data.json")

if __name__ == "__main__":
    main()