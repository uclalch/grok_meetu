from setuptools import setup, find_packages

setup(
    name="grok_meetu",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "cassandra-driver",
        "pandas",
        "scikit-surprise",
        "python-dotenv",
        "psutil",
        "colorama",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "grok-start=backend.service_manager:start",
            "grok-stop=backend.service_manager:stop",
            "grok-restart=backend.service_manager:restart"
        ]
    }
) 