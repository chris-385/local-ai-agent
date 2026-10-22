import ollama

messages = [
    {
        "role": "system",
        "content": "You are a helpful local AI assistant."
    }
]

print("Local AI Agent gestartet.")
print("Tippe 'exit', um das Programm zu beenden.\n")

while True:
    user_input = input("Du: ")

    if user_input.lower() == "exit":
        print("Agent beendet.")
        break

    messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    response = ollama.chat(
        model="llama3.2:3b",
        messages=messages
    )

    assistant_message = response["message"]["content"]

    messages.append(
        {
            "role": "assistant",
            "content": assistant_message
        }
    )

    print(f"\nAI: {assistant_message}\n")