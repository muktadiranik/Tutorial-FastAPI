import dotenv
import os
from openai import OpenAI

dotenv.load_dotenv()


llm = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant that answers questions. Give short and helpful answers.",
    }
]


def bot(message):
    messages.append({"role": "user", "content": message})

    response = llm.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=messages,
    )

    text_response = response.choices[0].message.content

    messages.append({"role": "assistant", "content": text_response})

    return text_response


def chat():
    while True:
        user_input = input("Ask something(type 'q' to quit): ").strip().lower()
        if user_input == "q":
            break
        bot_answer = bot(user_input)
        print(bot_answer)


def main():
    chat()


if __name__ == "__main__":
    main()
