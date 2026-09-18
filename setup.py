"""
Setup script for RNA-Seq Data Analysis Program
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="rna-seq-data-analyzer",
    version="1.2.11",
    author="RNA-Seq Analysis Team",
    author_email="your-email@example.com",
    description="A comprehensive tool for RNA-Seq data analysis and visualization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/rna-seq-data-view",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",   # pandas 3.x 요구사항 (PoC F11 실측 2026-09-02)
    install_requires=[
        "PyQt6>=6.4.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "openpyxl>=3.1.0",
        "scipy>=1.10.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "matplotlib-venn>=0.11.0",
        "upsetplot>=0.8.0",
        # GO/KEGG Enrichment Engine (plan §8, PoC 확정 2026-09-02)
        "gseapy>=1.1.0",
        "goatools>=1.6.0",
        "statsmodels>=0.14.0,<0.15",  # goatools fdr_bh 전용 — 0.15 sandbox.multicomp.multipletests 제거(P0-3)
        "requests>=2.28.0",
        "mygene>=3.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.0",
            "pytest-qt>=4.2.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rna-seq-analyzer=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
