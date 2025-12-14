#!/usr/bin/env python3
"""Setup script for notion-sync-tools."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="notion-sync-tools",
    version="1.0.0",
    description="Bidirectional markdown ↔ Notion sync tools with full formatting preservation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Graeme Ross",
    author_email="",
    url="https://github.com/graemejross/notion-sync-tools",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    install_requires=[
        "PyYAML>=5.4.0",  # For YAML configuration file support
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ]
    },
    entry_points={
        "console_scripts": [
            "markdown-to-notion=notion_sync.markdown_to_notion:main",
            "notion-to-markdown=notion_sync.notion_to_markdown:main",
            "bulk-upload-notion=notion_sync.bulk_upload:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Documentation",
        "Topic :: Text Processing :: Markup :: Markdown",
    ],
    keywords="notion markdown sync documentation api",
)
