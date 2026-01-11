import sys
sys.dont_write_bytecode = True
import lib as lib
from multiprocessing import Process
import sys
import datetime 
import pandas as pd 
from dateutil.relativedelta import relativedelta
import os

TUESDAY  = 1 
if os.path.exists(lib.DIRECTORY+"test/output/prod/.gitignore"):
    os.remove(lib.DIRECTORY+"test/output/prod/.gitignore")

# Spot suffix切替（段階1：testだけ新データ）
spot_suffix = os.getenv("SPOT_SUFFIX", "")
lib.init_spot_globals(spot_suffix)
print(f"[RUN] SPOT_SUFFIX={spot_suffix!r}")

date_  =  pd.to_datetime(sys.argv[1])
date_  =  date_ + relativedelta(hours=16, minutes=30)
LASTSIMULATIONPERIOD = date_.year





if  date_.weekday() == TUESDAY  :

	def run_proc1():
		lib.testForProd_NY17NY17_NY17NY17_NY17TK1630_A(LASTSIMULATIONPERIOD,date_)

	def run_proc2():
		lib.testForProd_NY17NY17_NY17NY17_NY17TK1630_B(LASTSIMULATIONPERIOD,date_)

	def run_proc3():
		lib.testForProd_NY17NY17_NY17NY17_NY17TK1630_C(LASTSIMULATIONPERIOD,date_)

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

		lib.testForProd_NY17NY17_NY17NY17_NY17TK1630_TOTAL(date_)
