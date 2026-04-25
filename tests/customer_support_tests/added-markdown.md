diff --git a/agents/customer_support.py b/agents/customer_support.py
index 6061ef4..1410afa 100644
--- a/agents/customer_support.py
+++ b/agents/customer_support.py
@@ -28,6 +28,24 @@ def _get_llm():
     return OllamaLLM(model=ollama_model)
 
 
+
+# ==========================================================
+# Markdown Response Formatter (UI improvement)
+# ==========================================================
+
+def _format_response(query: str, response: str) -> str:
+    """
+    Wrap the LLM plain-text answer in lightweight Markdown so
+    Chainlit renders it cleanly in the chat UI.
+    """
+    return (
+        f"**Here's what I found:**\n\n"
+        f"{response}\n\n"
+        f"---\n"
+        f"*Need more help? Type your question or ask to speak to a human agent.*"
+    )
+
+
 # ==========================================================
 # Responsible Prompt Design (Module 1)
 # ==========================================================
@@ -152,11 +170,13 @@ def customer_support_agent(state: dict) -> dict:
     # --- Return path: LangGraph (messages-based state) (Module 3) ---
     if "messages" in state:
         from langchain_core.messages import AIMessage
-        reply = (
-            "I'm sorry, I don't have that information. "
-            "Let me connect you with a human agent."
-            if escalate else response or ""
-        )
+        if escalate:
+            reply = (
+                "I\'m sorry, I don\'t have that information. "
+                "Let me connect you with a human agent. 🙏"
+            )
+        else:
+            reply = _format_response(query, response or "")
         return {
             "messages":    [AIMessage(content=reply)],
             "current_agent": "customer_support_agent",
