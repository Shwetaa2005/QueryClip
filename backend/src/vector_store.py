import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding

class VectorStoreManager:
    def __init__(self, collection_name: str = "queryclip_videos"):
        """
        Initializes persistent local ChromaDB storage and the lightweight FastEmbed model.
        """
        # 1. Initialize persistent local database client (saves to ./chroma_db folder)
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 2. Load lightweight FastEmbed model (ONNX runtime, ~100MB footprint)
        self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        
        # 3. Create or get an existing ChromaDB collection
        self.collection = self.client.get_or_create_collection(name=collection_name)
        print("VectorStoreManager initialized successfully!")

    def add_chunks(self, chunks: list[dict]):
        """
        Deletes existing chunks for the given video_id to avoid stale duplicates,
        then adds fresh chunks with unique index-based IDs.
        """
        if not chunks:
            return

        video_id = chunks[0]["metadata"]["video_id"]
        
        # 1. Clean up old records for this video before indexing new ones
        try:
            self.collection.delete(where={"video_id": video_id})
        except Exception as e:
            print(f"Notice: No prior records deleted for video {video_id}: {e}")

        # 2. Extract documents, metadata, and format unique index-based IDs
        documents = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [f"{video_id}_{i}" for i in range(len(chunks))]
        
        # 3. Generate embeddings using FastEmbed
        embeddings = [e.tolist() for e in list(self.embedding_model.embed(documents))]

        # 4. Add documents, embeddings, metadatas, and ids to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully indexed {len(chunks)} chunks for video '{video_id}' in ChromaDB!")

    def query(self, user_query: str, video_id: str, top_k: int = 3) -> list[dict]:
        """
        Converts user query to a vector using FastEmbed, searches ChromaDB with a video_id filter,
        and returns top_k matching chunks with metadata.
        """
        # 1. Convert user_query into a vector embedding using FastEmbed
        query_embedding = [e.tolist() for e in list(self.embedding_model.embed([user_query]))]

        # 2. Query ChromaDB collection with metadata filtering
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where={"video_id": video_id}
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