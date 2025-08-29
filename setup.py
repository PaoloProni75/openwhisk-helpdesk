"""
Setup configuration for OpenWhisk Helpdesk project
"""
from setuptools import setup, find_packages

with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="openwhisk-helpdesk",
    version="1.0.0",
    description="Modular helpdesk backend system for OpenWhisk with Ollama LLM support",
    author="Paolo Proni",
    author_email="paolo.proni@example.com",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "test-orchestrator=orchestrator.main:main",
            "test-similarity=similarity.main:main", 
            "test-ollama=ollama.main:main",
        ],
    },
)