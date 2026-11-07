import duckdb

duckdb.sql("""
COPY (
    SELECT o.id, o.name, o.address, o.city, o.category, o.lat, o.lon, g.google_id,
           c.ownership, c.tags
    FROM 'data/raw/overture.csv' o
    LEFT JOIN 'data/google_ids.csv' g ON o.id = g.id
    LEFT JOIN 'data/store_categories.csv' c ON o.id = c.id
    WHERE o.operating_status IS DISTINCT FROM 'permanently_closed'
) TO 'web/data/stores.json' (FORMAT json, ARRAY true)
""")
print("Wrote web/data/stores.json")