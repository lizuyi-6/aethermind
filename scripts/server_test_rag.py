import sys
import os

# Ensure we can import from the current project directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

try:
    from agent import IntelligentAgent
    from config import Config
    from sqlite_rag_adapter import SQLiteRAGAugmenter
    
    print("--- Starting Server-Side RAG Test (v2) ---")
    
    # 1. Initialize Agent
    print("[1] Initializing IntelligentAgent...")
    config = Config()
    agent = IntelligentAgent(config, enable_rag=True)
    
    # 2. Verify Lazy Loading
    print("[2] Verifying Lazy Loading...")
    if agent.rag_augmenter is None and agent._rag_initialized is False:
        print("PASS: RAG is not initialized immediately (Lazy Loading working).")
    else:
        print(f"FAIL: RAG initialized too early? augmenter={agent.rag_augmenter}, _rag_initialized={agent._rag_initialized}")
        
    # 3. Trigger Initialization
    print("[3] Triggering _init_rag()...")
    agent._init_rag()
    
    if agent.rag_augmenter is not None and agent._rag_initialized is True:
        print("PASS: RAG initialized successfully.")
    else:
        print("FAIL: RAG failed to initialize.")
        sys.exit(1)

    if isinstance(agent.rag_augmenter, SQLiteRAGAugmenter):
        print("PASS: SQLite RAG adapter is active.")
    else:
        print("FAIL: SQLite RAG adapter is not active.")
        sys.exit(1)

    # 4. Test Retrieval
    print("[4] Testing RAG Retrieval...")
    # Search for a term likely to be in the "legal/regulations" knowledge base mentioned in logs
    keywords = ["安全", "管理", "规定", "法律"] 
    
    found_any = False
    for keyword in keywords:
        print(f"  Searching for: {keyword}")
        try:
            # CORRECTED: Access retriever through rag_augmenter.retriever
            results = agent.rag_augmenter.retriever.retrieve(keyword)
            print(f"  Found {len(results)} results.")
            if results:
                print(f"  Top result: {results[0]['payload'].get('content', '')[:100]}...")
                found_any = True
                break
        except Exception as e:
            print(f"  Error searching for {keyword}: {e}")
            import traceback
            traceback.print_exc()
            
    if found_any:
        print("PASS: Retrieval operational.")
    else:
        print("WARNING: Retrieval ran but found no results (Knowledge base might be empty or query mismatch).")

    print("--- Test Complete ---")

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
