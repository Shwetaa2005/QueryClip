from src.vector_store import VectorStoreManager

db = VectorStoreManager()

# Check total number of indexed chunks
print("Total chunks:", db.collection.count())

# Retrieve indexed records
results = db.collection.get(
    include=["documents", "metadatas"]
)

for i, (doc, metadata) in enumerate(
    zip(results["documents"], results["metadatas"])
):
    print(f"\n--- CHUNK {i + 1} ---")
    print("Metadata:", metadata)
    print("Text:", doc)