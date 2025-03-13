from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rufus-web-crawler",
    version="0.1.0",
    author="Nikhil Malkari",
    author_email="nikhilmalkari8@gmail.com",
    description="An intelligent web scraper and content analyzer with AI-powered relevance scoring",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nikhilmalkari8/rufus-web-crawler",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "playwright>=1.20.0",
        "openai>=0.27.0",
        "nltk>=3.6.0",
        "asyncio>=3.4.3",
    ],
    entry_points={
        "console_scripts": [
            "rufus=rufus.client:cli_main",
        ],
    },
)