from graph.workflow import graph
from langgraph.types import Command

THREAD_CONFIG = {
    "configurable": {
        "thread_id": "research-001"
    }
}

result = graph.invoke(
    {
        "topic": "What are the benefits of solar energy?"
    },
    config=THREAD_CONFIG
)

decision = input(
    "approve or reject: "
)

final_result = graph.invoke(
    Command(resume=decision),
    config=THREAD_CONFIG
)

print(final_result)