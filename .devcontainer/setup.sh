#!/bin/bash
set -e

echo "=== Installing MongoDB ==="
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg

echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt-get update -q
sudo apt-get install -y mongodb-org

echo "=== Installing Redis ==="
sudo apt-get install -y redis-server

echo "=== Installing Python libraries ==="
pip install pymongo redis

echo "=== Starting services ==="
sudo mkdir -p /var/lib/mongodb /var/log/mongodb
sudo mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /var/lib/mongodb
sudo redis-server --daemonize yes

echo "✅ Setup complete!"