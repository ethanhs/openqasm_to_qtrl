import os, sys
import numpy as np
from pathlib import Path

QTRL_DIR = os.path.join(os.getcwd(), 'qtrl')
QUANTUM_SIMULATION = os.path.join(QTRL_DIR, "projects", "quantum_simulation")
TESTS_DIR = os.path.join(QTRL_DIR, "tests")
REF_CONFIG = os.path.join(QTRL_DIR, 'ref_config')
REF_OUTPUT = os.path.join(QTRL_DIR, 'ref_output')
sys.path.insert(0, QTRL_DIR)
sys.path.insert(0, QUANTUM_SIMULATION)
sys.path.insert(0, TESTS_DIR)

import utils
import pkgutil
import qtrl
import common
package = qtrl
for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
    print("Found submodule {} (is a package: {})".format(modname, ispkg))
from qtrl.sequencer import Sequence
import os
path = os.path.dirname(qtrl.__file__)
print(path)

# some units for readability
GHz = 1e9
MHz = 1e6
KHz = 1e3
ms = 1e-3
us = 1e-6
ns = 1e-9

class TestREFERENCE:
    def setup_class(cls):
        common.setup_managers('online')

        from qtrl.managers import VariableManager, MetaManager, PulseManager
        from utils.readout import add_readout

        EXAMPLE_DIR = os.path.join(TESTS_DIR, 'ref_config')
        assert os.path.exists(EXAMPLE_DIR)

        var = VariableManager(os.path.join(EXAMPLE_DIR, 'Variables.yaml'))
        cls.cfg = MetaManager({'variables': var,
            'pulses': PulseManager(os.path.join(EXAMPLE_DIR,
'Pulses.yaml'), var)
        })

        cls.cfg.add_readout = add_readout
        cls.cfg.load()

        cls.output_dir = os.path.join(rf'{os.getcwd()}', 'sequence_outputs')
        if not os.path.exists(cls.output_dir):
            os.makedirs(cls.output_dir)

    def verify_output(self, name, sequence):
        with open(os.path.join(REF_OUTPUT,'{}_output.np'.format(name)), 'rb') as f:
            ref_array = np.load(f)
            print(ref_array)
            print(ref_array.shape)
        assert np.sum(ref_array != sequence.array) == 0

    def test_arb_seq(self, file_name):

        import logging
        #caplog.set_level(logging.DEBUG, logger='qtrl')

        from qtrl.sequencer import Sequence

        qubits = [0]

        seq = Sequence(n_elements=2, name=file_name[:len(file_name)-5])
        l = [line.rstrip('\n') for line in open(file_name)]


        e_ref = 'Start'
        for line in l:
            s_ref, e_ref = seq.append([self.cfg.pulses[line]], element=0, end_delay=10*ns)

        self.cfg.add_readout(self.cfg, seq=seq, herald_refs=['Start', 'Start'], readout_refs=['Start', e_ref])
        seq.compile()
        print(seq.array.shape)
        assert seq.array.shape == (12, 2, 12110, 1)

        active_channels = 0
        for idx, val in enumerate(seq.array):
            if val.any():
                active_channels += 1

        assert active_channels == 5 #2 for qubit, 3 for readout



    def test01_rabi(self):
        """Create and verify a Rabi sequence"""

        from utils.char_sequences import rabi

        qubits = [0]

        kwargs = {'cfg': self.cfg,
                  'qubits': qubits,
                  'step_size': 20*ns,
                  'n_elements': 5
                  }

        sequence = rabi(**kwargs)
        self.verify_output('rabi', sequence)

    def test02_rough_pulse_tuning_sequence(self):
        """Create and verify a rough pulse tuning sequence"""

        from qtrl.calibration.single_pulse import rough_pulse_tuning_sequence

        qubits = [0]

        kwargs = {'config': self.cfg,
                  'qubits': qubits,
                  'pulse_type': '90',
                  'min_amplitude': 0.3,
                  'max_amplitude': 0.5,
                 }

        sequence = rough_pulse_tuning_sequence(**kwargs)
        self.verify_output('rough_pulse_tuning_sequence', sequence)

    def test03_ramsey(self):
        """Create and verify a Ramsey sequence"""

        from utils.char_sequences import ramsey

        qubits = [0]

        kwargs = {'cfg': self.cfg,
                  'qubits': qubits,
                  'n_elements': 50,
                  'step_size': 1000*ns,
                  'artificial_detune': 0.1*MHz,
                 }

        sequence = ramsey(**kwargs)
        self.verify_output('ramsey', sequence)

    def all_xy(cfg, qubit, prepulse=None):
        """AllXY sequence for the GE levels of a qubit"""
        first_pulses = ['I', 'X180', 'Z180', 'X180', 'Z180',  # end in |0> state
                        'X90', 'Z90', 'X90', 'Z90', 'X90', 'Z90',# end in |0>+|1> state
                        'X180', 'Z180', 'X90', 'X180', 'Z90', 'Z180',   # end in |0>+|1> state
                        'X180', 'Z180', 'X90', 'Z90']  # end in |1> state

        first_pulses_doubled = list(chain(*zip(first_pulses,first_pulses)))
        second_pulses = ['I', 'X180', 'Z180', 'Z180', 'X180', 'I', 'I',
                         'Z90', 'X90', 'Z180', 'X180', 'Z90',
                         'X90', 'X180', 'X90', 'Z180', 'Z90',
                         'I', 'I', 'X90', 'Z90']
        second_pulses_doubled = list(chain(*zip(second_pulses, second_pulses)))
        seq = Sequence(n_elements=len(first_pulses_doubled),x_axis = list(zip(first_pulses_doubled,second_pulses_doubled)))
        seq._name = 'allxy'
        readout_refs = []
        if prepulse is not None:
            _, og_e_ref = seq.append(prepulse)
        else:
            og_e_ref = "Start"

        for i, (p1, p2) in enumerate(zip(first_pulses_doubled, second_pulses_doubled)):
            _, e_ref = seq.append(cfg.pulses[f'Q{qubit}/{p1}'],
                                  start=og_e_ref,
                                  element=i)

            _, e_ref = seq.append(cfg.pulses[f'Q{qubit}/{p2}'],
                                  start=e_ref,
                                  element=i)
            readout_refs.append(e_ref)

        cfg.add_readout(cfg, seq, readout_refs, seq.n_elements*['Start'])
        seq._name = 'all_xy'  # this sets what subdirectory to save the data into after the acquisition
        seq.compile()

        return seq

    def test05_all_xy(self):
        """Create and verify an all xy sequence"""

        # from utils.char_sequences import all_xZ

        qubits = [0]

        kwargs = {'cfg': self.cfg,
                  'qubit': qubits[0]
                 }

        sequence = all_xy(**kwargs)
        self.verify_output('all_xy', sequence)

    
    def pi_no_pi(self, cfg, qubits, file_name):
        """Assuming X180 pulses are well tuned for the qubits specified,
        This generates a 2 element sequence, element 1 is X180 on all qubit
        element 0 is nothing on all qubits"""
        seq = Sequence(n_elements=2)

        e_ref = 'Start'

        l = [line.rstrip('\n') for line in open(file_name)]
        for qubit in qubits:
            for line in l:
                s_ref, e_ref = seq.append([cfg.pulses[line]], element=1, end_delay=10e-9)

        cfg.add_readout(cfg, seq=seq, herald_refs=['Start', 'Start'], readout_refs=['Start', e_ref])
        seq.compile()
        seq._name = 'pi_no_pi'
        return seq

    def test06_pi_no_pi(self, file_name):
        """Create and verify a pi_no_pi sequence"""

        qubits = [0]

        kwargs = {'cfg': self.cfg,
                  'qubits': qubits,
                  'file_name': file_name
                 }

        sequence = self.pi_no_pi(**kwargs)
        self.verify_output('pi_no_pi', sequence)

list_names = ['interleaved_coherence',\
              'echo',\
              't1',\
              'pi_no_pi',\
              'all_xy',\
              'ramsey',\
              'rough_pulse_tuning_sequence',\
              'rabi']

#for name in list_names:
#verify_output(list_names[3])
test_ref = TestREFERENCE()
test_ref.setup_class()
test_ref.test06_pi_no_pi(sys.argv[1])
