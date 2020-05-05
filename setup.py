from setuptools import setup, find_packages
import os

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
QTRL_DEP = f'qtrl @ file://localhost{PKG_DIR}/qtrl'
setup(
    name='openqasm2qtrl',
    version='0.1.0',
    description='Generate qtrl given IBM OpenQasm',
    url='https://github.com/ethanhs/openqasm_to_qtrl',
    install_requires=['numpy',QTRL_DEP],
    packages=find_packages(exclude='qtrl/*')
)
