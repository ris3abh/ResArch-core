# File: setup.py
from setuptools import setup, find_packages

setup(
    name="spinscribe",
    version="0.1.0",
    description="SpinScribe Multi-Agent Content Creation System",
    long_description="An advanced platform that leverages AI agents working in concert to streamline content creation for various clients.",
    long_description_content_type="text/plain",
    packages=find_packages(),
    install_requires=[
        "camel-ai[all]==0.2.70",
    ],
    python_requires=">=3.8",
    author="Spniutech",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
    ],
)