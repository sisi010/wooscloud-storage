"""
Setup configuration for WoosCloud Storage Python client
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="wooscloud",
    version="1.0.0",
    author="WoosCloud Team",
    author_email="support@woos-ai.com",
    description="Simple, powerful, and scalable cloud storage for Python applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sisi010/wooscloud-storage",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
    ],
    keywords="cloud storage database api rest wooscloud",
    project_urls={
        "Documentation": "https://wooscloud-storage-production.up.railway.app/api/docs",
        "Source": "https://github.com/sisi010/wooscloud-storage",
        "Bug Reports": "https://github.com/sisi010/wooscloud-storage/issues",
    },
)