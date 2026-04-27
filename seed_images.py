import os
import random
import requests
import mysql.connector

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "project_shop",
    "port": 8889,
}

conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()

# Clear old image database links
cur.execute("DELETE FROM listing_images")

# Get all listing ids
cur.execute("SELECT id FROM listings ORDER BY id")
listing_ids = [row[0] for row in cur.fetchall()]

for listing_id in listing_ids:
    image_count = random.choice([2, 3, 3, 4])

    for img_num in range(1, image_count + 1):
        filename = f"listing_{listing_id}_{img_num}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Random demo image
        url = f"https://picsum.photos/seed/listing{listing_id}_{img_num}/900/900"

        response = requests.get(url, timeout=20)
        response.raise_for_status()

        with open(filepath, "wb") as file:
            file.write(response.content)

        cur.execute(
            "INSERT INTO listing_images (listing_id, image_path) VALUES (%s, %s)",
            (listing_id, filename),
        )

conn.commit()
cur.close()
conn.close()

print("Done. Random images added to all listings.")