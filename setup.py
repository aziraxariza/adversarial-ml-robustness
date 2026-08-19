from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="adversarial-ml-robustness",
    version="1.0.0",
    author="Ariza Wasim",
    author_email="ariza@example.com",
    description="Adversarial Machine Learning: Robustness Evaluation & Training",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aziraxariza/adversarial-ml-robustness",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "torch>=1.9.0",
        "torchvision>=0.10.0",
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        "tqdm>=4.62.0",
        "pyyaml>=5.4.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0", "black>=22.0.0", "flake8>=4.0.0"],
        "certified": ["randomized-smoothing>=0.1.0", "auto-attack>=0.1.0"],
    },
)
