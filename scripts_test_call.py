"""First Token Factory test call: python scripts_test_call.py"""
from app.llm import chat

print(chat([{"role": "user", "content": "Say hello in one sentence."}]))
