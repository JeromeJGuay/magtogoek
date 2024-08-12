import os
from setuptools import find_packages, setup

VERSION = "1.0.0"


def read_file(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="magtogoek",
    version=VERSION,
    author="JeromeJGuay,",
    author_email="jerome.guay@dfo-mpo.gc.ca",
    description="""Magtogoek is a Linux python package and command line application (CLI) for processing ocean data. At the moment, only Accoustisc Doopler Current Profiler (ADCP) data can be processed. This package is developped by the Scientific Advice, Information and Support Branch at the Fisheries and Ocean Canada Maurice-Lamontagne Institute.""",
    long_description=read_file('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/iml-gddaiss/magtogoek",
    install_requires=[
        # "pytest",
        # "xarray",
        # "matplotlib>=3.5.0",
        # "scipy>=1.7.0",
        # "numpy",
        # "pandas",
        # "pathlib",
        # "nptyping",
        # "datetime",
        # "configparser",
        # "pathlib",
        # "click==7.1.2", this may have been important
        # "tqdm>=4.59.0",
        # "pygeodesy",
        # "gpxpy",
        # "pynmea2",
        # "cmocean~=2.0",
        # "obsub",
        # "crc16",
        # "pyqt5",
        # "gsw",
        # "pycurrents @ hg+https://currents.soest.hawaii.edu/hgstage/pycurrents",
    ],
    packages=find_packages(),
    package_data={"": ["*.json"], "magtogoek/tests": ["files/*.*"]},
    include_package_data=True,
    classifiers=["Programming Language :: Python :: 3"],
    python_requires="~=3.8",
    entry_points={"console_scripts": ["mtgk=magtogoek.app:magtogoek", ]},
)
