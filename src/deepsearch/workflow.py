"""LangGraph workflow for DeepSearch."""

from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from deepsearch.agents import (
    PlannerAgent,
    ReflectorAgent,
    ResearcherAgent,
    VerifierAgent,
    WriterAgent,
)
from deepsearch.search.base import SearchTool
from deepsearch.state import (
    ResearchDepth,
    ResearchState,
    ResearchStatus,
)


def create_research_workflow(
    llm: BaseChatModel,
    search_tool: SearchTool,
) -> StateGraph:
    """Create the research workflow graph."""

    # Initialize agents
    planner = PlannerAgent(llm)
    researcher = ResearcherAgent(llm, search_tool)
    reflector = ReflectorAgent(llm)
    verifier = VerifierAgent(llm)
    writer = WriterAgent(llm)

    # Define nodes
    async def plan_node(state: ResearchState) -> ResearchState:
        """Create research plan with graph topology."""
        depth = ResearchDepth(state.get("depth", "balanced"))
        questions = await planner.plan(state["topic"], depth)

        # Set researcher depth for subsequent research
        researcher.set_depth(depth)

        return {
            **state,
            "plan": questions,
            "current_question_index": 0,
            "completed_question_ids": [],
            "status": ResearchStatus.RUNNING,
        }

    async def research_node(state: ResearchState) -> ResearchState:
        """Execute research on current question with dependency tracking."""
        plan = state.get("plan", [])
        idx = state.get("current_question_index", 0)
        completed_ids = state.get("completed_question_ids", [])

        if idx >= len(plan):
            return state

        question = plan[idx]

        # Check if dependencies are satisfied
        if question.dependencies:
            deps_satisfied = all(dep_id in completed_ids for dep_id in question.dependencies)
            if not deps_satisfied:
                # Skip this question for now, move to next
                return {
                    **state,
                    "current_question_index": idx + 1,
                }

        # Execute research
        findings, search_record = await researcher.research(question)

        return {
            **state,
            "findings": state.get("findings", []) + findings,
            "search_history": state.get("search_history", []) + [search_record],
            "current_question_index": idx + 1,
            "completed_question_ids": completed_ids + [question.id],
        }

    async def reflect_node(state: ResearchState) -> ResearchState:
        """Reflect on research progress."""
        reflection = await reflector.reflect(
            findings=state.get("findings", []),
            plan=state.get("plan", []),
            iteration=state.get("iteration", 0),
            max_iterations=state.get("max_iterations", 5),
        )

        # Add new questions to plan if any
        plan = state.get("plan", [])
        if reflection.new_questions:
            plan = plan + reflection.new_questions

        return {
            **state,
            "reflection": reflection,
            "plan": plan,
            "iteration": state.get("iteration", 0) + 1,
        }

    async def verify_node(state: ResearchState) -> ResearchState:
        """Verify findings."""
        verified = await verifier.verify(state.get("findings", []))

        return {
            **state,
            "verified_findings": verified,
        }

    async def write_node(state: ResearchState) -> ResearchState:
        """Write final report."""
        depth = ResearchDepth(state.get("depth", "balanced"))
        report = await writer.write(
            verified_findings=state.get("verified_findings", []),
            topic=state["topic"],
            depth=depth,
        )

        return {
            **state,
            "report": report,
            "status": ResearchStatus.COMPLETED,
        }

    # Define conditional edges
    def should_continue_researching(state: ResearchState) -> Literal["continue", "verify"]:
        """Decide whether to continue researching or move to verification."""
        plan = state.get("plan", [])
        idx = state.get("current_question_index", 0)
        reflection = state.get("reflection")
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 5)

        # First check: respect max_iterations limit
        if iteration >= max_iterations:
            return "verify"

        # Continue if there are more questions in plan
        if idx < len(plan):
            return "continue"

        # Check if reflection suggests more research
        if reflection and not reflection.is_complete:
            return "continue"

        # Otherwise move to verification
        return "verify"

    # Build graph
    workflow = StateGraph(ResearchState)

    workflow.add_node("plan", plan_node)
    workflow.add_node("research", research_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("write", write_node)

    # Set entry point
    workflow.set_entry_point("plan")

    # Add edges
    workflow.add_edge("plan", "research")

    workflow.add_conditional_edges(
        "research",
        should_continue_researching,
        {
            "continue": "reflect",
            "verify": "verify",
        },
    )

    workflow.add_edge("reflect", "research")
    workflow.add_edge("verify", "write")
    workflow.add_edge("write", END)

    return workflow.compile()


def create_llm(config: dict) -> BaseChatModel:
    """Create LLM instance based on config."""
    provider = config.get("provider", "openrouter")
    model = config.get("model", "openai/gpt-4o-mini")
    api_key = config.get("api_key")

    if provider == "openrouter":
        # OpenRouter requires full model name (e.g., "openai/gpt-4o-mini")
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.3,
            default_headers={
                "HTTP-Referer": "https://github.com/deepsearch-cli",
                "X-Title": "DeepSearch CLI",
            },
        )
    else:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0.3,
        )
