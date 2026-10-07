"""
Local MCP Server for RAG Chat Agent (No Azure Required)
Mimics Azure AI Foundry Agent Service behavior locally:
- Local LLM via Ollama
- Local vector search via ChromaDB
- Same evaluation framework
- Local tracing/logging

Run: python local_mcp_server.py
"""

import os
import json
import asyncio
import logging
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Local dependencies
import chromadb
from chromadb.utils import embedding_functions
import ollama

# Evaluation (same as Azure version)
from evaluators import (
    evaluate_groundedness,
    evaluate_relevance,
    evaluate_safety,
    EvaluationResult,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


@dataclass
class AgentInteraction:
    """Represents a single agent interaction for evaluation and logging"""
    timestamp: str
    user_query: str
    agent_response: str
    citations: List[str]
    tools_used: List[str]
    latency_ms: float
    token_usage: Dict[str, int]
    evaluation: Optional[EvaluationResult] = None


class LocalTracer:
    """Local tracing to console and JSON file"""

    def __init__(self, service_name: str = "rag-chat-agent-local"):
        self.service_name = service_name
        self.trace_file = f"traces_{datetime.now().strftime('%Y%m%d')}.jsonl"
        logger.info(f"Local tracing to {self.trace_file}")

    @asynccontextmanager
    async def trace_agent_call(self, operation_name: str, attributes: Dict[str, Any] = None):
        """Context manager for tracing agent operations"""
        span_id = f"{operation_name}_{datetime.now().timestamp()}"
        start_time = datetime.now()
        logger.info(f"🔵 START {operation_name} | {attributes}")
        
        yield span_id
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"🟢 END {operation_name} | Duration: {duration:.0f}ms")
        
        # Write to trace file
        trace_record = {
            "span_id": span_id,
            "operation": operation_name,
            "attributes": attributes or {},
            "duration_ms": duration,
            "timestamp": start_time.isoformat(),
            "service": self.service_name
        }
        with open(self.trace_file, "a") as f:
            f.write(json.dumps(trace_record) + "\n")

    def record_interaction(self, interaction: AgentInteraction):
        """Record interaction for observability"""
        trace_record = {
            "type": "agent_interaction",
            "user_query": interaction.user_query[:500],
            "response_length": len(interaction.agent_response),
            "citations_count": len(interaction.citations),
            "tools_used": interaction.tools_used,
            "latency_ms": interaction.latency_ms,
            "token_usage": interaction.token_usage,
            "evaluation": asdict(interaction.evaluation) if interaction.evaluation else None,
            "timestamp": interaction.timestamp,
            "service": self.service_name
        }
        with open(self.trace_file, "a") as f:
            f.write(json.dumps(trace_record) + "\n")


class LocalEvaluationHooks:
    """Evaluation hooks for measuring agent quality"""

    def __init__(self, tracer: LocalTracer):
        self.tracer = tracer
        self.interactions: List[AgentInteraction] = []

    async def evaluate_interaction(self, interaction: AgentInteraction) -> EvaluationResult:
        """Run all evaluations on an interaction"""
        logger.info(f"Evaluating interaction: {interaction.user_query[:50]}...")

        groundedness_task = evaluate_groundedness(
            interaction.user_query,
            interaction.agent_response,
            interaction.citations
        )
        relevance_task = evaluate_relevance(
            interaction.user_query,
            interaction.agent_response
        )
        safety_task = evaluate_safety(interaction.agent_response)

        groundedness, relevance, safety = await asyncio.gather(
            groundedness_task, relevance_task, safety_task
        )

        result = EvaluationResult(
            groundedness=groundedness,
            relevance=relevance,
            safety=safety,
            timestamp=datetime.utcnow().isoformat()
        )

        interaction.evaluation = result
        self.tracer.record_interaction(interaction)
        self.interactions.append(interaction)

        logger.info(f"Evaluation complete - Groundedness: {groundedness}, Relevance: {relevance}, Safety: {safety}")
        return result

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get aggregated metrics from all interactions"""
        if not self.interactions:
            return {}

        evals = [i.evaluation for i in self.interactions if i.evaluation]
        return {
            "total_interactions": len(self.interactions),
            "avg_groundedness": sum(e.groundedness for e in evals) / len(evals) if evals else 0,
            "avg_relevance": sum(e.relevance for e in evals) / len(evals) if evals else 0,
            "avg_safety": sum(e.safety for e in evals) / len(evals) if evals else 0,
            "avg_latency_ms": sum(i.latency_ms for i in self.interactions) / len(self.interactions),
        }


class LocalVectorStore:
    """Local vector store using ChromaDB for document search"""

    def __init__(self, persist_dir: str = "./chroma_db"):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Use sentence transformers for embeddings
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_fn
        )
        
        logger.info(f"Vector store initialized at {persist_dir}")

    def add_documents(self, documents: List[Dict[str, str]]):
        """Add documents to the vector store"""
        ids = []
        texts = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            ids.append(doc.get("id", f"doc_{i}"))
            texts.append(doc["content"])
            metadatas.append({
                "source": doc.get("source", "unknown"),
                "title": doc.get("title", ""),
            })
        
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas
        )
        logger.info(f"Added {len(documents)} documents to vector store")

    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if "distances" in results else None
            })
        return docs


class LocalRAGChatAgent:
    """Local RAG Chat Agent mimicking Azure AI Foundry Agent Service"""

    def __init__(
        self,
        ollama_model: str = "llama3.2",
        chroma_dir: str = "./chroma_db",
        sample_docs_dir: str = "./sample_documents"
    ):
        self.ollama_model = ollama_model
        self.sample_docs_dir = sample_docs_dir
        
        # Initialize components
        self.vector_store = LocalVectorStore(chroma_dir)
        self.tracer = LocalTracer()
        self.evaluator = LocalEvaluationHooks(self.tracer)
        
        # Load agent instructions
        with open("agent_instructions.md", "r") as f:
            self.instructions = f.read()
        
        # Load sample documents into vector store
        self._load_sample_documents()

    def _load_sample_documents(self):
        """Load sample markdown documents into vector store"""
        docs_path = self.sample_docs_dir
        if not os.path.exists(docs_path):
            logger.warning(f"Sample docs directory not found: {docs_path}")
            return

        documents = []
        for filename in os.listdir(docs_path):
            if filename.endswith(".md"):
                filepath = os.path.join(docs_path, filename)
                with open(filepath, "r") as f:
                    content = f.read()
                
                # Chunk the document (simple approach: split by headers)
                chunks = self._chunk_document(content, filename)
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "id": f"{filename}_{i}",
                        "content": chunk,
                        "source": filename,
                        "title": filename.replace(".md", "").replace("_", " ")
                    })
        
        if documents:
            self.vector_store.add_documents(documents)
            logger.info(f"Loaded {len(documents)} document chunks from {len(os.listdir(docs_path))} files")

    def _chunk_document(self, content: str, filename: str) -> List[str]:
        """Simple document chunking by markdown headers"""
        # Split by headers (## or ###)
        import re
        sections = re.split(r'\n(?=#{2,3}\s)', content)
        chunks = []
        for section in sections:
            if len(section.strip()) > 100:  # Only keep substantial chunks
                chunks.append(section.strip())
        return chunks if chunks else [content]

    async def chat(self, user_message: str) -> AgentInteraction:
        """Process a user message using local RAG"""
        start_time = datetime.utcnow()

        async with self.tracer.trace_agent_call("local_agent_chat", {"user_message": user_message[:100]}) as span_id:
            # 1. Search vector store for relevant context
            search_results = self.vector_store.search(user_message, n_results=3)
            
            # 2. Build context from search results
            context_parts = []
            citations = []
            for result in search_results:
                context_parts.append(f"[Source: {result['metadata']['source']}]\n{result['content']}")
                citations.append(result['metadata']['source'])
            
            context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant documents found."
            
            # 3. Build prompt with instructions + context + user query
            system_prompt = self.instructions
            user_prompt = f"""Context from knowledge base:
{context}

User question: {user_message}

Answer based on the context above. Cite sources using [source: filename] format. If the answer is not in the context, admit uncertainty."""

            # 4. Call local LLM (Ollama)
            tools_used = ["vector_search"]
            try:
                response = ollama.chat(
                    model=self.ollama_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    options={"temperature": 0.1}
                )
                response_content = response["message"]["content"]
                # Estimate tokens (rough approximation)
                token_usage = {
                    "prompt_tokens": len(user_prompt.split()) * 1.3,
                    "completion_tokens": len(response_content.split()) * 1.3,
                    "total_tokens": int((len(user_prompt) + len(response_content)) / 4)
                }
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                response_content = f"Error calling local LLM: {e}. Make sure Ollama is running with model '{self.ollama_model}'."
                token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                tools_used.append("error")

            # Calculate latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            interaction = AgentInteraction(
                timestamp=start_time.isoformat(),
                user_query=user_message,
                agent_response=response_content,
                citations=citations,
                tools_used=tools_used,
                latency_ms=latency_ms,
                token_usage=token_usage,
            )

            # Evaluate the interaction
            await self.evaluator.evaluate_interaction(interaction)

            return interaction


# Custom tool implementations (same as Azure version)
async def get_employee_info(employee_id: str) -> Dict[str, Any]:
    return {
        "employee_id": employee_id,
        "name": "John Doe",
        "department": "Engineering",
        "hire_date": "2022-01-15",
        "vacation_balance": 12,
    }


async def create_it_ticket(issue_type: str, description: str) -> Dict[str, Any]:
    ticket_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{hash(description) % 10000:04d}"
    return {
        "ticket_id": ticket_id,
        "status": "Created",
        "issue_type": issue_type,
        "description": description,
    }


async def check_system_status(service_name: str) -> Dict[str, Any]:
    return {
        "service": service_name,
        "status": "healthy",
        "last_incident": None,
        "uptime_99": True,
    }


custom_functions = {
    "get_employee_info": get_employee_info,
    "create_it_ticket": create_it_ticket,
    "check_system_status": check_system_status,
}


async def main():
    """Main entry point for the local MCP server"""
    logger.info("Starting Local RAG Chat Agent MCP Server")

    # Configuration from env or defaults
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    chroma_dir = os.getenv("CHROMA_DIR", "./chroma_db")
    sample_docs_dir = os.getenv("SAMPLE_DOCS_DIR", "./sample_documents")

    agent = LocalRAGChatAgent(
        ollama_model=ollama_model,
        chroma_dir=chroma_dir,
        sample_docs_dir=sample_docs_dir
    )

    print("\n" + "="*60)
    print("Local RAG Chat Agent - Enterprise Policy Assistant")
    print(f"Model: {ollama_model} | Vector DB: {chroma_dir}")
    print("Type 'exit' to quit, 'metrics' to see evaluation summary")
    print("="*60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                break

            if user_input.lower() == "metrics":
                metrics = agent.evaluator.get_metrics_summary()
                print(json.dumps(metrics, indent=2))
                continue

            if not user_input:
                continue

            print("Agent: Thinking...")
            interaction = await agent.chat(user_input)

            print(f"\nAgent: {interaction.agent_response}\n")

            if interaction.citations:
                print(f"📚 Citations: {', '.join(interaction.citations)}")
            if interaction.tools_used:
                print(f"🔧 Tools used: {', '.join(interaction.tools_used)}")
            print(f"⏱️  Latency: {interaction.latency_ms:.0f}ms | Tokens: {interaction.token_usage['total_tokens']}")
            if interaction.evaluation:
                print(f"📊 Evaluation - Groundedness: {interaction.evaluation.groundedness:.2f}, "
                      f"Relevance: {interaction.evaluation.relevance:.2f}, "
                      f"Safety: {interaction.evaluation.safety:.2f}")
            print()

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            print(f"Error: {e}\n")

    # Print final metrics
    print("\n" + "="*60)
    print("Session Summary")
    print("="*60)
    metrics = agent.evaluator.get_metrics_summary()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())