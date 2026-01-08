import sys
sys.dont_write_bytecode = True
import lib as lib
from multiprocessing import Process
import sys
LASTSIMULATIONPERIOD=int(sys.argv[1])




def run_proc1():
    lib.testForSim_NY17NY17_NY17NY17_NY17TK1630_A(LASTSIMULATIONPERIOD)

def run_proc2():
	lib.testForSim_NY17NY17_NY17NY17_NY17TK1630_B(LASTSIMULATIONPERIOD)

def run_proc3():
	lib.testForSim_NY17NY17_NY17NY17_NY17TK1630_C(LASTSIMULATIONPERIOD)



if __name__ == "__main__":
	p1 = Process(target=run_proc1)
	p2 = Process(target=run_proc2)
	p3 = Process(target=run_proc3)

	print('Child process will start.')
	p1.start()
	p2.start()
	p3.start()
	
	p1.join()
	p2.join()
	p3.join()
	print('Child process end.')

	lib.testForSim_NY17NY17_NY17NY17_NY17TK1630_TOTAL()
