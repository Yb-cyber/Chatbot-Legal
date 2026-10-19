import json
import uuid
from datetime import datetime
from typing import List, Dict

import requests

BASE_URL = "http://localhost:8000"
MAX_HISTORY = 10


class ChatClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        self.history: List[Dict[str, str]] = []

    def send_message(self, message: str, mode: str = "hybrid") -> str:
        payload = {
            "question": message,
            "mode": mode,
            "top_k": 50,
            "only_need_context": False,
        }

        if self.history:
            payload["conversation_history"] = self.history[-MAX_HISTORY:]

        try:
            response = requests.post(
                f"{self.base_url}/query",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("answer", "")

            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": answer})

            return answer
        except requests.exceptions.RequestException as e:
            return f"Error: {e}"

    def show_history(self):
        if not self.history:
            print("No hay historial de conversación.")
            return

        print("\n" + "=" * 60)
        print("HISTORIAL DE CONVERSACIÓN")
        print("=" * 60)
        for i in range(0, len(self.history), 2):
            user_msg = self.history[i]["content"] if i < len(self.history) else ""
            assistant_msg = self.history[i + 1]["content"] if i + 1 < len(self.history) else ""
            print(f"\nTú: {user_msg}")
            print(f"RAG: {assistant_msg}")
        print("\n" + "=" * 60)

    def clear_history(self):
        self.history = []
        print("Historial eliminado.")

    def run(self):
        print("=" * 60)
        print("  CHAT RAG - Asistente Legal para Freelancers")
        print("=" * 60)
        print(f"Session ID: {self.session_id}")
        print("Comandos: /exit, /history, /clear")
        print("-" * 60)

        while True:
            try:
                message = input("\nTú: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n¡Hasta luego!")
                break

            if not message:
                continue

            if message == "/exit":
                print("\n¡Hasta luego!")
                break
            elif message == "/history":
                self.show_history()
                continue
            elif message == "/clear":
                self.clear_history()
                continue

            print("\nRAG: ", end="", flush=True)
            answer = self.send_message(message)
            print(answer)


if __name__ == "__main__":
    client = ChatClient()
    client.run()
