import codecs, os
from setuptools import setup, find_packages
import re


here = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# https://packaging.python.org/guides/single-sourcing-package-version/
def read(*parts):
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()

def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='qtrl',
    version=find_version('qtrl', '_version.py'),
    description='Control software for the QNL lab and AQT testbed.',
    long_description=long_description,

    url='http://github.com/qnl/qtrl',

    author='Brad Mitchell, Dar Dahlen, Ravi Naik, Wim Lavrijsen',
    maintainer='Wim Lavrijsen',
    maintainer_email='WLavrijsen@lbl.gov',

    license='LBNL BSD',

    install_requires=[
        'IPython',
        'jupyter',
        'cycler',
        'seaborn',
        'scipy',
        'numpy',
        'matplotlib',
        'ruamel.yaml',
        'lmfit',
        'mkl',
        'sklearn',
        'pandas',
        'qcodes',
        'pyqtgraph',  # for qcodes.plots.pyqtgraph
        'PyQt5',      # id.
    ],

    package_dir={'': '.'},
    packages=find_packages('.', include=['qtrl']),

    keywords='quantum computing',

    zip_safe=False,    # Why?
)
