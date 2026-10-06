"""
MCP Server for Azure AI Foundry Agent Service
Implements the complete Agent Service lifecycle: Create, Test, Trace, Evaluate, Optimize, Publish, Monitor

Features:
- End-to-end tracing with Application Insights
- Custom evaluation hooks for quality measurement
- OpenTelemetry instrumentation
- Agent Service integration
- Custom tool implementations
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Azure AI Foundry SDK
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    Agent,
    AgentThread,
    MessageRole,
    ToolSet,
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

# Load environment variables
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
AGENT_ID = os.getenv("AGENT_ID")
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

if not all([PROJECT_ENDPOINT, AGENT_ID, APPLICATIONINSIGHTS_CONNECTION_STRING]):
    raise ValueError(
        "Missing required environment variables: PROJECT_ENDPOINT, AGENT_ID, APPLICATIONINSIGHTS_CONNECTION_STRING"
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
        # Set up tracer provider
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

        # Configure Azure Monitor exporter
        configure_azure_monitor(
            connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING,
            logger_name=__name__,
        )

        # Instrument common libraries
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

        # Run evaluations in parallel
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
    """Main agent class integrating with Azure AI Foundry Agent Service"""

    def __init__(self):
        self.project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )
        self.tracer = MCPTracer()
        self.evaluator = EvaluationHooks(self.tracer)
        self.agent: Optional[Agent] = None
        self.thread: Optional[AgentThread] = None

        # Load agent instructions
        with open("agent_instructions.md", "r") as f:
            self.instructions = f.read()

    async def initialize(self):
        """Initialize agent connection and create thread"""
        logger.info(f"Connecting to agent: {AGENT_ID}")

        # Get existing agent from Playground
        self.agent = self.project_client.agents.get_agent(AGENT_ID)
        logger.info(f"Loaded agent: {self.agent.name} (ID: {self.agent.id})")

        # Create a new thread for this session
        self.thread = self.project_client.agents.create_thread()
        logger.info(f"Created thread: {self.thread.id}")

    async def chat(self, user_message: str) -> AgentInteraction:
        """Process a user message and return the interaction record"""
        start_time = datetime.utcnow()

        async with self.tracer.trace_agent_call("agent_chat", {"user_message": user_message[:100]}) as span:
            # Send user message
            self.project_client.agents.create_message(
                thread_id=self.thread.id,
                role=MessageRole.USER,
                content=user_message,
            )

            # Run the agent
            run = self.project_client.agents.create_and_process_run(
                thread_id=self.thread.id,
                agent_id=self.agent.id,
            )

            # Wait for completion
            while run.status in ["queued", "in_progress", "requires_action"]:
                await asyncio.sleep(1)
                run = self.project_client.agents.get_run(thread_id=self.thread.id, run_id=run.id)

            if run.status == "failed":
                raise RuntimeError(f"Agent run failed: {run.last_error}")

            # Get the assistant's response
            messages = self.project_client.agents.list_messages(thread_id=self.thread.id)
            assistant_messages = [m for m in messages.data if m.role == MessageRole.ASSISTANT]
            latest_response = assistant_messages[0] if assistant_messages else None

            if not latest_response:
                raise RuntimeError("No response from agent")

            response_content = latest_response.content[0].text.value if latest_response.content else ""

            # Extract citations and tools used
            citations = self._extract_citations(latest_response)
            tools_used = self._extract_tools_used(run)

            # Calculate latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Get token usage
            token_usage = {
                "prompt_tokens": run.usage.prompt_tokens if run.usage else 0,
                "completion_tokens": run.usage.completion_tokens if run.usage else 0,
                "total_tokens": run.usage.total_tokens if run.usage else 0,
            }

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

    def _extract_citations(self, message) -> List[str]:
        """Extract citation references from agent response"""
        citations = []
        if hasattr(message, 'content') and message.content:
            for content_item in message.content:
                if hasattr(content_item, 'text') and hasattr(content_item.text, 'annotations'):
                    for annotation in content_item.text.annotations:
                        if hasattr(annotation, 'file_citation'):
                            citations.append(annotation.file_citation.file_id)
                        elif hasattr(annotation, 'file_path'):
                            citations.append(annotation.file_path.file_id)
        return citations

    def _extract_tools_used(self, run) -> List[str]:
        """Extract tools used during the run"""
        tools = []
        if hasattr(run, 'required_action') and run.required_action:
            if hasattr(run.required_action, 'submit_tool_outputs'):
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    tools.append(tool_call.function.name)
        return tools

    async def close(self):
        """Clean up resources"""
        logger.info("Closing agent session")
        if self.thread:
            # Thread cleanup if needed
            pass


# Custom tool implementations
async def get_employee_info(employee_id: str) -> Dict[str, Any]:
    """Get basic employee information (mock implementation)"""
    # In production, this would call HR system API
    return {
        "employee_id": employee_id,
        "name": "John Doe",
        "department": "Engineering",
        "hire_date": "2022-01-15",
        "vacation_balance": 12,
    }


async def create_it_ticket(issue_type: str, description: str) -> Dict[str, Any]:
    """Create an IT support ticket (mock implementation)"""
    # In production, this would call ServiceNow or similar
    ticket_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{hash(description) % 10000:04d}"
    return {
        "ticket_id": ticket_id,
        "status": "Created",
        "issue_type": issue_type,
        "description": description,
    }


async def check_system_status(service_name: str) -> Dict[str, Any]:
    """Check system/service health status (mock implementation)"""
    # In production, this would call monitoring API
    return {
        "service": service_name,
        "status": "healthy",
        "last_incident": None,
        "uptime_99": True,
    }


# Register custom functions for the agent
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

    # Print final metrics
    print("\n" + "="*60)
    print("Session Summary")
    print("="*60)
    metrics = agent.evaluator.get_metrics_summary()
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())