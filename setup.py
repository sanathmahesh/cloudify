"""
Setup configuration for Cloudify.
"""

from pathlib import Path
from setuptools import setup, find_packages

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().split("\n")
        if line.strip() and not line.startswith("#")
    ]
else:
    requirements = []

setup(
    name="cloudify",
    version="1.0.0",
    description="Automated cloud migration system for Spring Boot + React apps to GCP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cloudify Team",
    author_email="team@cloudify.dev",
    url="https://github.com/yourusername/cloudify",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "cloudify=migration_orchestrator:app",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    keywords="cloud migration gcp docker kubernetes spring-boot react ai agents",
)
