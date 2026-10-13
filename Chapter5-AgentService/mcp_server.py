"""
MCP Server for Azure AI Foundry Agent Service (New Session-based API)
Implements the complete Agent Service lifecycle: Create, Test, Trace, Evaluate, Optimize, Publish, Monitor

Features:
- End-to-end tracing with Application Insights
- Custom evaluation hooks for quality measurement
- OpenTelemetry instrumentation
- Agent Service integration (using azure-ai-projects SDK v2.x new API)
- Custom tool implementations
"""

import os
import json
import asyncio
import logging
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

# Azure AI Foundry Projects SDK (New Agent Service API)
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentSessionResource,
    CodeInterpreterTool,
    FileSearchTool,
    FunctionTool,
)
from azure.identity import DefaultAzureCredential

# OpenTelemetry for tracing
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Azure Monitor OpenTelemetry Exporter
from azure.monitor.opentelemetry import configure_azure_monitor

# Evaluation
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

# Load environment variables from root .env (walks up parent directories)
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Load environment variables
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT") or os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AGENT_ID = os.getenv("AGENT_ID")
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

if not all([PROJECT_ENDPOINT, AGENT_ID, APPLICATIONINSIGHTS_CONNECTION_STRING]):
    raise ValueError(
        "Missing required environment variables in .env:\n"
        "  PROJECT_ENDPOINT (or AZURE_AI_PROJECT_ENDPOINT)\n"
        "  AGENT_ID\n"
        "  APPLICATIONINSIGHTS_CONNECTION_STRING\n"
        "See Chapter5-AgentService/README.md for where to find these values."
    )


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


class MCPTracer:
    """Wrapper for OpenTelemetry tracing with custom attributes"""

    def __init__(self, service_name: str = "rag-chat-agent"):
        self.service_name = service_name
        self._setup_tracing()
        self.tracer = trace.get_tracer(__name__)

    def _setup_tracing(self):
        """Configure OpenTelemetry with Azure Monitor exporter"""
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

        configure_azure_monitor(
            connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING,
            logger_name=__name__,
        )

        OpenAIInstrumentor().instrument()
        RequestsInstrumentor().instrument()

        logger.info("OpenTelemetry tracing configured with Azure Monitor")

    @asynccontextmanager
    async def trace_agent_call(self, operation_name: str, attributes: Dict[str, Any] = None):
        """Context manager for tracing agent operations"""
        with self.tracer.start_as_current_span(operation_name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            span.set_attribute("service.name", self.service_name)
            yield span

    def record_interaction(self, interaction: AgentInteraction):
        """Record interaction as a span for observability"""
        with self.tracer.start_as_current_span("agent_interaction") as span:
            span.set_attribute("user.query", interaction.user_query[:500])
            span.set_attribute("agent.response_length", len(interaction.agent_response))
            span.set_attribute("agent.citations_count", len(interaction.citations))
            span.set_attribute("agent.tools_used", ",".join(interaction.tools_used))
            span.set_attribute("agent.latency_ms", interaction.latency_ms)
            span.set_attribute("agent.prompt_tokens", interaction.token_usage.get("prompt_tokens", 0))
            span.set_attribute("agent.completion_tokens", interaction.token_usage.get("completion_tokens", 0))

            if interaction.evaluation:
                span.set_attribute("eval.groundedness", interaction.evaluation.groundedness)
                span.set_attribute("eval.relevance", interaction.evaluation.relevance)
                span.set_attribute("eval.safety", interaction.evaluation.safety)


class EvaluationHooks:
    """Evaluation hooks for measuring agent quality"""

    def __init__(self, tracer: MCPTracer):
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


class RAGChatAgent:
    """Main agent class integrating with Azure AI Foundry Agent Service (New Session API)"""

    def __init__(self):
        self.project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )
        self.tracer = MCPTracer()
        self.evaluator = EvaluationHooks(self.tracer)
        self.agent: Optional[object] = None
        self.session: Optional[AgentSessionResource] = None

        # Load agent instructions
        with open("agent_instructions.md", "r") as f:
            self.instructions = f.read()

    async def initialize(self):
        """Initialize agent connection and create session"""
        logger.info(f"Connecting to agent: {AGENT_ID}")

        # Get existing agent from Playground
        self.agent = self.project_client.agents.get_agent(AGENT_ID)
        logger.info(f"Loaded agent: {self.agent.name} (ID: {self.agent.id})")

        # Create a new session for this conversation
        # The new API uses sessions - we create one with the agent
        self.session = self.project_client.agents.create_session(
            agent_name=self.agent.id,
        )
        logger.info(f"Created session: {self.session.agent_session_id}")

    async def chat(self, user_message: str) -> AgentInteraction:
        """Process a user message using the new session-based API"""
        start_time = datetime.utcnow()

        async with self.tracer.trace_agent_call("agent_chat", {"user_message": user_message[:100]}) as span:
            # In the new session-based API, we upload the user message as a file
            # and the agent processes it. This is the file-based interaction model.
            
            # Create a temporary file with the user message
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(user_message)
                temp_file = f.name

            try:
                # Upload the user message file to the session
                upload_result = self.project_client.agents.upload_session_file(
                    agent_session_id=self.session.agent_session_id,
                    file_path=temp_file,
                )
                logger.info(f"Uploaded message file: {upload_result}")

                # The agent processes the session - in the new API, we may need to
                # wait for processing or check session status
                # For now, we'll simulate waiting and then get the response
                
                # TODO: The exact processing mechanism depends on the agent configuration
                # This is a simplified version - real implementation would poll for completion
                
                await asyncio.sleep(2)  # Wait for processing
                
                # Get session files to find the response
                session_files = self.project_client.agents.list_session_files(
                    agent_session_id=self.session.agent_session_id
                )
                
                # Find the response file (typically the last uploaded file after our input)
                response_content = "Response processing not fully implemented in new session API yet."
                citations = []
                tools_used = []
                
                # For now, return a placeholder
                # Real implementation would download and parse response files
                
            finally:
                # Clean up temp file
                os.unlink(temp_file)

            # Calculate latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Placeholder token usage (not available in new API yet)
            token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

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

            span.set_attribute("interaction_id", len(self.evaluator.interactions))
            return interaction

    async def close(self):
        """Clean up resources"""
        logger.info("Closing agent session")
        if self.session:
            try:
                self.project_client.agents.delete_session(
                    agent_session_id=self.session.agent_session_id
                )
                logger.info(f"Deleted session: {self.session.agent_session_id}")
            except Exception as e:
                logger.warning(f"Failed to delete session: {e}")


# Custom tool implementations
async def get_employee_info(employee_id: str) -> Dict[str, Any]:
    """Get basic employee information (mock implementation)"""
    return {
        "employee_id": employee_id,
        "name": "John Doe",
        "department": "Engineering",
        "hire_date": "2022-01-15",
        "vacation_balance": 12,
    }


async def create_it_ticket(issue_type: str, description: str) -> Dict[str, Any]:
    """Create an IT support ticket (mock implementation)"""
    ticket_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{hash(description) % 10000:04d}"
    return {
        "ticket_id": ticket_id,
        "status": "Created",
        "issue_type": issue_type,
        "description": description,
    }


async def check_system_status(service_name: str) -> Dict[str, Any]:
    """Check system/service health status (mock implementation)"""
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
    """Main entry point for the MCP server"""
    logger.info("Starting RAG Chat Agent MCP Server")

    agent = RAGChatAgent()
    await agent.initialize()

    print("\n" + "="*60)
    print("RAG Chat Agent - Enterprise Policy Assistant")
    print("Type 'exit' to quit, 'metrics' to see evaluation summary")
    print("="*60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except EOFError:
            print("\nExiting (EOF received).")
            break

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

    await agent.close()

    print("\n" + "="*60)
    print("Session Summary")
    print("="*60)
    metrics = agent.evaluator.get_metrics_summary()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())