from typing import List
from langchain_core.messages import BaseMessage, ToolMessage

def get_recent_messages(messages: List[BaseMessage], limit: int = 8) -> List[BaseMessage]:
    # 合并相邻重复消息（按类型和 content 区分），避免重复处理
    if not messages:
        return []
    deduped = []
    for m in messages:
        if not deduped:
            deduped.append(m)
            continue
        prev = deduped[-1]
        if type(prev) is type(m) and getattr(prev, 'content', None) == getattr(m, 'content', None):
            continue
        deduped.append(m)
    messages = deduped
    if len(messages) <= limit:
        return messages
    recent = messages[-limit:]
    if recent and isinstance(recent[0], ToolMessage):
        if len(messages) > limit:
            recent = messages[-(limit+1):]
    return recent

from langgraph.graph import END

def should_continue(state):
    last_msg = state['messages'][-1]
    return "tools" if (hasattr(last_msg, "tool_calls") and last_msg.tool_calls) else END


def transport_should_continue(state):
    if state.get("selected_transport"):
        return END
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END
