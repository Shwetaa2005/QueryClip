import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

class VectorStoreManager:
    def __init__(self, collection_name: str = "queryclip_videos"):
        """
        Initializes persistent local ChromaDB storage and the embedding model.
        """
        # 1. Initialize persistent local database client (saves to ./chroma_db folder)
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 2. Load open-source sentence transformer model for generating embeddings
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # 3. Create or get an existing ChromaDB collection
        self.collection = self.client.get_or_create_collection(name=collection_name)
        print("VectorStoreManager initialized successfully!")

    def add_chunks(self, chunks: list[dict]):
        """
        Embeds transcript text chunks and stores them with metadata in ChromaDB.
        """
        # 1. Extract documents (texts) from chunks
        documents = [c["text"] for c in chunks]
        
        # 2. Extract metadata dictionaries from chunks
        metadatas = [c["metadata"] for c in chunks]
        
        # 3. Create unique string IDs for each chunk (e.g., "videoID_startTime")
        ids = [f"{c['metadata']['video_id']}_{c['metadata']['start_time']}" for c in chunks]
        
        # 4. Generate vector embeddings using self.embedding_model.encode()
        # Note: Convert numpy output to python list using .tolist()
        embeddings = self.embedding_model.encode(documents).tolist()
        
        # 5. Add documents, embeddings, metadatas, and ids to self.collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully added {len(chunks)} chunks to ChromaDB!")
    
    def query(self, user_query: str, video_id: str, top_k: int = 3) -> list[dict]:
        """
        Converts user query to a vector, searches ChromaDB with a video_id filter,
        and returns top_k matching chunks with metadata.
        """
        # 1. Convert user_query into a vector embedding
        query_embedding = self.embedding_model.encode([user_query]).tolist()

        # 2. Query ChromaDB collection with metadata filtering
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where={"video_id": video_id}  # Metadata filter!
        )

        # 3. Format returned results into a clean list of dictionaries
        retrieved_chunks = []
        if results and results["documents"] and results["documents"][0]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                retrieved_chunks.append({
                    "text": doc,
                    "start_time": meta["start_time"],
                    "video_id": meta["video_id"]
                })

        return retrieved_chunks
    
if __name__ == "__main__":
    from backend.src.ingestion import fetch_and_process_video, extract_video_id

    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    v_id = extract_video_id(test_url)

    # 1. Process video and save chunks
    chunks = fetch_and_process_video(test_url)
    db_manager = VectorStoreManager()
    db_manager.add_chunks(chunks)

    # 2. Test querying the vector store
    user_question = "What is this song about?"
    matching_chunks = db_manager.query(user_question, video_id=v_id, top_k=2)

    print("\n--- SEARCH RESULTS ---")
    print(f"Query: '{user_question}'")
    for idx, match in enumerate(matching_chunks):
        print(f"\nResult {idx+1} [Start Time: {match['start_time']}s]:")
        print(match["text"][:150], "...")