from setuptools import setup, find_packages

setup(
    name="researcher",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "flask",
        "python-dotenv",
        "langchain",
        "faiss-cpu",
        "sentence-transformers",
        "beautifulsoup4",
        "requests",
        "litellm",
        "langchain-google-genai",
    ],
)
