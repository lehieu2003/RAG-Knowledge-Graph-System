"""
Example usage script
Demonstrates the full workflow: upload → ingest → query
"""
import asyncio
import httpx
from pathlib import Path


API_BASE_URL = "http://localhost:8000"


async def example_workflow():
    """Complete workflow example"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # 1. Upload a PDF document
        print("📄 Uploading document...")
        with open("example.pdf", "rb") as f:
            response = await client.post(
                f"{API_BASE_URL}/documents/upload",
                files={"file": ("example.pdf", f, "application/pdf")}
            )
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.text}")
            return
        
        doc_data = response.json()
        doc_id = doc_data["doc_id"]
        print(f"✅ Document uploaded: {doc_id}")
        
        # 2. Start ingestion
        print("\n⚙️  Starting ingestion job...")
        response = await client.post(
            f"{API_BASE_URL}/ingestion/jobs",
            json={"doc_id": doc_id}
        )
        
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ Job submitted: {job_id}")
        
        # 3. Poll job status
        print("\n⏳ Waiting for ingestion to complete...")
        while True:
            response = await client.get(f"{API_BASE_URL}/ingestion/jobs/{job_id}")
            job_status = response.json()
            
            status = job_status["status"]
            print(f"   Status: {status} - Step: {job_status.get('current_step', 'N/A')}")
            
            if status == "done":
                print("✅ Ingestion complete!")
                print(f"   Progress: {job_status['progress']}")
                break
            elif status == "failed":
                print(f"❌ Ingestion failed: {job_status.get('error_message')}")
                return
            
            await asyncio.sleep(3)
        
        # 4. Check knowledge graph stats
        print("\n📊 Knowledge Graph Stats:")
        response = await client.get(f"{API_BASE_URL}/kg/stats")
        stats = response.json()
        print(f"   Entities: {stats['entity_count']}")
        print(f"   Relations: {stats['relation_count']}")
        
        # 5. Ask a question
        print("\n💬 Asking question...")
        response = await client.post(
            f"{API_BASE_URL}/chat",
            json={
                "question": "What are the main concepts discussed in the document?",
                "mode": "auto",
                "top_k": 5
            }
        )
        
        answer_data = response.json()
        print(f"\n📝 Answer (mode: {answer_data['mode_used']}):")
        print(f"   Confidence: {answer_data['confidence']:.2f}")
        print(f"\n{answer_data['answer']}")
        print(f"\n   Evidence sources: {len(answer_data['evidence'])}")
        
        # 6. Search entities
        print("\n🔍 Searching entities...")
        response = await client.post(
            f"{API_BASE_URL}/kg/entities/search",
            json={"query": "neural", "limit": 5}
        )
        
        search_results = response.json()
        print(f"   Found {search_results['count']} entities:")
        for entity in search_results["entities"][:3]:
            print(f"   - {entity['canonical_name']} ({entity['entity_type']})")


if __name__ == "__main__":
    print("🚀 RAG Knowledge Graph System - Example Workflow\n")
    print("Make sure the FastAPI server is running at http://localhost:8000")
    print("=" * 60)
    
    try:
        asyncio.run(example_workflow())
        print("\n✅ Workflow completed successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
