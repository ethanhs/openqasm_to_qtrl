'''
A compiler to serve as a bridge between qiskit and qtrl
Input format: either qiskit code or OpenQASM code (likely the latter)
Output format: qtrl list of strings formatted as follows:
    'Q0/X90'
'''
import sys
import numpy as np
import re

custom_gates = {}

def compile_qasm(file_name):
    l = [line.rstrip('\n') for line in open(file_name)][2:]
    output = []
    qubit_names = []

    global custom_gates
    on_custom = False
    curr_custom = []

    for line in l:
        # if on_custom and ('}' not in line):
        #     curr_custom.append(line)
        # elif on_custom and ('}' in line):
        #     index = np.argwhere(np.array([ch for ch in line]) == '}')[0][0]
        #     curr_custom.append(line[:index])
        #     on_custom = False
        if line[:7] == "include" or line[:8] == "OPENQASM":
            pass
        elif line[:4] == 'qreg':
            # Add string of qubit name to list of qubits we may draw from?
            n = re.match(r'qreg\s[a-z][A-Za-z0-9_]*\[([1-9]+[0-9]*|0)\];', line).group(1)
            for i in range(int(n)):
                q_name = "Q"+str(i)
                qubit_names.append(q_name)
        elif line[:4] == 'creg':
            # Simply pass if the input to the qpu does not
            # need to keep track of classical registers
            pass
        elif line[:4] == 'gate':
            # Parse things inside the brackets to list of gates,
            # add to dict of prebuilt gate names
            gate_name, rotations = parse_custom_gate(line[5:])
            custom_gates[gate_name] = rotations
            pass
        elif line[:7] == 'measure':
            # Do not have to handle measurement
            pass
        elif line[:7] == 'barrier':
            pass
        elif line =='':
            pass
        else:
            # It's a gate operation!
            q_name, gates = parse_gate_and_q(line[:len(line) - 1])
            for gate in gates:
                if len(q_name) == 2:

                    if gate == 'CNOT':
                        output.append('{},{}/CNOT'.format(q_name[0].upper(),\
                                                        q_name[1].upper()))
                    elif gate == 'swap':
                        output.append( \
                            ['{},{}/CNOT'.format(q_name[0].upper(), q_name[1].upper()), \
                            '{},{}/CNOT'.format(q_name[1].upper(), q_name[0].upper())])
                    else:
                        output.append(q_name[1].upper()+'/' + gate)
                else:
                    output.append(q_name[0].upper()+'/' + gate)

    print("---------------")
    print(output)
    with open('{}_qtrl.txt'.format(file_name[:len(file_name) - 5]), 'w') as f:
        for item in output:
            f.write("%s\n" % item)
    print("Output saved!")
    return output


def parse_q_name(line_seg):
    q_name = ""
    for ch in line_seg:
        if ch != '[' and ch != ']':
            q_name += ch
    return q_name

def parse_gate_and_q(line):
    #parse parameters in here?
    gate = ""
    params = []
    p_count = 0
    q_name = []
    q_count = 0
    on_gate = True
    on_params = False

    for ch in line:
        if on_gate and ch != ' ' and ch != '(':
            gate += ch
        elif on_params and (ch != ',') and (ch != ')'):
            params[p_count] = params[p_count]+ch
        elif on_params and ch ==',':
            params.append('')
            p_count += 1
        elif ch == ' ':
            on_gate = False
            on_params = False
            q_name.append('')
        elif ch == '(':
            on_gate = False
            on_params = True
            params.append('')
        elif ch ==')':
            on_params = False
            pass
        elif not on_params and not on_gate and ch ==',':
            q_name.append('')
            q_count += 1
        elif (ch != '[') and (ch != ']') and (ch !=','):
            q_name[q_count] = q_name[q_count] + ch
    gate = determine_gate(q_name, gate, params)

    return q_name, gate

''' TODO: finish this!'''
def parse_custom_gate(line_seg):
    comb = []
    for gate in custom_gates[line_seg]:
        comb.append(determine_gate(gate))
    return comb


import qtrl_repr
from qtrl_repr import paramless_reprs as reps
from qtrl_repr import p

#Compute angles of gate operations here
#use combination of Rz * Rx(90) * Rz * Rx(90) * Rz to represent:
def determine_gate(q_name, line_seg, params=None):
    if line_seg in reps.keys():
        return reps[line_seg]
    elif line_seg[:10] in list(custom_gates.keys()):
        if params is not None:
            return custom_gates[line_seg](params)
        else:
            return custom_gates[line_seg]
    elif params != []:
        switcher = {'u3':qtrl_repr.u3,\
                    'u2':qtrl_repr.u2,\
                    'u1':qtrl_repr.u1,\
                    'rx':qtrl_repr.rx,\
                    'ry':qtrl_repr.ry,\
                    'rz':qtrl_repr.rz,\
                    'cu3':qtrl_repr.cu3,\
                    'cu1':qtrl_repr.cu1,\
                    'crz':qtrl_repr.crz}
        return switcher[line_seg](params)
    elif line_seg[:4] == 'swap':
        return ['swap']
    else:
        print(line_seg)
        print("Error! Gate not handled")
        sys.exit()



    return line_seg

def parse_reg_and_q_name(line_seg):
    reg = ""
    q_name = ""
    on_q = True
    for ch in line:
        if on_q and ch != ' ':
            q_name += ch
        elif ch == ' ':
            on_q = False
        elif ch not in  ['-', '>', ' ', '[', ']']:
            reg += ch
    return q_name, reg

if __name__ == '__main__':
    compile_qasm(sys.argv[1])
