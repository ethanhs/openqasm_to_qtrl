"""
A transpiler to serve as a bridge between qiskit and qtrl
Input format: either qiskit code or OpenQASM code (likely the latter)
Output format: qtrl list of strings formatted as follows:
    'Q0/X90'
original repo: https://github.com/qnl/openqasm_transpiler
"""
import io, os, sys
import re
from openqasm2qtrl.qtrl_repr import paramless_reprs as reps
import openqasm2qtrl.qtrl_repr as qtrl_repr

custom_gates = {}


def qasm_to_qtrl(circuit_qasm, mapping=None):
    """ TODO: This function still need some love for the CR-gate"""
    # do the first pass with the transpiler
    circuit = transpile_qasm(circuit_qasm, mapping=mapping)
    if mapping is not None:
        qubits = [f'Q{v}' for v in mapping.values()]
    else:
        print('error, no mapping not implemeted yet..')
    qtrl_circuit = [[] for _ in qubits]
    print(qtrl_circuit)
    for operation in circuit:

        if 'CR' in operation:
            # make sure the idx have all the same number of gate. Fill the gap with NUll
            n_ops = [len(qtrl_circuit[k]) for k in range(len(qubits))]
            for k, q in enumerate(qubits):
                if n_ops[k] < max(n_ops):
                    qtrl_circuit[k].extend([q + '/Null'] * (max(n_ops) - n_ops[k]))

            # then we append the CR
            for k, q in enumerate(qubits):
                if f'C{q[-1]}' in operation:
                    qtrl_circuit[k].append(operation)
                else:
                    qtrl_circuit[k].append(q + '/Null')


        # look if it's has a qubit label. This means it willl be a single qbuits gates
        for k, q in enumerate(qubits):
            if q in operation:
                qtrl_circuit[k].append(operation)

    # padding the last step to have the same number of gate in each qubits
    # make sure the idx have all the same number of gate. Fill the gap with NUll
    n_ops = [len(qtrl_circuit[k]) for k in range(len(qubits))]
    for k, q in enumerate(qubits):
        if n_ops[k] < max(n_ops):
            qtrl_circuit[k].extend([q + '/Null'] * (max(n_ops) - n_ops[k]))

    return list(map(list, zip(*qtrl_circuit)))


def transpile_qasm(input, outf='default', verbose=False, mapping=None):
    """ Translate a Qiskit or openQASM circuit into a qtrl circuit.

    Args:
        input:
        outf:
        verbose:
        mapping (dict): mapping of the qregister to qtrl qubits
    """

    if os.path.exists(input):
        file_name = input
        l = [line.rstrip('\n') for line in open(input)][2:]
    else:
        file_name = "dummy"
        l = [line.rstrip('\n') for line in io.StringIO(input)][2:]
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
            # qregister line format are ike "qreg q[1]" The number of qubits
            # register is given in the bracket. Sometime, the qubit name is
            # not a single character. Added a regex search. The regex will
            # search for a digit inside bracker []
            # Add string of qubit name to list of qubits we may draw from?

            # How many qubits are we considering
            n_qubits = int(re.search(r"\[([0-9]+)\]", line).group(1))

            # Constructing the dictionnary of qubits names
            if (mapping is None):
                mapping = {i: i for i in range(n_qubits)}

            for i in range(n_qubits):
                q_name = "Q" + str(mapping[i])
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
            output.append('New Cycle')
            pass

        elif line == '':
            pass

        else:
            # It's a gate operation!
            q_name, gates = parse_gate_and_q(line[:- 1], mapping)

            for gate in gates:
                # first check if it's an entanglement gate
                if len(q_name) == 2:

                    if gate == 'CNOT':
                        output.append(f'CR/C{q_name[0][1]}T{q_name[1][1]}')

                    # TODO: in our configuration, we cannot make CNOT in both direction...
                    # We need to add some local gate to make this happen
                    elif gate == 'swap':
                        output.extend( \
                            ['{},{}/CNOT'.format(q_name[0].upper(), q_name[1].upper()), \
                             '{},{}/CNOT'.format(q_name[1].upper(), q_name[0].upper())])
                    else:
                        output.append(q_name[1].upper() + '/' + gate)
                else:
                    output.append(q_name[0].upper() + '/' + gate)
        # print(output)
    if verbose:
        print("---------------")
        print(output)
    if outf:
        fname = (outf == 'default') and file_name[:len(file_name) - 5] or outf
        with open('{}_qtrl.txt'.format(fname), 'w') as f:
            for item in output:
                f.write("%s\n" % item)
        if verbose:
            print("Output saved!")
    return output


def parse_q_name(s, mapping):
    """ Parse the name of the qubit. Assuming here that the qubit is named following
    the convention Q8 for register_name[8]"""
    # this look for a *[digit]* pattern and return the digit
    qregister_list = s.split(",")
    qiskit_qubits = [int(qr[qr.find("[") + 1:qr.find("]")]) for qr in qregister_list]
    return ["Q" + str(mapping[q]) for q in qiskit_qubits]


def parse_gate(s):
    """ Parse the gate name and parameter"""
    if "(" in s:
        gate = s[:s.find("(")]
        params = (s[s.find("(") + 1:s.find(")")]).split(',')
    else:
        gate = s
        params = []
    return gate, params


def parse_gate_and_q(line, mapping):
    # parse parameters in here?
    # Generic gate are defined as:
    #   gate_name(param!, param2, ...) qubit_register[qubit_integer]

    # # first, split the sequence with the space
    gate_string, qregister = line.split()

    # # parse the qregister name
    q_names = parse_q_name(qregister, mapping)

    # # parse the gate and its parameter
    gate, params = parse_gate(gate_string)
    gate = determine_gate(q_names, gate, params)

    return q_names, gate


# TODO: finish this!
def parse_custom_gate(line_seg):
    comb = []
    for gate in custom_gates[line_seg]:
        comb.append(determine_gate(gate))
    return comb


# Compute angles of gate operations here
# use combination of Rz * Rx(90) * Rz * Rx(90) * Rz to represent:
def determine_gate(q_name, line_seg, params=None):
    if line_seg in reps.keys():
        return reps[line_seg]
    elif line_seg[:10] in list(custom_gates.keys()):
        if params is not None:
            return custom_gates[line_seg](params)
        else:
            return custom_gates[line_seg]
    elif params != []:
        switcher = {'u3': qtrl_repr.u3, \
                    'u2': qtrl_repr.u2, \
                    'u1': qtrl_repr.u1, \
                    'rx': qtrl_repr.rx, \
                    'ry': qtrl_repr.ry, \
                    'rz': qtrl_repr.rz, \
                    'cu3': qtrl_repr.cu3, \
                    'cu1': qtrl_repr.cu1, \
                    'crz': qtrl_repr.crz}
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
        elif ch not in ['-', '>', ' ', '[', ']']:
            reg += ch
    return q_name, reg


if __name__ == '__main__':
    transpile_qasm(sys.argv[1])
