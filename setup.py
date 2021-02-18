import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ad_query_proxy",
    version="0.5.1",
    author="Bernd Kampe",
    author_email="bernd.kampe@uni-jena.de",
    description="This proxy translates ontology IDs into Elasticsearch search terms and queries a specifically prepared index.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AquaDiva-INFRA1/ad-query-proxy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Framework :: Flask",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    python_requires=">=3.6",
)
