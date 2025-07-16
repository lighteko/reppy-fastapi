# /app/rag/chain.py
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from app.rag.retriever import get_retriever
from app.rag.prompts import get_prompt_template
from app.rag.llm import get_llm


def format_docs(docs):
    """
    Helper function to format the retrieved documents into a single string.
    """
    return "\n\n".join(doc.page_content for doc in docs)


def create_rag_chain():
    """
    Creates and returns a complete RAG (Retrieval-Augmented Generation) chain.
    This chain orchestrates the retriever, prompt, LLM, and output parser.

    The structure of this chain is designed for clarity and easy modification.
    It includes a parallel step to fetch documents and pass the question through,
    which is a common and effective pattern in LCEL.
    """
    retriever = get_retriever()
    prompt = get_prompt_template()
    llm = get_llm()

    # This part of the chain is responsible for retrieving documents
    # and formatting them.
    retrieval_chain = {
        "context": retriever | format_docs,
        "question": RunnablePassthrough()
    }

    # This is the main chain that combines retrieval with generation.
    rag_chain = (
            retrieval_chain
            | prompt
            | llm
            | StrOutputParser()
    )

    # To return source documents alongside the answer, we wrap the chain
    # in another RunnableParallel.
    chain_with_sources = RunnableParallel(
        {"answer": rag_chain, "docs": retriever}
    )

    return chain_with_sources
