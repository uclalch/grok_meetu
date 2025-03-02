from setuptools import setup, find_packages

setup(
    name="grok_meetu",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.109.2",
        "uvicorn==0.27.1",
        "python-dotenv==1.0.1",
        "cassandra-driver==3.28.0",
        "pandas==2.2.0",
        "scikit-surprise==1.1.3",
        "pydantic==2.6.1"
    ],
) 