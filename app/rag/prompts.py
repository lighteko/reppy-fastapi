# /app/rag/prompts.py
from langchain_core.prompts import ChatPromptTemplate


def get_prompt_template():
    """
    Creates and returns a ChatPromptTemplate for the RAG chain.

    The prompt is a crucial component that instructs the LLM on how to use
    the retrieved context to answer the user's question. It's designed to be
    clear and concise to guide the model effectively.
    """
    template = """
    You are an expert assistant for question-answering tasks.
    Use the following pieces of retrieved context to answer the question.
    If you don't know the answer, just say that you don't know.
    Be concise and helpful.

    Question: {question}

    Context:
    {context}

    Answer:
    """

    prompt = ChatPromptTemplate.from_template(template)
    return prompt
