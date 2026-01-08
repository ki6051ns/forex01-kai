import sys
sys.dont_write_bytecode = True
import lib as lib
from multiprocessing import Process
import sys
LASTSIMULATIONPERIOD=2025

def run_proc1():
    lib.train_NY17TK20_A( LASTSIMULATIONPERIOD)

def run_proc2():
	lib.train_NY17TK20_B( LASTSIMULATIONPERIOD)

def run_proc3():
	lib.train_NY17TK20_C( LASTSIMULATIONPERIOD)

def run_proc4():
	lib.train_NY17NY17_A( LASTSIMULATIONPERIOD)

def run_proc5():
	lib.train_NY17NY17_B( LASTSIMULATIONPERIOD)

def run_proc6():
	lib.train_NY17NY17_C( LASTSIMULATIONPERIOD)

if __name__ == "__main__":
	p1 = Process(target=run_proc1)
	p2 = Process(target=run_proc2)
	p3 = Process(target=run_proc3)
	p4 = Process(target=run_proc4)
	p5 = Process(target=run_proc5)
	p6 = Process(target=run_proc6)

	print('Child process will start.')
	p1.start()
	p2.start()
	p3.start()
	p4.start()
	p5.start()
	p6.start()

	p1.join()
	p2.join()
	p3.join()
	p4.join()
	p5.join()
	p6.join()
	print('Child process end.')
    

