import sys
from openqasm2qtrl.compiler import transpile_qasm

transpile_qasm(sys.argv[1])