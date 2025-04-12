from setuptools import setup, find_packages

with open("dependencies.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="shl-assessment-recommender",
    version="1.1.0",
    packages=find_packages(),
    install_requires=requirements,
    author="Your Name",
    author_email="your.email@example.com",
    description="An SHL Assessment Recommendation System that suggests relevant assessments based on job descriptions",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/YOUR_USERNAME/shl-assessment-recommender",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)