from setuptools import setup, find_packages

setup(
    name="fpllab",
    version="0.1.0",
    description="FPL + Understat projections",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31",
        "pandas>=2.0",
        "streamlit>=1.32",
        "pulp>=2.7",
    ],
)
