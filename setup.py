import setuptools
import time

with open("requirements.txt") as fp:
    requirements = fp.read().splitlines()

setuptools.setup(
    name="schttp",
    author="h0nda",
    description="A faster alternate for the requests library",
    version=str(time.time()),
    url="https://github.com/h0nde/schttp",
    packages=setuptools.find_packages(),
    classifiers=[],
    install_requires=requirements
)
