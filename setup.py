from setuptools import setup, find_packages

setup(
    name="nexustalk",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "dealflow>=0.1.3",
        "fastapi>=0.95.0",
        "uvicorn>=0.21.1",
        "boto3>=1.26.0",
        "pydantic>=2.0.0",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "python-multipart>=0.0.6",
        "pymongo>=4.3.3",
        "pynamodb>=5.4.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "black>=23.3.0",
            "isort>=5.12.0",
            "mypy>=1.2.0",
            "pytest-cov>=4.1.0",
        ]
    },
    python_requires=">=3.12",
)
