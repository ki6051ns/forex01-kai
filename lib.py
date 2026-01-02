########################################################################################3
# libraries
########################################################################################3
from audioop import add
from genericpath import exists
from re import A
from turtle import pos, position
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import numpy as np
import itertools
from IPython.display import clear_output
import datetime
import threading
import os
#import mysql.connector
import warnings
warnings.simplefilter('ignore')

import inspect
stack = inspect.stack()
for s in stack[1:]:
    m = inspect.getmodule(s[0])
    if m:
        PYTHONFILENAME =  m.__file__
        break

DIRECTORY = PYTHONFILENAME.replace("\\","/")
PYTHONFILENAME  = PYTHONFILENAME.split("\\")
PYTHONFILENAME= PYTHONFILENAME[len(PYTHONFILENAME)-1]
if PYTHONFILENAME == "train.py":
    INPUTPATH = "train/input/"
elif ( PYTHONFILENAME == "test_sim.py" ) | ( PYTHONFILENAME == "test_prod.py" ) :
    INPUTPATH = "test/input/"
else:
    # デフォルト値（スクリプトから直接インポートされた場合など）
    INPUTPATH = "train/input/"

DIRECTORY = DIRECTORY.replace(PYTHONFILENAME,"")
INPUTPATH= DIRECTORY+INPUTPATH


########################################################################################3
# static values
########################################################################################3

# 高速化フラグ（True: 高速版使用, False: 既存版使用）
USE_FAST = True

CURRENCY_A = ['AUDUSD','CADUSD','CHFUSD','EURUSD','GBPUSD','NZDUSD']
CURRENCY_B = ['AUDUSD','CADUSD','CHFUSD','EURUSD','GBPUSD','NZDUSD','JPYUSD']
CURRENCY_C = ['AUDUSD','CADUSD','CHFUSD','EURUSD','GBPUSD','NZDUSD']

COST = {'AUDUSD':2.0E-4, 'CADUSD':2.0E-4, 'CHFUSD':2.0E-4, 'EURUSD':2.0E-4, 'GBPUSD':2.0E-4, 'NZDUSD':2.0E-4 , 'JPYUSD':2.0E-4 }

REF_PERIOD_WIDTH = [12,25,50,100,150] #p2
TRADE_PERIOD_WIDTH = [5,12,25,50] #p1
NUMBER_OF_PARAMETERS = [1,3,5,10] # p4
NUMBER_OF_HYPERPARAMETER = 4
THRESHOLD = 0.0008  #LB

TRAIN_PERIOD_TO_A = range(2005,2024)
TRAIN_PERIOD_TO_B = range(2006,2024)
TRAIN_PERIOD_TO_C = range(2005,2024)

TRAIN_PERIOD_TO_A_TK1630 = range(2010,2024)
TRAIN_PERIOD_TO_B_TK1630 = range(2010,2024)
TRAIN_PERIOD_TO_C_TK1630 = range(2010,2024)


FACTOR_CALCULATION_PERIOD_A = range(20,31,1 )
FACTOR_CALCULATION_PERIOD_B = range(100,155,5 )
FACTOR_CALCULATION_PERIOD_C = range(1,13,1 )

LAG_RANGE = range(1,6)


########################################################################################3
# market info functions & Load DataSet
########################################################################################3

def loadSQL(date, tenor,pricing_source ):
    """
    MySQLデータベースから為替レートを読み込む関数
    
    ⚠️ セキュリティ警告: 認証情報は環境変数から取得してください
    現在は未使用のため、空のDataFrameを返します。
    
    環境変数（将来使用する場合）:
        MYSQL_HOST: データベースホスト
        MYSQL_PORT: ポート番号（デフォルト: 3306）
        MYSQL_USER: ユーザー名
        MYSQL_PASSWORD: パスワード
        MYSQL_DATABASE: データベース名
    
    使用例（環境変数を使用）:
        import os
        import mysql.connector
        
        host = os.getenv("MYSQL_HOST")
        port = int(os.getenv("MYSQL_PORT", "3306"))
        user = os.getenv("MYSQL_USER")
        password = os.getenv("MYSQL_PASSWORD")
        database = os.getenv("MYSQL_DATABASE")
        
        mydb = mysql.connector.connect(host=host, port=port, user=user, password=password, database=database)
    """
    # 現在は未使用のため、空のDataFrameを返す
    # 認証情報のハードコードを避けるため、実装はコメントアウト
    return pd.DataFrame()

def imputation(fwdRate_,spotRate_):
    for currency_ in fwdRate_.columns.drop("date_time"):
        index_ = fwdRate_.index[fwdRate_[currency_].isna()]
        for i_ in index_ :
            datePre_ = fwdRate_["date_time"][i_-1]
            date_ = fwdRate_["date_time"][i_]
            spotRatePre_ = spotRate_[currency_][spotRate_["date_time"] == datePre_ ].iloc[-1]
            fwdRatePre_ =  fwdRate_[currency_][fwdRate_["date_time"] == datePre_ ].iloc[-1]
            ratio_ =  fwdRatePre_/spotRatePre_
            spotRatePost_ = spotRate_[currency_][spotRate_["date_time"] == date_ ].iloc[-1]
            fwdRate_[currency_][i_] = ratio_ * spotRatePost_

    return fwdRate_


def loadData(inputFile_):
    
    ret_ = pd.read_csv( INPUTPATH  + inputFile_).dropna()
    ret_["date_time"] = pd.to_datetime(ret_["date_time"])
    return ret_

def loadForwardRate1w_NY17( ):
    return loadData(inputFile_ = "market/forward_rates_1w_ny17.csv")

def loadForwardRate1w_TK20( ):
    return loadData(inputFile_ = "market/forward_rates_1w_tk20.csv")

def loadForwardRate1w_TK1630( ):
    return loadData(inputFile_ = "market/forward_rates_1w_tk1630.csv")

def loadSpotRate_NY17( ):
    return loadData(inputFile_ = "market/spot_rates_ny17.csv")

def loadSpotRate_TK20( ):
    return loadData(inputFile_ = "market/spot_rates_tk20.csv")

def loadSpotRate_TK1630( ):
    return loadData(inputFile_ = "market/spot_rates_tk1630.csv")

########################################################################################3
# MARKET UPDATE
########################################################################################3
# FWDRATE_NY17 = loadForwardRate1w_NY17()
# SPOTRATE_NY17 = loadSpotRate_NY17( )
# addon_1w_ny17 = loadSQL(FWDRATE_NY17["date_time"].max(), "1W","CMPN")
# if len(addon_1w_ny17) >0 :
#     addon_spot_ny17 = loadSQL(SPOTRATE_NY17["date_time"].max(), "Spot","CMPN")
#     addon_1w_ny17 = imputation(addon_1w_ny17,addon_spot_ny17)
#     addon_1w_ny17["date_time"] = addon_1w_ny17["date_time"].map( lambda x : x  + relativedelta( hours= 17 )  )
#     addon_spot_ny17["date_time"] = addon_spot_ny17["date_time"].map( lambda x : x  + relativedelta( hours= 17 )  )

#     FWDRATE_NY17 = FWDRATE_NY17.append(addon_1w_ny17)
#     SPOTRATE_NY17 = SPOTRATE_NY17.append(addon_spot_ny17) 
#     FWDRATE_NY17.to_csv( INPUTPATH  +"market/forward_rates_1w_ny17.csv",index=False)
#     SPOTRATE_NY17.to_csv( INPUTPATH  +"market/spot_rates_ny17.csv",index=False)



# FWDRATE_TK20 = loadForwardRate1w_TK20()
# SPOTRATE_TK20 = loadSpotRate_TK20( )
# addon_1w_tk20 = loadSQL(FWDRATE_TK20["date_time"].max(), "1W","BGNT")
# if len(addon_1w_tk20) >0 :
#     addon_spot_tk20 = loadSQL(SPOTRATE_TK20["date_time"].max(), "Spot","BGNT")
#     addon_1w_tk20 = imputation(addon_1w_tk20,addon_spot_tk20)
#     addon_1w_tk20["date_time"] = addon_1w_tk20["date_time"].map( lambda x : x  + relativedelta( hours= 20 )  )
#     addon_spot_tk20["date_time"] = addon_spot_tk20["date_time"].map( lambda x : x  + relativedelta( hours= 20 )  )

#     FWDRATE_TK20 = FWDRATE_TK20.append(addon_1w_tk20)
#     SPOTRATE_TK20 = SPOTRATE_TK20.append(addon_spot_tk20)
#     FWDRATE_TK20.to_csv( INPUTPATH  +"market/forward_rates_1w_tk20.csv",index=False)
#     SPOTRATE_TK20.to_csv( INPUTPATH  +"market/spot_rates_tk20.csv",index=False)




# FWDRATE_TK1630 = loadForwardRate1w_TK1630()
# SPOTRATE_TK1630 = loadSpotRate_TK1630( )
# addon_1w_tk1630 = loadSQL(FWDRATE_TK1630["date_time"].max(), "1W","T163")
# if len(addon_1w_tk1630) >0:
#     addon_spot_tk1630 = loadSQL(SPOTRATE_TK1630["date_time"].max(), "Spot","T163")
#     addon_1w_tk1630 = imputation(addon_1w_tk1630,addon_spot_tk1630)
#     addon_1w_tk1630["date_time"] = addon_1w_tk1630["date_time"].map( lambda x : x  + relativedelta( hours= 16)+  relativedelta(minutes= 30 )   )
#     addon_spot_tk1630["date_time"] = addon_spot_tk1630["date_time"].map( lambda x : x  + relativedelta( hours= 16)+  relativedelta(minutes= 30 )   )

#     FWDRATE_TK1630 = FWDRATE_TK1630.append(addon_1w_tk1630)
#     SPOTRATE_TK1630 = SPOTRATE_TK1630.append(addon_spot_tk1630)
#     FWDRATE_TK1630.to_csv( INPUTPATH  +"market/forward_rates_1w_tk1630.csv",index=False)
#     SPOTRATE_TK1630.to_csv( INPUTPATH  +"market/spot_rates_tk1630.csv",index=False)



########################################################################################3
# Load DataSet
########################################################################################3

FWDRATE_NY17 = loadForwardRate1w_NY17()
FWDRATE_NY17 = FWDRATE_NY17.rename(columns = {'date_time':'start_time'} )
FWDRATE_NY17 = FWDRATE_NY17[ (FWDRATE_NY17['start_time'].dt.hour == 17) & (FWDRATE_NY17['start_time'].dt.weekday == 0 )  ].reset_index(drop= True)
FWDRATE_A_NY17 = FWDRATE_NY17[["start_time"]+ CURRENCY_A ]
FWDRATE_B_NY17 = FWDRATE_NY17[["start_time"]+ CURRENCY_B ]
FWDRATE_C_NY17 = FWDRATE_NY17[["start_time"]+ CURRENCY_C ]

FWDRATE_NY17TK20 = FWDRATE_NY17.copy()
FWDRATE_NY17TK20["start_time"] = FWDRATE_NY17TK20["start_time"].map( lambda x : x + relativedelta(days = 1 ) + relativedelta( hours= 3 )  )
FWDRATE_A_NY17TK20 = FWDRATE_NY17TK20[["start_time"]+ CURRENCY_A ]
FWDRATE_B_NY17TK20 = FWDRATE_NY17TK20[["start_time"]+ CURRENCY_B ]
FWDRATE_C_NY17TK20 = FWDRATE_NY17TK20[["start_time"]+ CURRENCY_C ]

FWDRATE_NY17TK1630 = FWDRATE_NY17.copy()
FWDRATE_NY17TK1630["start_time"] = FWDRATE_NY17TK1630["start_time"].map( lambda x : x + relativedelta(days = 1 ) - relativedelta( minutes= 30 )  )
FWDRATE_A_NY17TK1630 = FWDRATE_NY17TK1630[["start_time"]+ CURRENCY_A ]
FWDRATE_B_NY17TK1630 = FWDRATE_NY17TK1630[["start_time"]+ CURRENCY_B ]
FWDRATE_C_NY17TK1630 = FWDRATE_NY17TK1630[["start_time"]+ CURRENCY_C ]

FWDRATE_TK20 = loadForwardRate1w_TK20()
FWDRATE_TK20 = FWDRATE_TK20.rename(columns = {'date_time':'start_time'} )
FWDRATE_TK20 = FWDRATE_TK20[ (FWDRATE_TK20['start_time'].dt.hour == 20) & (FWDRATE_TK20['start_time'].dt.weekday == 1 )  ].reset_index(drop= True)
FWDRATE_A_TK20 = FWDRATE_TK20[["start_time"]+ CURRENCY_A ]
FWDRATE_B_TK20 = FWDRATE_TK20[["start_time"]+ CURRENCY_B ]
FWDRATE_C_TK20 = FWDRATE_TK20[["start_time"]+ CURRENCY_C ]

FWDRATE_TK1630 = loadForwardRate1w_TK1630()
FWDRATE_TK1630 = FWDRATE_TK1630.rename(columns = {'date_time':'start_time'} )
FWDRATE_TK1630 = FWDRATE_TK1630[ (FWDRATE_TK1630['start_time'].dt.hour == 16) & (FWDRATE_TK1630['start_time'].dt.minute == 30 ) &(FWDRATE_TK1630['start_time'].dt.weekday == 1 )  ].reset_index(drop= True)
FWDRATE_A_TK1630 = FWDRATE_TK1630[["start_time"]+ CURRENCY_A ]
FWDRATE_B_TK1630 = FWDRATE_TK1630[["start_time"]+ CURRENCY_B ]
FWDRATE_C_TK1630 = FWDRATE_TK1630[["start_time"]+ CURRENCY_C ]




SPOTRATE_NY17 = loadSpotRate_NY17( )
SPOTRATE_NY17 = SPOTRATE_NY17.rename(columns = {'date_time':'start_time'} )
SPOTRATE_NY17 = SPOTRATE_NY17[ (SPOTRATE_NY17['start_time'].dt.hour == 17) & (SPOTRATE_NY17['start_time'].dt.weekday == 0 )  ].reset_index(drop= True)
SPOTRATE_A_NY17 = SPOTRATE_NY17[["start_time"]+ CURRENCY_A ]
SPOTRATE_B_NY17 = SPOTRATE_NY17[["start_time"]+ CURRENCY_B ]
SPOTRATE_C_NY17 = SPOTRATE_NY17[["start_time"]+ CURRENCY_C ]

SPOTRATE_NY17TK20 = SPOTRATE_NY17.copy()
SPOTRATE_NY17TK20["start_time"] = SPOTRATE_NY17TK20["start_time"].map( lambda x : x + relativedelta(days = 1 ) + relativedelta( hours= 3 )  )
SPOTRATE_A_NY17TK20 = SPOTRATE_NY17TK20[["start_time"]+ CURRENCY_A ]
SPOTRATE_B_NY17TK20 = SPOTRATE_NY17TK20[["start_time"]+ CURRENCY_B ]
SPOTRATE_C_NY17TK20 = SPOTRATE_NY17TK20[["start_time"]+ CURRENCY_C ]

SPOTRATE_NY17TK1630 = SPOTRATE_NY17.copy()
SPOTRATE_NY17TK1630["start_time"] = SPOTRATE_NY17TK1630["start_time"].map( lambda x : x + relativedelta(days = 1 ) - relativedelta( minutes= 30 )  )
SPOTRATE_A_NY17TK1630 = SPOTRATE_NY17TK1630[["start_time"]+ CURRENCY_A ]
SPOTRATE_B_NY17TK1630 = SPOTRATE_NY17TK1630[["start_time"]+ CURRENCY_B ]
SPOTRATE_C_NY17TK1630 = SPOTRATE_NY17TK1630[["start_time"]+ CURRENCY_C ]

SPOTRATE_TK20 = loadSpotRate_TK20( )
SPOTRATE_TK20 = SPOTRATE_TK20.rename(columns = {'date_time':'start_time'} )
SPOTRATE_TK20 = SPOTRATE_TK20[ (SPOTRATE_TK20['start_time'].dt.hour == 20) & (SPOTRATE_TK20['start_time'].dt.weekday == 1 )  ].reset_index(drop= True)
SPOTRATE_A_TK20 = SPOTRATE_TK20[["start_time"]+ CURRENCY_A ]
SPOTRATE_B_TK20 = SPOTRATE_TK20[["start_time"]+ CURRENCY_B ]
SPOTRATE_C_TK20 = SPOTRATE_TK20[["start_time"]+ CURRENCY_C ]

SPOTRATE_TK1630 = loadSpotRate_TK1630( )
SPOTRATE_TK1630 = SPOTRATE_TK1630.rename(columns = {'date_time':'start_time'} )
SPOTRATE_TK1630 = SPOTRATE_TK1630[ (SPOTRATE_TK1630['start_time'].dt.hour == 16) & (SPOTRATE_TK1630['start_time'].dt.minute == 30 ) &(SPOTRATE_TK1630['start_time'].dt.weekday == 1 )  ].reset_index(drop= True)
SPOTRATE_A_TK1630 = SPOTRATE_TK1630[["start_time"]+ CURRENCY_A ]
SPOTRATE_B_TK1630 = SPOTRATE_TK1630[["start_time"]+ CURRENCY_B ]
SPOTRATE_C_TK1630 = SPOTRATE_TK1630[["start_time"]+ CURRENCY_C ]




def getEndTime(calculateFactorReturn):
    endTime_ = calculateFactorReturn(pd.DataFrame(), 0)[["start_time"]]
    endTime_["end_time"] = endTime_["start_time"].map( lambda x : x + relativedelta( weeks= 1 ) )
    return endTime_.dropna()

########################################################################################3
# position functions
# 検証完了 @ 2021-11-24
# コード書き換え&検証完了 @ 2021-12-03
########################################################################################3

def definitionA(name_, position1_, position2_, position3_, position4_, position5_, position6_):
    def name_(vec_ ):
        position_ = np.array(vec_, dtype='float32')
        np.place(position_, position_ == 1, position1_ )
        np.place(position_, position_ == 2, position2_ )
        np.place(position_, position_ == 3, position3_ )
        np.place(position_, position_ == 4, position4_ )
        np.place(position_, position_ == 5, position5_ )
        np.place(position_, position_ == 6, position6_ )
        return position_
    return name_

POSITION_A = pd.read_csv(INPUTPATH + "position/position_functions_6.csv")
POSITION_FUNCTIONS_A = {}

for row_ in range( len(POSITION_A)):
    POSITION_FUNCTIONS_A[row_] = definitionA(POSITION_A['id'][row_],
                                           POSITION_A['position_1'][row_],POSITION_A['position_2'][row_],POSITION_A['position_3'][row_],
                                           POSITION_A['position_4'][row_],POSITION_A['position_5'][row_],POSITION_A['position_6'][row_])
    

def definitionB(name_, position1_, position2_, position3_, position4_, position5_, position6_, position7_):
    def name_(vec_ ):
        position_ = np.array(vec_, dtype='float32')
        np.place(position_, position_ == 1, position1_ )
        np.place(position_, position_ == 2, position2_ )
        np.place(position_, position_ == 3, position3_ )
        np.place(position_, position_ == 4, position4_ )
        np.place(position_, position_ == 5, position5_ )
        np.place(position_, position_ == 6, position6_ )
        np.place(position_, position_ == 7, position7_ )
        return position_
    return name_

POSITION_B = pd.read_csv(INPUTPATH + "position/position_functions_7.csv")
POSITION_FUNCTIONS_B = {}

for row_ in range( len(POSITION_B)):
    POSITION_FUNCTIONS_B[row_] = definitionB(POSITION_B['id'][row_],
                                           POSITION_B['position_1'][row_],POSITION_B['position_2'][row_],POSITION_B['position_3'][row_],
                                           POSITION_B['position_4'][row_],POSITION_B['position_5'][row_],POSITION_B['position_6'][row_],POSITION_B['position_7'][row_])    
    
POSITION_C = POSITION_A
POSITION_FUNCTIONS_C = POSITION_FUNCTIONS_A


def performanceSummary(df_, column_ ) :
    def mdd(vec_):
        vec_ = list( vec_[ vec_.columns[1] ]) 
        if len(vec_) <= 1 :
            return 0 
        else: 
            dd_ = []
            for i_ in range(len(vec_)-1 ):
                dd_.append( min( vec_[i_+1 :] ) - vec_[i_]  ) 
            return min(dd_)
    
    def mdd2(vec_):
        vec_ = list( vec_[ vec_.columns[0] ]) 
        if len(vec_) <= 1 :
            return 0 
        else: 
            dd_ = []
            for i_ in range(len(vec_)-1 ):
                dd_.append( min( vec_[i_+1 :] ) - vec_[i_]  ) 
            return min(dd_)
    
    total_ = pd.DataFrame()
    df_ = df_.reset_index(drop=False)
    tmp_ = pd.DataFrame({"start_time": df_["start_time"],  "pl": df_[column_]}  ).dropna()
    tmp_["year"] = tmp_["start_time"].dt.year
    smry_ = tmp_.groupby("year").agg(["sum", "mean","std" ]  )[["pl"]]
    smry_.columns = smry_.columns.droplevel(0)
    if smry_.isna().any()["std"]:
        smry_["sr"] = -float('inf') 
    else: 
        smry_["sr"] = smry_["mean"] / smry_["std"] * np.sqrt(50)
    total_["year"] = ["total"]
    total_["sum"] = [tmp_["pl"].sum()]
    total_["mean"] = [tmp_["pl"].mean()]
    total_["std"] = [tmp_["pl"].std()]
    if total_.isna().any()["std"]:
        total_["sr"] = -float('inf') 
    else: 
        sr_ = total_["mean"] / total_["std"] * np.sqrt(50)
        total_["sr"] = [ sr_[0]]
    tmp_["pl"] = tmp_["pl"].cumsum()
    smry2_ = pd.DataFrame(tmp_[["year","pl"]] .groupby("year").apply(mdd) )
    smry_ = smry_.join(smry2_)
    smry_ = smry_.rename( columns = {0 : "mdd" })
    smry_["sortino"] = smry_["sum"] / np.abs( smry_["mdd"]) 
    total_["mdd"] =  [mdd2(tmp_[["pl"]])]
    sortino_ = total_["sum"] / np.abs(total_["mdd"])
    total_["sortino"] = [sortino_[0] ]
    

    smry_ = pd.concat([smry_.reset_index(), total_])
    smry_ = smry_.set_index("year")
    return smry_

def performanceSummary2(df_, column_ ) :
    def mdd(vec_):
        vec_ = list( vec_[ vec_.columns[1] ]) 
        if len(vec_) <= 1 :
            return 0 
        else: 
            dd_ = []
            for i_ in range(len(vec_)-1 ):
                dd_.append( min( vec_[i_+1 :] ) - vec_[i_]  ) 
            return min(dd_)
    
    def mdd2(vec_):
        vec_ = list( vec_[ vec_.columns[0] ]) 
        if len(vec_) <= 1 :
            return 0 
        else: 
            dd_ = []
            for i_ in range(len(vec_)-1 ):
                dd_.append( min( vec_[i_+1 :] ) - vec_[i_]  ) 
            return min(dd_)
    
    total_ = pd.DataFrame()
    df_ = df_.reset_index(drop=False)
    df_[column_] = df_[column_]* (df_[column_]+1).shift(1).fillna(1).cumprod()
    tmp_ = pd.DataFrame({"start_time": df_["start_time"],  "pl": df_[column_]}  ).dropna()
    tmp_["year"] = tmp_["start_time"].dt.year
    smry_ = tmp_.groupby("year").agg(["sum", "mean","std" ]  )[["pl"]]
    smry_.columns = smry_.columns.droplevel(0)
    if smry_.isna().any()["std"]:
        smry_["sr"] = -float('inf') 
    else: 
        smry_["sr"] = smry_["mean"] / smry_["std"] * np.sqrt(50)
    total_["year"] = ["total"]
    total_["sum"] = [tmp_["pl"].sum()]
    total_["mean"] = [tmp_["pl"].mean()]
    total_["std"] = [tmp_["pl"].std()]
    if total_.isna().any()["std"]:
        total_["sr"] = -float('inf') 
    else: 
        sr_ = total_["mean"] / total_["std"] * np.sqrt(50)
        total_["sr"] = [ sr_[0]]
    tmp_["pl"] = tmp_["pl"].cumsum()
    smry2_ = pd.DataFrame(tmp_[["year","pl"]] .groupby("year").apply(mdd) )
    smry_ = smry_.join(smry2_)
    smry_ = smry_.rename( columns = {0 : "mdd" })
    smry_["sortino"] = smry_["sum"] / np.abs( smry_["mdd"]) 
    total_["mdd"] =  [mdd2(tmp_[["pl"]])]
    sortino_ = total_["sum"] / np.abs(total_["mdd"])
    total_["sortino"] = [sortino_[0] ]
    
    
    smry_ = pd.concat([smry_.reset_index(), total_])
    smry_ = smry_.set_index("year")
    return smry_


########################################################################################3
# simulation functionsonRate_
########################################################################################3    

def makeFactorReturn(factorReturns_,ranking_, cprd_,  fwdRate_,spotRate_ ):
    """既存版（互換性維持）"""
    ccyList_ = list(fwdRate_.columns)
    ccyList_.remove("start_time")
        
    ranking_2_tmp = pd.merge(ranking_, fwdRate_[["start_time"]], on ="start_time" , how = "inner")
    ranking_2     = pd.merge(ranking_2_tmp, spotRate_[["start_time"]], on ="start_time" , how = "inner")
    ranking_= pd.merge(ranking_ , ranking_2["start_time"],on ="start_time",how="inner" ).set_index("start_time")
    ranking_3_mine = ranking_2.copy()
    ranking_3_mine["end_time"] = ranking_3_mine["start_time"].shift(-1)
    #>> mutate( end_time  = lead(X.start_time, i=1))
    ranking_4_mine = ranking_3_mine.dropna().reset_index(drop=True)
    merged_2_mine  = pd.merge(ranking_4_mine, fwdRate_, on ="start_time" , how = "left", suffixes=['', '_fwd'])
    merged_3_mine = pd.merge(merged_2_mine, spotRate_.rename(columns = {'start_time':'end_time'} ), on ="end_time" , how = "left", suffixes=['', '_spot'])
    merged_3 = merged_3_mine
    for ccy_ in ccyList_:
        merged_3[ccy_+"ror"] = merged_3[ccy_+"_spot"] / merged_3[ccy_+"_fwd"] -1
    
    
    costRow_ = (pd.DataFrame.from_dict(COST, orient='index').T/2)
    cost_ = pd.DataFrame()
    for i in range(len(ranking_)):
        cost_ = pd.concat([cost_, costRow_])
    weightDiff_ = pd.concat([ranking_[:1], ranking_.diff()[1:]])
    cost_["start_time"] = weightDiff_.index
    cost_ = cost_.set_index("start_time")[ccyList_]
    costTable_ = abs(weightDiff_ * cost_).reset_index()

    merged_ = pd.merge(merged_3, costTable_ , on ="start_time", how ="inner" ,  suffixes=['_position', '_cost'] )

    pl_ = 0
    for ccy_ in ccyList_:
        pl_ = pl_ + merged_[ccy_+"ror" ] * merged_[ccy_ + "_position" ]  - merged_[ccy_ + "_cost" ]
    
    if len(factorReturns_) == 0:
        factorReturns_ = pd.DataFrame( { "start_time": merged_["start_time"],"end_time": merged_["end_time"], str(cprd_) :pl_ }  )
    else:
        factorReturns_ = pd.merge(factorReturns_, pd.DataFrame( { "start_time": merged_["start_time"],str(cprd_) :pl_ }  ), on ="start_time", how ="inner"  )
    return factorReturns_


def makeFactorReturn_fast(factorReturns_, ranking_, cprd_, fwdRate_, spotRate_, swap_df=None):
    """
    高速化版: pd.merge削減、ベクトル化、NumPy行列演算
    
    Args:
        factorReturns_: 既存のファクターリターンDataFrame（空でも可）
        ranking_: ランキングDataFrame（start_timeをindexに持つ）
        cprd_: 計算期間
        fwdRate_: フォワードレートDataFrame（start_time列を含む）
        spotRate_: スポットレートDataFrame（start_time列を含む）
        swap_df: スワップ損益DataFrame（Optional、後付け設計）
    
    Returns:
        factorReturns_: 更新されたファクターリターンDataFrame
    """
    # デバッグ: 高速化版が呼ばれていることを確認（最初の1回のみ）
    if not hasattr(makeFactorReturn_fast, '_debug_logged'):
        import sys
        if PYTHONFILENAME == "train.py":
            print(f"[DEBUG] makeFactorReturn_fast が呼ばれました (USE_FAST={USE_FAST})", file=sys.stderr)
        makeFactorReturn_fast._debug_logged = True
    
    ccyList_ = list(fwdRate_.columns)
    ccyList_.remove("start_time")
    
    # 1. インデックスをstart_timeに統一（reindex使用）
    # ranking_は既にset_index("start_time")されている前提
    ranking_idx = ranking_.index
    
    # fwdRate_とspotRate_をインデックス化
    fwdRate_idx = fwdRate_.set_index("start_time")
    spotRate_idx = spotRate_.set_index("start_time")
    
    # 共通インデックスを取得（inner join相当）
    common_idx = ranking_idx.intersection(fwdRate_idx.index).intersection(spotRate_idx.index)
    if len(common_idx) == 0:
        return factorReturns_
    
    # 2. データをインデックスで再配置（mergeの代わり）
    ranking_aligned = ranking_.reindex(common_idx)
    fwdRate_aligned = fwdRate_idx.reindex(common_idx)[ccyList_]
    spotRate_aligned = spotRate_idx.reindex(common_idx)[ccyList_]
    
    # 3. end_timeを計算（shift(-1)）
    end_time_series = pd.Series(common_idx, index=common_idx).shift(-1)
    valid_mask = ~end_time_series.isna()
    
    # 有効な行のみ抽出
    valid_idx = common_idx[valid_mask]
    ranking_valid = ranking_aligned.loc[valid_idx]
    fwdRate_valid = fwdRate_aligned.loc[valid_idx]
    end_time_valid = end_time_series.loc[valid_idx].values
    
    # 4. end_timeに対応するspotRateを取得（reindex使用）
    spotRate_end = spotRate_idx.reindex(end_time_valid)[ccyList_]
    
    # 5. リターン計算（NumPy行列演算で一括処理）
    # ror = spot / fwd - 1
    fwdRate_array = fwdRate_valid.values.astype(np.float64)
    spotRate_array = spotRate_end.values.astype(np.float64)
    ror_array = np.divide(spotRate_array, fwdRate_array, out=np.zeros_like(spotRate_array), where=fwdRate_array!=0) - 1.0
    
    # 6. コスト計算（ベクトル化）
    # costRow = COST / 2
    cost_row = np.array([COST.get(ccy, 2.0E-4) / 2.0 for ccy in ccyList_], dtype=np.float64)
    
    # weightDiff = diff(ranking)（最初の行はrankingそのまま）
    ranking_array = ranking_valid.values.astype(np.float64)
    weight_diff = np.zeros_like(ranking_array)
    weight_diff[0] = ranking_array[0]
    if len(ranking_array) > 1:
        weight_diff[1:] = np.diff(ranking_array, axis=0)
    
    # costTable = abs(weightDiff * cost_row)
    cost_table = np.abs(weight_diff * cost_row[np.newaxis, :])
    
    # 7. PL計算（NumPy行列演算で一括処理）
    # pl = sum(ror * position - cost) for each currency
    position_array = ranking_array  # rankingがposition
    pl_array = np.sum(ror_array * position_array - cost_table, axis=1)
    
    # 8. スワップ損益を追加（後付け設計）
    if swap_df is not None:
        swap_idx = swap_df.set_index("start_time") if "start_time" in swap_df.columns else swap_df
        swap_aligned = swap_idx.reindex(valid_idx)[ccyList_]
        if not swap_aligned.empty and not swap_aligned.isna().all().all():
            swap_array = swap_aligned.fillna(0).values.astype(np.float64)
            # スワップ損益を加算
            pl_array = pl_array + np.sum(swap_array * position_array, axis=1)
    
    # 9. 結果をDataFrameに変換（既存フォーマット互換）
    result_df = pd.DataFrame({
        "start_time": valid_idx,
        "end_time": end_time_valid,
        str(cprd_): pl_array
    })
    
    # 10. factorReturns_に結合（高速化：pd.concatを使用、最も高速）
    if len(factorReturns_) == 0:
        factorReturns_ = result_df
    else:
        # 既存のfactorReturns_と結合（reindexで高速化、pd.mergeを避ける）
        if "start_time" in factorReturns_.columns:
            # 既存データをstart_timeでインデックス化
            factorReturns_idx = factorReturns_.set_index("start_time")
            result_idx = result_df.set_index("start_time")
            
            # 共通インデックスを取得
            common_idx = factorReturns_idx.index.intersection(result_idx.index)
            
            if len(common_idx) > 0:
                # 既存データを共通インデックスに再配置
                factorReturns_aligned = factorReturns_idx.reindex(common_idx)
                result_aligned = result_idx.reindex(common_idx)
                
                # 新規列を直接代入（高速、end_time列は上書き）
                for col in result_aligned.columns:
                    factorReturns_aligned[col] = result_aligned[col]
                
                factorReturns_ = factorReturns_aligned.reset_index()
            else:
                # 共通インデックスがない場合は新規データのみ
                factorReturns_ = result_df
        else:
            # 既存データにstart_time列がない場合は新規データのみ
            factorReturns_ = result_df
    
    return factorReturns_



def makeFactorReturnA(fwdRateFactor_ , factorReturns_, position_id_ , fwdRatePosition_,spotRate_ , swap_df=None):
    for cprd_ in FACTOR_CALCULATION_PERIOD_A :
        ranking_  = fwdRateFactor_.set_index("start_time").rolling(cprd_).std().rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_A[position_id_], axis=0).T.dropna()
        if USE_FAST:
            factorReturns_ = makeFactorReturn_fast(factorReturns_, ranking_, cprd_, fwdRatePosition_, spotRate_, swap_df=swap_df)
        else:
            factorReturns_ = makeFactorReturn(factorReturns_,ranking_ , cprd_ , fwdRatePosition_,spotRate_ )
    return factorReturns_

def makeFactorReturnA_NY17(factorReturns_, position_id_ ):
    return makeFactorReturnA(FWDRATE_A_NY17 , factorReturns_, position_id_ , FWDRATE_A_NY17, SPOTRATE_A_NY17 )

def makeFactorReturnA_NY17TK20( factorReturns_, position_id_ ):
    return makeFactorReturnA(FWDRATE_A_NY17TK20 , factorReturns_, position_id_ , FWDRATE_A_NY17TK20, SPOTRATE_A_NY17TK20 )

def makeFactorReturnA_NY17TK1630( factorReturns_, position_id_ ):
    return makeFactorReturnA(FWDRATE_A_NY17TK1630 , factorReturns_, position_id_ ,FWDRATE_A_NY17TK1630, SPOTRATE_A_NY17TK1630 )


def makeFactorReturnA_TK20(factorReturns_, position_id_ ):
    return makeFactorReturnA(FWDRATE_A_NY17TK20 , factorReturns_, position_id_ ,FWDRATE_A_TK20, SPOTRATE_A_TK20 )

def makeFactorReturnA_TK1630(factorReturns_, position_id_ ):
    return makeFactorReturnA(FWDRATE_A_NY17TK1630 , factorReturns_, position_id_ , FWDRATE_A_TK1630, SPOTRATE_A_TK1630 )


def makeFactorReturnB( fwdRateFactor_ ,factorReturns_, position_id_,fwdRatePosition_, spotRate_ , swap_df=None):
    for cprd_ in FACTOR_CALCULATION_PERIOD_B :
        ranking_  = (fwdRateFactor_ .set_index(["start_time"]) - fwdRateFactor_.set_index(["start_time"]).rolling(cprd_).mean() ).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_B[position_id_], axis=0).T.dropna()
        if USE_FAST:
            factorReturns_ = makeFactorReturn_fast(factorReturns_, ranking_, cprd_, fwdRatePosition_, spotRate_, swap_df=swap_df)
        else:
            factorReturns_ = makeFactorReturn(factorReturns_,ranking_ ,  cprd_,fwdRatePosition_,spotRate_ )
    return factorReturns_

def makeFactorReturnB_NY17( factorReturns_, position_id_ ):
    return makeFactorReturnB(FWDRATE_B_NY17 , factorReturns_, position_id_ , FWDRATE_B_NY17, SPOTRATE_B_NY17 )

def makeFactorReturnB_NY17TK20( factorReturns_, position_id_ ):
    return makeFactorReturnB(FWDRATE_B_NY17TK20 , factorReturns_, position_id_ ,FWDRATE_B_NY17TK20, SPOTRATE_B_NY17TK20 )

def makeFactorReturnB_NY17TK1630( factorReturns_, position_id_ ):
    return makeFactorReturnB(FWDRATE_B_NY17TK1630 , factorReturns_, position_id_ ,FWDRATE_B_NY17TK1630, SPOTRATE_B_NY17TK1630 )


def makeFactorReturnB_TK20( factorReturns_, position_id_ ):
    return makeFactorReturnB(FWDRATE_B_NY17TK20 , factorReturns_, position_id_ , FWDRATE_B_TK20, SPOTRATE_B_TK20 )

def makeFactorReturnB_TK1630( factorReturns_, position_id_ ):
    return makeFactorReturnB(FWDRATE_B_NY17TK1630 , factorReturns_, position_id_ ,FWDRATE_B_TK1630, SPOTRATE_B_TK1630 )

def makeFactorReturnC(fwdRateFactor_, factorReturns_, position_id_ ,fwdRatePosition_, spotRate_ , swap_df=None):
    for cprd_ in FACTOR_CALCULATION_PERIOD_C :
        ranking_  = fwdRateFactor_.set_index(["start_time"]).pct_change(cprd_).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_C[position_id_], axis=0).T.dropna()
        if USE_FAST:
            factorReturns_ = makeFactorReturn_fast(factorReturns_, ranking_, cprd_, fwdRatePosition_, spotRate_, swap_df=swap_df)
        else:
            factorReturns_ = makeFactorReturn(factorReturns_,ranking_ ,  cprd_ , fwdRatePosition_,spotRate_ )
    return factorReturns_

def makeFactorReturnC_NY17( factorReturns_, position_id_ ):
    return makeFactorReturnC(FWDRATE_C_NY17 , factorReturns_, position_id_ , FWDRATE_C_NY17,SPOTRATE_C_NY17 )

def makeFactorReturnC_NY17TK20( factorReturns_, position_id_ ):
    return makeFactorReturnC(FWDRATE_C_NY17TK20 , factorReturns_, position_id_ , FWDRATE_C_NY17TK20,SPOTRATE_C_NY17TK20 )

def makeFactorReturnC_NY17TK1630( factorReturns_, position_id_ ):
    return makeFactorReturnC(FWDRATE_C_NY17TK1630 , factorReturns_, position_id_ ,FWDRATE_C_NY17TK1630, SPOTRATE_C_NY17TK1630 )

def makeFactorReturnC_TK20( factorReturns_, position_id_ ):
    return makeFactorReturnC(FWDRATE_C_NY17TK20 , factorReturns_, position_id_ , FWDRATE_C_TK20,SPOTRATE_C_TK20 )

def makeFactorReturnC_TK1630( factorReturns_, position_id_ ):
    return makeFactorReturnC(FWDRATE_C_NY17TK1630 , factorReturns_, position_id_ ,FWDRATE_C_TK1630, SPOTRATE_C_TK1630 )



def makeWeightA(fwdRate_,positionId1_,positionId2_):
    if positionId1_ == positionId2_:
        weight_ = {}
        for cprd_ in FACTOR_CALCULATION_PERIOD_A :
            weight_[str(cprd_)] = fwdRate_.set_index("start_time").rolling(cprd_).std().rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_A[positionId1_], axis=0).T.dropna()

    else:
        weight_ = {}
        for cprd_ in FACTOR_CALCULATION_PERIOD_A :
            weight_[str(cprd_)+"_x"] = fwdRate_.set_index("start_time").rolling(cprd_).std().rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_A[positionId1_], axis=0).T.dropna()
            weight_[str(cprd_)+"_y"] = fwdRate_.set_index("start_time").rolling(cprd_).std().rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_A[positionId2_], axis=0).T.dropna()
    return weight_    

def makeWeightA_NY17(positionId1_,positionId2_):
    return makeWeightA(FWDRATE_A_NY17,positionId1_,positionId2_)

def makeWeightA_TK20(positionId1_,positionId2_):
    return makeWeightA(FWDRATE_A_NY17TK20,positionId1_,positionId2_)

def makeWeightA_TK1630(positionId1_,positionId2_):
    return makeWeightA(FWDRATE_A_NY17TK1630,positionId1_,positionId2_)


def makeWeightB(fwdRate_, positionId1_,positionId2_):
    if positionId1_ == positionId2_:
        weight_ = {}
        for cprd_ in FACTOR_CALCULATION_PERIOD_B :
            weight_[str(cprd_)] =  (fwdRate_.set_index(["start_time"]) - fwdRate_.set_index(["start_time"]).rolling(cprd_).mean() ).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_B[positionId1_], axis=0).T.dropna()

    else:
       weight_ = {}
       for cprd_ in FACTOR_CALCULATION_PERIOD_B :
            weight_[str(cprd_)+"_x"] =  (fwdRate_.set_index(["start_time"]) - fwdRate_.set_index(["start_time"]).rolling(cprd_).mean() ).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_B[positionId1_], axis=0).T.dropna()
            weight_[str(cprd_)+"_y"] =  (fwdRate_.set_index(["start_time"]) - fwdRate_.set_index(["start_time"]).rolling(cprd_).mean() ).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_B[positionId2_], axis=0).T.dropna()
    return weight_    

def makeWeightB_NY17(positionId1_,positionId2_):
    return makeWeightB(FWDRATE_B_NY17,positionId1_,positionId2_)

def makeWeightB_TK20(positionId1_,positionId2_):
    return makeWeightB(FWDRATE_B_NY17TK20,positionId1_,positionId2_)

def makeWeightB_TK1630(positionId1_,positionId2_):
    return makeWeightB(FWDRATE_B_NY17TK1630,positionId1_,positionId2_)


def makeWeightC(fwdRate_, positionId1_,positionId2_):
    if positionId1_ == positionId2_:
        weight_ = {}
        for cprd_ in FACTOR_CALCULATION_PERIOD_C :
            weight_[str(cprd_)] = fwdRate_.set_index(["start_time"]).pct_change(cprd_).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_C[positionId1_], axis=0).T.dropna()

    else:
        weight_ = {}
        for cprd_ in FACTOR_CALCULATION_PERIOD_C :
            weight_[str(cprd_)+"_x"] = fwdRate_.set_index(["start_time"]).pct_change(cprd_).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_C[positionId1_], axis=0).T.dropna()
            weight_[str(cprd_)+"_y"] = fwdRate_.set_index(["start_time"]).pct_change(cprd_).rank(axis = 1, method= "min").T.apply( POSITION_FUNCTIONS_C[positionId2_], axis=0).T.dropna()
    return weight_    

def makeWeightC_NY17(positionId1_,positionId2_):
    return makeWeightC(FWDRATE_C_NY17,positionId1_,positionId2_)

def makeWeightC_TK20(positionId1_,positionId2_):
    return makeWeightC(FWDRATE_C_NY17TK20,positionId1_,positionId2_)

def makeWeightC_TK1630(positionId1_,positionId2_):
    return makeWeightC(FWDRATE_C_NY17TK1630,positionId1_,positionId2_)






def simulateIndividualStrategyForSim(factorReturns_, in_, out_, n_ ,weight_,positionId1_ , positionId2_,  fileName_ ,factorReturns2_=None ):
    if factorReturns2_ is None:
        factorReturns2_ = factorReturns_
        
    rslt_ = pd.DataFrame()
    retWeight_ = pd.DataFrame()
    def my_select(vec_, n_ ):
        vec_[ vec_ <= n_ ]  = 1
        vec_[ vec_ >= (n_+1) ]  = 0
        sum_ = sum(vec_)
        if sum_ > 0 :
            vec_ = vec_ /sum(vec_)
        return vec_
    def vecProduct( vec1_ , vec2_):
        return vec1_ * vec2_
    
    #my_factorReturns_ = factorReturns_ >> mutate(end_time=lead(X.start_time, i=1)) >> select(X.start_time, X.end_time, everything())
    my_factorReturns_ = factorReturns_.copy()
    my_factorReturns_["end_time"] =my_factorReturns_["start_time"].shift(-1)
        
    #date_df = my_factorReturns_[["start_time"]] >> mutate(ref_last_start_time = lag(X.start_time, i=2), ref_last_end_time = lag(X.start_time, i=1)) >> mutate(trade_fst_start_time = X.start_time)
    date_df = my_factorReturns_[["start_time"]].copy()
    date_df["ref_last_start_time"] = my_factorReturns_["start_time"].shift(2)
    date_df["ref_last_end_time"] = my_factorReturns_["start_time"].shift(1)
    date_df["trade_fst_start_time"] = my_factorReturns_["start_time"]

    # rollingする前に数値列のみを選択（datetime列を除外）
    numeric_cols = my_factorReturns_.select_dtypes(include=[np.number]).columns.tolist()
    if 'start_time' in numeric_cols:
        numeric_cols.remove('start_time')
    my_sr_ = my_factorReturns_.set_index("start_time")[numeric_cols].rolling(in_-1 ).mean().shift(2).dropna()
    ref_mean_vals= my_sr_.reset_index().copy()
    ref_mean_vals = pd.merge(ref_mean_vals, date_df, on = "start_time",how ="left")
    #ref_mean_vals= my_sr_.reset_index() >> mutate(start_time = my_sr_.index) >> left_join(date_df, by = "start_time") >> select(X.start_time, X.ref_last_start_time, X.ref_last_end_time, X.trade_fst_start_time, everything())
    
    # rank()を実行する前に数値列のみを選択（datetime列を除外）
    rank_cols = ref_mean_vals.select_dtypes(include=[np.number]).columns.tolist()
    if 'start_time' in rank_cols:
        rank_cols.remove('start_time')
    position_ =   ref_mean_vals[::out_].set_index("start_time")[rank_cols].round(10).rank(
    axis = 1 , ascending = False, method ="min" ).apply(
    my_select, n_ = n_,  axis=1).dropna().sort_index()
    
    if PYTHONFILENAME == "train.py":
        allocation_ = pd.merge(factorReturns2_[["start_time"]],position_, on ="start_time", how ="left"  ).fillna(method='ffill').dropna()
        fileFolder_ = fileName_.replace("train/output/summary/train_result_","train/output/intermediate/factor_return_portfolio_allocation/" )
        #allocation_.to_csv(fileFolder_+"_"+str(out_)+"_"+str(in_)+"_"+str(positionId1_)+"_"+str(positionId2_)+"_"+str(n_)+".csv" ,index=False)
    
    
    for row_ in range(1, len(position_) ):
        outofSamplePeriodFrom_ = position_.index[row_-1]
        outofSamplePeriodTo_ = position_.index[row_]
        tmp_ =  factorReturns2_[  ( factorReturns2_["start_time"] >=outofSamplePeriodFrom_ )  & ( factorReturns2_["start_time"] < outofSamplePeriodTo_ )  ].set_index("start_time") 
        vec_ = list( position_.loc[outofSamplePeriodFrom_].reset_index(drop = True) ) 
        tmp_result = tmp_.apply( vecProduct, vec2_ = vec_ , axis= 1 )
        if len(rslt_) == 0:
            rslt_ = tmp_result
        else:
            rslt_ = pd.concat([rslt_, tmp_result])
        addonWeight_ = 0
        for i_,v_ in enumerate(vec_):
            if v_ >0:
                addonWeightEach_ = weight_[position_.columns[i_]]
                addonWeightEach_ = addonWeightEach_[ (addonWeightEach_.index >=outofSamplePeriodFrom_) & ((addonWeightEach_.index < outofSamplePeriodTo_) ) ]
                addonWeight_ = addonWeight_  + addonWeightEach_*v_
        if len(retWeight_) == 0:
            retWeight_ = addonWeight_
        else:
            retWeight_  = pd.concat([retWeight_, addonWeight_])
    
        
    outofSamplePeriodFrom_ = position_.index[ len(position_)-1 ]
    tmp_ =  factorReturns2_[  ( factorReturns2_["start_time"] >=outofSamplePeriodFrom_ ) ].set_index("start_time") 
    vec_ = list( position_.loc[outofSamplePeriodFrom_].reset_index(drop = True) ) 
    addonWeight_ = 0
    for i_,v_ in enumerate(vec_):
        if v_ >0:
            addonWeightEach_ = weight_[position_.columns[i_]]
            addonWeightEach_ = addonWeightEach_[ addonWeightEach_.index >=outofSamplePeriodFrom_]
            addonWeight_ = addonWeight_  + addonWeightEach_*v_
            
    if len(retWeight_) == 0:
        retWeight_ = addonWeight_
    else:
        retWeight_  = pd.concat([retWeight_, addonWeight_])
    
    tmp_result = tmp_.apply( vecProduct, vec2_ = vec_ , axis= 1 )
    if len(rslt_) == 0:
        rslt_ = tmp_result
    else:
        rslt_ = pd.concat([rslt_, tmp_result]) 
    rslt_["total"]  = rslt_.sum(axis= 1)
    
    return rslt_, retWeight_



def simulateIndividualStrategyForProd(factorReturns_, in_, out_, n_ ,weight_,positionId1_ , positionId2_,  fileName_ , datePre_,factorReturns2_=None ):
    if factorReturns2_ is None:
        factorReturns2_ = factorReturns_
        
    rslt_ = pd.DataFrame()
    retWeight_ = pd.DataFrame()
    def my_select(vec_, n_ ):
        vec_[ vec_ <= n_ ]  = 1
        vec_[ vec_ >= (n_+1) ]  = 0
        sum_ = sum(vec_)
        if sum_ > 0 :
            vec_ = vec_ /sum(vec_)
        return vec_
    def vecProduct( vec1_ , vec2_):
        return vec1_ * vec2_
    
    #my_factorReturns_ = factorReturns_ >> mutate(end_time=lead(X.start_time, i=1)) >> select(X.start_time, X.end_time, everything())
    my_factorReturns_ = factorReturns_.copy()
    my_factorReturns_["end_time"] =my_factorReturns_["start_time"].shift(-1)
        
    #date_df = my_factorReturns_[["start_time"]] >> mutate(ref_last_start_time = lag(X.start_time, i=2), ref_last_end_time = lag(X.start_time, i=1)) >> mutate(trade_fst_start_time = X.start_time)
    date_df = my_factorReturns_[["start_time"]].copy()
    date_df["ref_last_start_time"] = my_factorReturns_["start_time"].shift(2)
    date_df["ref_last_end_time"] = my_factorReturns_["start_time"].shift(1)
    date_df["trade_fst_start_time"] = my_factorReturns_["start_time"]

    # rollingする前に数値列のみを選択（datetime列を除外）
    numeric_cols = my_factorReturns_.select_dtypes(include=[np.number]).columns.tolist()
    if 'start_time' in numeric_cols:
        numeric_cols.remove('start_time')
    my_sr_ = my_factorReturns_.set_index("start_time")[numeric_cols].rolling(in_-1 ).mean().shift(2).dropna()
    ref_mean_vals= my_sr_.reset_index().copy()
    ref_mean_vals = pd.merge(ref_mean_vals, date_df, on = "start_time",how ="left")
    #ref_mean_vals= my_sr_.reset_index() >> mutate(start_time = my_sr_.index) >> left_join(date_df, by = "start_time") >> select(X.start_time, X.ref_last_start_time, X.ref_last_end_time, X.trade_fst_start_time, everything())
    
    # rank()を実行する前に数値列のみを選択（datetime列を除外）
    rank_cols = ref_mean_vals.select_dtypes(include=[np.number]).columns.tolist()
    if 'start_time' in rank_cols:
        rank_cols.remove('start_time')
    position_ =   ref_mean_vals[::out_].set_index("start_time")[rank_cols].round(10).rank(
    axis = 1 , ascending = False, method ="min" ).apply(
    my_select, n_ = n_,  axis=1).dropna().sort_index()
    
    
    from_ = np.count_nonzero(position_.index  < datePre_)
    for row_ in range(from_, len(position_) ):
        outofSamplePeriodFrom_ = position_.index[row_-1]
        outofSamplePeriodTo_ = position_.index[row_]
        tmp_ =  factorReturns2_[  ( factorReturns2_["start_time"] >=outofSamplePeriodFrom_ )  & ( factorReturns2_["start_time"] < outofSamplePeriodTo_ )  ].set_index("start_time") 
        vec_ = list( position_.loc[outofSamplePeriodFrom_].reset_index(drop = True) ) 
        tmp_result = tmp_.apply( vecProduct, vec2_ = vec_ , axis= 1 )
        if len(rslt_) == 0:
            rslt_ = tmp_result
        else:
            rslt_ = pd.concat([rslt_, tmp_result])
        addonWeight_ = 0
        for i_,v_ in enumerate(vec_):
            if v_ >0:
                addonWeightEach_ = weight_[position_.columns[i_]]
                addonWeightEach_ = addonWeightEach_[ (addonWeightEach_.index >=outofSamplePeriodFrom_) & ((addonWeightEach_.index < outofSamplePeriodTo_) ) ]
                addonWeight_ = addonWeight_  + addonWeightEach_*v_
        if len(retWeight_) == 0:
            retWeight_ = addonWeight_
        else:
            retWeight_  = pd.concat([retWeight_, addonWeight_])
    
        
    outofSamplePeriodFrom_ = position_.index[ len(position_)-1 ]
    tmp_ =  factorReturns2_[  ( factorReturns2_["start_time"] >=outofSamplePeriodFrom_ ) ].set_index("start_time") 
    vec_ = list( position_.loc[outofSamplePeriodFrom_].reset_index(drop = True) ) 
    addonWeight_ = 0
    for i_,v_ in enumerate(vec_):
        if v_ >0:
            addonWeightEach_ = weight_[position_.columns[i_]]
            addonWeightEach_ = addonWeightEach_[ addonWeightEach_.index >=outofSamplePeriodFrom_]
            addonWeight_ = addonWeight_  + addonWeightEach_*v_
            
    if len(retWeight_) == 0:
        retWeight_ = addonWeight_
    else:
        retWeight_  = pd.concat([retWeight_, addonWeight_])
    
    tmp_result = tmp_.apply( vecProduct, vec2_ = vec_ , axis= 1 )
    if len(rslt_) == 0:
        rslt_ = tmp_result
    else:
        rslt_ = pd.concat([rslt_, tmp_result]) 
    rslt_["total"]  = rslt_.sum(axis= 1)
    
    return rslt_, retWeight_


def simulate(factorReturns_, simulationPeriod_,endTime_,weight_,positionId1_ , positionId2_,  fileName_  ):
    output_ = pd.DataFrame()
    ret_ = {}
    for simulationTo_ in simulationPeriod_:
        ret_[simulationTo_] =pd.DataFrame()
    
    for in_ in REF_PERIOD_WIDTH :
        for out_ in TRADE_PERIOD_WIDTH:
            for n_ in NUMBER_OF_PARAMETERS:
                name_ = str(in_)+"_"+str(out_)+"_"+str(n_) 
                rslt_, retWeight_ = simulateIndividualStrategyForSim(factorReturns_.drop("end_time",axis=1), in_, out_, n_,weight_,positionId1_ , positionId2_,  fileName_  )
                fileFolder_ = fileName_.replace("train/output/summary/train_result_","train/output/intermediate/targetWeight_each_parameter/")
                #retWeight_.to_csv(fileFolder_+"_"+str(out_)+"_"+str(in_)+"_"+str(positionId1_)+"_"+str(positionId2_)+"_"+str(n_)+".csv" )
                addon_ = rslt_.reset_index()[["start_time","total" ]].rename(columns = {"total": name_ }  ) 
                addon_ = pd.merge(addon_, endTime_[["start_time","end_time"]], on ="start_time", how ="inner" )

                for simulationTo_ in simulationPeriod_:
                    addonSimulationTo_ = addon_[addon_["end_time"].dt.year <= simulationTo_   ].drop("end_time",axis=1)
                    if len(ret_[simulationTo_]) == 0 :
                        ret_[simulationTo_] =  addonSimulationTo_
                    else:
                        ret_[simulationTo_] = pd.merge(ret_[simulationTo_], addonSimulationTo_ ,  on ="start_time", how ="inner"    )

    for simulationTo_ in simulationPeriod_:
        for in_ in REF_PERIOD_WIDTH :
            for out_ in TRADE_PERIOD_WIDTH:
                for n_ in NUMBER_OF_PARAMETERS:
                    name_ = str(in_)+"_"+str(out_)+"_"+str(n_) 
                    sr_ = ret_[simulationTo_][name_].mean() 
                    output_ = pd.concat([output_, pd.DataFrame({"ref_period_width": [in_], "trade_period_width":  [out_],
                                                        "number_of_parameters": [n_], "mean":[sr_], "simulation_period_to": [simulationTo_]    })])
    output_ = output_.reset_index(drop=True)
    output_["position_id_1"] = positionId1_
    output_["position_id_2"] = positionId2_
    return output_


def train(  calculateFactorReturn , simulationPeriod_ , calculateWeight,positionFunctions_ ,  fileName_ ):
    
    endTime_ = getEndTime(calculateFactorReturn)
    factorReturnsDict_ = {} 
    weightDict_ = {}
    for positionId1_ ,positionId2_  in itertools.combinations_with_replacement(range(0,len(positionFunctions_) ) ,2):
        weightDict_[(positionId1_ ,positionId2_)] = calculateWeight( positionId1_ , positionId2_)
        if positionId1_ == positionId2_: 
                    factorReturnsDict_[positionId1_] = calculateFactorReturn(pd.DataFrame(), positionId1_)
                    
    strategyInfo_ = {}
    for simulationTo_ in simulationPeriod_:
        strategyInfo_[simulationTo_] = pd.DataFrame()
    
    for positionId1_ ,positionId2_  in itertools.combinations_with_replacement(range(0,len(positionFunctions_) ) ,2):
        
        factorReturns_ = factorReturnsDict_[positionId1_]
        if positionId1_ != positionId2_: 
            factorReturns_ = pd.merge( factorReturns_, factorReturnsDict_[positionId2_], on =["start_time","end_time"],how="inner")
            
        weight_ = weightDict_[(positionId1_ ,positionId2_)]
        simulationResult_ = simulate(factorReturns_, simulationPeriod_,endTime_ ,weight_,positionId1_ , positionId2_,  fileName_ )
        
        for simulationTo_ in simulationPeriod_:
            output_ = simulationResult_[simulationResult_["simulation_period_to"] == simulationTo_  ].sort_values("mean",ascending = False,kind="mergesort").reset_index(drop=True)
            
            for row_ in range(NUMBER_OF_HYPERPARAMETER) :
                if output_["mean"][row_]  > THRESHOLD:
                    strategyInfo_[simulationTo_] = pd.concat([strategyInfo_[simulationTo_], output_.iloc[[row_]]])

    #結果の出力
    ret_ = pd.DataFrame()
    for simulationTo_ in simulationPeriod_:
        try:
            strategyInfo_[simulationTo_] = strategyInfo_[simulationTo_].reset_index(drop=True)
            strategyInfo_[simulationTo_]["trade_period_width"] = strategyInfo_[simulationTo_]["trade_period_width"].astype(int)
            strategyInfo_[simulationTo_]["ref_period_width"]= strategyInfo_[simulationTo_]["ref_period_width"].astype(int)
            strategyInfo_[simulationTo_]["number_of_parameters"]= strategyInfo_[simulationTo_]["number_of_parameters"].astype(int)
            ret_ = pd.concat([ret_, strategyInfo_[simulationTo_]])
        except:
            pass
    ret_.to_csv( fileName_ + ".csv" , index=False )
    

def train_NY17TK20_A( LastSimulationPeriod_): 
    train(  calculateFactorReturn = makeFactorReturnA_TK20 ,
        simulationPeriod_ = range(2005,LastSimulationPeriod_+1) ,
        calculateWeight = makeWeightA_TK20 ,
        positionFunctions_ = POSITION_FUNCTIONS_A,
        fileName_ = DIRECTORY+"train/output/summary/train_result_NY17TK20_A")

def train_NY17TK20_B( LastSimulationPeriod_): 
    train(  calculateFactorReturn = makeFactorReturnB_TK20 ,
            simulationPeriod_ = range(2006,LastSimulationPeriod_+1) ,
            calculateWeight = makeWeightB_TK20 ,
            positionFunctions_ = POSITION_FUNCTIONS_B,
            fileName_ = DIRECTORY+"train/output/summary/train_result_NY17TK20_B")

def train_NY17TK20_C( LastSimulationPeriod_): 
    train(  calculateFactorReturn = makeFactorReturnC_TK20 ,
            simulationPeriod_ = range(2005,LastSimulationPeriod_+1) ,
            calculateWeight = makeWeightC_TK20 ,
            positionFunctions_ = POSITION_FUNCTIONS_C,
            fileName_ = DIRECTORY+"train/output/summary/train_result_NY17TK20_C")


def train_NY17NY17_A( LastSimulationPeriod_): 
    train(  calculateFactorReturn = makeFactorReturnA_NY17 ,
        simulationPeriod_ = range(2005,LastSimulationPeriod_+1) ,
        calculateWeight = makeWeightA_NY17 ,
        positionFunctions_ = POSITION_FUNCTIONS_A,
        fileName_ = DIRECTORY+"train/output/summary/train_result_NY17NY17_A")

def train_NY17NY17_B( LastSimulationPeriod_): 
    train(  calculateFactorReturn = makeFactorReturnB_NY17 ,
            simulationPeriod_ = range(2006,LastSimulationPeriod_+1) ,
            calculateWeight = makeWeightB_NY17 ,
            positionFunctions_ = POSITION_FUNCTIONS_B,
            fileName_ =DIRECTORY+ "train/output/summary/train_result_NY17NY17_B")

def train_NY17NY17_C( LastSimulationPeriod_): 
    train(  calculateFactorReturn = makeFactorReturnC_NY17,
            simulationPeriod_ = range(2005,LastSimulationPeriod_+1) ,
            calculateWeight = makeWeightC_NY17 ,
            positionFunctions_ = POSITION_FUNCTIONS_C,
            fileName_ = DIRECTORY+"train/output/summary/train_result_NY17NY17_C")


def testForSim(  calculateFactorReturn , calculateFactorReturn2 ,simulationPeriod_ , calculateWeight,  fileName_,outputName_,strategyName_ = "strategy"):
    if "test_result_NY17NY17_NY17NY17_NY17TK1630" in outputName_:
        detailOutputFolder_ = "test/output/detail/TK1630/"
    elif "test_result_NY17NY17_NY17NY17_NY17TK20" in outputName_:
        detailOutputFolder_ = "test/output/detail/TK20/"
    summaryOutputFolder_ = "test/output/summary/"
    
    
    if calculateFactorReturn is not None:
        for simulationTo_ in simulationPeriod_:
            strategyInfo_ = pd.read_csv( fileName_  +  ".csv")
            strategyInfo_ = strategyInfo_[strategyInfo_["simulation_period_to"] == simulationTo_ ].reset_index()
            if len(strategyInfo_) == 0 :
                return 

        ret_ = {}
        ret2_ = {}
        for lag_ in LAG_RANGE:
            ret_[lag_] = pd.DataFrame()
            ret2_[lag_] = pd.DataFrame()
            
        factorReturnsDict1_ = {} 
        factorReturnsDict2_ = {} 
        weightDict_ = {}
        for positionId1_ ,positionId2_  in itertools.combinations_with_replacement(range(0,len(POSITION_FUNCTIONS_A) ) ,2): #len(POSITION_FUNCTIONS_A) = len(POSITION_FUNCTIONS_B) = len(POSITION_FUNCTIONS_C)
            weightDict_[(positionId1_ ,positionId2_)] = calculateWeight( positionId1_ , positionId2_)
            if positionId1_ == positionId2_: 
                factorReturnsDict1_[positionId1_] = calculateFactorReturn(pd.DataFrame(), positionId1_)
                factorReturnsDict2_[positionId1_] = calculateFactorReturn2(pd.DataFrame(), positionId1_)
        
        for simulationTo_ in simulationPeriod_:
            strategyInfo_ = pd.read_csv( fileName_  +  ".csv")
            strategyInfo_ = strategyInfo_[strategyInfo_["simulation_period_to"] == simulationTo_ ].reset_index()
            
            strategyWeight_ = 0 
            strategyReturn_ = pd.DataFrame()
            
            for row_ in range(len(strategyInfo_)):
                positionId1_ = strategyInfo_["position_id_1"][row_]
                positionId2_ = strategyInfo_["position_id_2"][row_] 
                
                factorReturns_ = pd.DataFrame() 
                factorReturns2_ = pd.DataFrame() 
                factorReturns_ = factorReturnsDict1_[positionId1_]
                factorReturns2_ = factorReturnsDict2_[positionId1_]
                
                if positionId1_ != positionId2_: 
                    factorReturns_ = pd.merge( factorReturns_, factorReturnsDict1_[positionId2_], on =["start_time","end_time"],how="inner")
                    factorReturns2_ = pd.merge( factorReturns2_, factorReturnsDict2_[positionId2_], on =["start_time","end_time"],how="inner")
                    
                    
                weight_ = weightDict_[(positionId1_ ,positionId2_)]

                out_ = strategyInfo_["trade_period_width"][row_] ;  in_ = strategyInfo_["ref_period_width"][row_] ; n_ = strategyInfo_["number_of_parameters"][row_]
                name_ = str(positionId1_)+ "_" +str(positionId2_)+"_" + str(in_)+"_"+str(out_)+"_"+str(n_) 
                
                rslt_, retWeight_ = simulateIndividualStrategyForSim(factorReturns_.drop("end_time",axis=1), in_, out_, n_,weight_,positionId1_ , positionId2_,  fileName_ ,factorReturns2_.drop("end_time",axis=1))
                addon_ = rslt_.reset_index()[["start_time","total" ]].rename(columns = {"total":name_ }  )
                
                strategyWeight_ = strategyWeight_ + retWeight_ 
                if len(strategyReturn_) == 0 :
                    strategyReturn_ =   addon_
                else:
                    strategyReturn_ = pd.merge(strategyReturn_, addon_ ,on ="start_time", how="inner")
                
                strategyReturn_= strategyReturn_[strategyReturn_["start_time"].dt.year >  simulationTo_ ]
                strategyWeight_= strategyWeight_[strategyWeight_.index.year >  simulationTo_ ]
                
                strategyWeight_ = strategyWeight_.dropna()
                strategyReturn_ = strategyReturn_.dropna()
                
            strategyWeight_ = strategyWeight_/len(strategyInfo_)
            strategyWeight_ = strategyWeight_.reset_index()
            strategyReturn_[strategyName_] = list(strategyReturn_.set_index("start_time").mean(axis=1))
            
            
            for lag_ in LAG_RANGE:
                ret_[lag_] = pd.concat([ret_[lag_], strategyReturn_[strategyReturn_["start_time"].dt.year ==  simulationTo_ + lag_][["start_time",strategyName_]]])
                ret2_[lag_] = pd.concat([ret2_[lag_], strategyWeight_[strategyWeight_["start_time"].dt.year ==  simulationTo_ + lag_]])
        
        for lag_ in LAG_RANGE:

                ret_[lag_].to_csv( detailOutputFolder_ + outputName_ +"_lag="+str(lag_)+".csv" )
                performanceSummary(ret_[lag_], strategyName_ ).to_csv(detailOutputFolder_ + outputName_ +"_lag="+str(lag_)+"_summary.csv", index=True )
                ret2_[lag_].to_csv( detailOutputFolder_ + outputName_ +"_lag="+str(lag_)+"_weight.csv" )


    else : 
        df_ = pd.DataFrame()
        targetWeight_ = 0
        cnt_  = 0
        
        for strategy_ in ["A","B","C"]:
            for lag_ in LAG_RANGE:
                try:
                    summary_ = pd.read_csv(detailOutputFolder_ + outputName_+"_"+strategy_+"_lag=" + str(lag_) + "_summary.csv") 
                    if summary_["sr"][len(summary_)-1] >= -float('inf') :
                        addon_ = pd.read_csv(detailOutputFolder_ + outputName_+"_"+strategy_+"_lag=" + str(lag_)+".csv")
                        column_ = outputName_  +"_"+strategy_+"_lag=" + str(lag_)
                        addonWeight_ = pd.read_csv(detailOutputFolder_ + outputName_ +"_"+strategy_+"_lag=" + str(lag_)+"_weight.csv")
                        addonWeight_["start_time"] =  pd.to_datetime(addonWeight_["start_time"])
                        if 'Unnamed: 0' in addonWeight_.columns :
                            addonWeight_ = addonWeight_.drop('Unnamed: 0',axis=1)
                        if 'JPYUSD' not in addonWeight_.columns :
                            addonWeight_['JPYUSD'] = 0
                        addon_ = addon_.rename(columns={ addon_.columns.values[len(addon_.columns)-1] : column_ })
                        if len(df_ ) == 0 :
                            df_ = addon_[["start_time",column_]]
                        else: 
                            df_ = pd.merge(df_, addon_[["start_time",column_]] , on ="start_time", how="inner" ) 
                        targetWeight_ = targetWeight_  + addonWeight_.set_index("start_time")
                        cnt_ += 1
                except:
                    pass
                
        df_["start_time"] = pd.to_datetime(df_["start_time"])
        df_["total"] = list( df_.set_index("start_time").mean(axis=1))
        
        performanceSummary(df_, "total").to_csv( summaryOutputFolder_ + outputName_+"_simple.csv")
        performanceSummary2(df_, "total").to_csv(summaryOutputFolder_ + outputName_+"_compound.csv")
        performanceSummary2(df_[df_["start_time"].dt.year >= 2015 ], "total").to_csv(summaryOutputFolder_ + outputName_+"_compound_since2015.csv")
        targetWeight_ =  targetWeight_/cnt_ 
        targetWeight_ = targetWeight_.dropna()
        targetWeight_.to_csv(summaryOutputFolder_ + outputName_+"_targetWeight.csv")
        

def testForSim_NY17NY17_NY17NY17_NY17TK1630_A(LastSimulationPeriod_):
    testForSim(  calculateFactorReturn = makeFactorReturnA_NY17TK1630,calculateFactorReturn2 = makeFactorReturnA_TK1630,
          simulationPeriod_ =range(2010,LastSimulationPeriod_+1) , calculateWeight = makeWeightA_TK1630,
          fileName_ = DIRECTORY+"test/input/input_by_train/train_result_NY17NY17_A", outputName_ = "test_result_NY17NY17_NY17NY17_NY17TK1630_A",
          strategyName_ = "strategy_A" )

def testForSim_NY17NY17_NY17NY17_NY17TK1630_B(LastSimulationPeriod_):
    testForSim(  calculateFactorReturn = makeFactorReturnB_NY17TK1630, calculateFactorReturn2 = makeFactorReturnB_TK1630,
          simulationPeriod_ =range(2010,LastSimulationPeriod_+1) , calculateWeight = makeWeightB_TK1630,
          fileName_ = DIRECTORY+"test/input/input_by_train/train_result_NY17NY17_B",  outputName_ = "test_result_NY17NY17_NY17NY17_NY17TK1630_B",
          strategyName_ = "strategy_B" )

def testForSim_NY17NY17_NY17NY17_NY17TK1630_C(LastSimulationPeriod_):
    testForSim(  calculateFactorReturn = makeFactorReturnC_NY17TK1630, calculateFactorReturn2 = makeFactorReturnC_TK1630,
          simulationPeriod_ =range(2010,LastSimulationPeriod_+1), calculateWeight = makeWeightC_TK1630,
          fileName_ = DIRECTORY+"test/input/input_by_train/train_result_NY17NY17_C", outputName_ = "test_result_NY17NY17_NY17NY17_NY17TK1630_C",
          strategyName_ = "strategy_C" )

def testForSim_NY17NY17_NY17NY17_NY17TK1630_TOTAL():
    testForSim(  calculateFactorReturn = None , calculateFactorReturn2 = None ,
          simulationPeriod_ = None  , calculateWeight = None ,
          fileName_ = None ,
          outputName_ = "test_result_NY17NY17_NY17NY17_NY17TK1630",
          strategyName_ = "total" )






def testForProd(  calculateFactorReturn , calculateFactorReturn2 ,simulationPeriod_ , calculateWeight, fileName_,outputName_,strategyName_, date_):
    NumFiles_ = len(os.listdir(path=DIRECTORY+'test/output/prod')) 
    
    
    if calculateFactorReturn is not None:
        
        for simulationTo_ in simulationPeriod_:
            strategyInfo_ = pd.read_csv( fileName_  +  ".csv")
            strategyInfo_ = strategyInfo_[strategyInfo_["simulation_period_to"] == simulationTo_ ].reset_index()
            if len(strategyInfo_) == 0 :
                return 

        ret_ = {}
        ret2_ = {}
        for lag_ in LAG_RANGE:
            ret_[lag_] = pd.DataFrame()
            ret2_[lag_] = pd.DataFrame()
            
        factorReturnsDict1_ = {} 
        factorReturnsDict2_ = {} 
        weightDict_ = {}
        for positionId1_ ,positionId2_  in itertools.combinations_with_replacement(range(0,len(POSITION_FUNCTIONS_A) ) ,2): #len(POSITION_FUNCTIONS_A) = len(POSITION_FUNCTIONS_B) = len(POSITION_FUNCTIONS_C)
            weightDict_[(positionId1_ ,positionId2_)] = calculateWeight( positionId1_ , positionId2_)
            if positionId1_ == positionId2_: 
                factorReturnsDict1_[positionId1_] = calculateFactorReturn(pd.DataFrame(), positionId1_)
                factorReturnsDict2_[positionId1_] = calculateFactorReturn2(pd.DataFrame(), positionId1_)
        
        for simulationTo_ in simulationPeriod_:
            strategyInfo_ = pd.read_csv( fileName_  +  ".csv")
            strategyInfo_ = strategyInfo_[strategyInfo_["simulation_period_to"] == simulationTo_ ].reset_index()
            
            strategyWeight_ = 0 
            strategyReturn_ = pd.DataFrame()
            
            for row_ in range(len(strategyInfo_)):
                positionId1_ = strategyInfo_["position_id_1"][row_]
                positionId2_ = strategyInfo_["position_id_2"][row_] 
                
                factorReturns_ = pd.DataFrame() 
                factorReturns2_ = pd.DataFrame() 
                factorReturns_ = factorReturnsDict1_[positionId1_]
                factorReturns2_ = factorReturnsDict2_[positionId1_]
                
                
                if positionId1_ != positionId2_: 
                    factorReturns_ = pd.merge( factorReturns_, factorReturnsDict1_[positionId2_], on =["start_time","end_time"],how="inner")
                    factorReturns2_ = pd.merge( factorReturns2_, factorReturnsDict2_[positionId2_], on =["start_time","end_time"],how="inner")
                    
                weight_ = weightDict_[(positionId1_ ,positionId2_)]
                
                out_ = strategyInfo_["trade_period_width"][row_] ;  in_ = strategyInfo_["ref_period_width"][row_] ; n_ = strategyInfo_["number_of_parameters"][row_]
                name_ = str(positionId1_)+ "_" +str(positionId2_)+"_" + str(in_)+"_"+str(out_)+"_"+str(n_) 
                if NumFiles_ ==0:
                    rslt_, retWeight_ = simulateIndividualStrategyForSim(factorReturns_.drop("end_time",axis=1), in_, out_, n_,weight_,positionId1_ , positionId2_,  fileName_ ,factorReturns2_.drop("end_time",axis=1))
                else: 
                    fileList_ =os.listdir(DIRECTORY+"test/output/prod") 
                    fileList_ = [ int( x.replace("WeightFX_","").replace(".csv","")) for x in fileList_ if "WeightFX_" in x ]  
                    datePre_ = pd.to_datetime( str(np.max(fileList_) ) )
                    datePre_  =  datePre_ + relativedelta(hours=16, minutes=30)
                    
                    factorReturns_ = factorReturns_[factorReturns_["start_time"] <= date_]
                    factorReturns2_ = factorReturns2_[factorReturns2_["start_time"] <= date_]
                    rslt_, retWeight_ = simulateIndividualStrategyForProd(factorReturns_.drop("end_time",axis=1), in_, out_,
                                                                          n_,weight_,positionId1_ , positionId2_,  fileName_ , datePre_,
                                                                          factorReturns2_.drop("end_time",axis=1) )
                addon_ = rslt_.reset_index()[["start_time","total" ]].rename(columns = {"total":name_ }  )
                                
                strategyWeight_ = strategyWeight_ + retWeight_ 
                if len(strategyReturn_) == 0 :
                    strategyReturn_ =   addon_
                else:
                    strategyReturn_ = pd.merge(strategyReturn_, addon_ ,on ="start_time", how="inner")
                
                strategyReturn_= strategyReturn_[strategyReturn_["start_time"].dt.year >  simulationTo_ ]
                strategyWeight_= strategyWeight_[strategyWeight_.index.year >  simulationTo_ ]
                
                strategyWeight_ = strategyWeight_.dropna()
                strategyReturn_ = strategyReturn_.dropna()
                
            strategyWeight_ = strategyWeight_/len(strategyInfo_)
            strategyWeight_ = strategyWeight_.reset_index()
            strategyReturn_[strategyName_] = list(strategyReturn_.set_index("start_time").mean(axis=1))
            
            
            for lag_ in LAG_RANGE:
                ret_[lag_] = pd.concat([ret_[lag_], strategyReturn_[strategyReturn_["start_time"].dt.year ==  simulationTo_ + lag_][["start_time",strategyName_]]])
                ret2_[lag_] = pd.concat([ret2_[lag_], strategyWeight_[strategyWeight_["start_time"].dt.year ==  simulationTo_ + lag_]])
        
        for lag_ in LAG_RANGE:
                ret_[lag_].to_csv(outputName_ +"_lag="+str(lag_)+".csv" )
                performanceSummary(ret_[lag_], strategyName_ ).to_csv(outputName_ +"_lag="+str(lag_)+"_summary.csv", index=True )
                ret2_[lag_].to_csv(outputName_ +"_lag="+str(lag_)+"_weight.csv" )
    else : 
        df_ = pd.DataFrame()
        targetWeight_ = 0
        cnt_  = 0
        for strategy_ in ["A","B","C"]:
            for lag_ in LAG_RANGE:
                try:
                    summary_ = pd.read_csv(outputName_+"_"+strategy_+"_lag=" + str(lag_) + "_summary.csv") 
                    if summary_["sr"][len(summary_)-1] >= -float('inf') :
                        addon_ = pd.read_csv(outputName_+"_"+strategy_+"_lag=" + str(lag_)+".csv")
                        column_ = outputName_  +"_"+strategy_+"_lag=" + str(lag_)
                        addonWeight_ = pd.read_csv(outputName_ +"_"+strategy_+"_lag=" + str(lag_)+"_weight.csv")
                        addonWeight_["start_time"] =  pd.to_datetime(addonWeight_["start_time"])
                        if 'Unnamed: 0' in addonWeight_.columns :
                            addonWeight_ = addonWeight_.drop('Unnamed: 0',axis=1)
                        if 'JPYUSD' not in addonWeight_.columns :
                            addonWeight_['JPYUSD'] = 0
                        addon_ = addon_.rename(columns={ addon_.columns.values[len(addon_.columns)-1] : column_ })
                        if len(df_ ) == 0 :
                            df_ = addon_[["start_time",column_]]
                        else: 
                            df_ = pd.merge(df_, addon_[["start_time",column_]] , on ="start_time", how="inner" ) 
                        targetWeight_ = targetWeight_  + addonWeight_.set_index("start_time")
                        cnt_ += 1
                except:
                    pass
                
        df_["start_time"] = pd.to_datetime(df_["start_time"])
        df_["total"] = list( df_.set_index("start_time").mean(axis=1))
        
        targetWeight_ =  targetWeight_/cnt_ 
        targetWeight_ = targetWeight_.dropna()
        targetWeight_ = targetWeight_[targetWeight_.index <= date_  ]
        
        #途中の余計なファイルを消す
        for strategy_ in ["A","B","C"]:
            for lag_ in LAG_RANGE:
                if os.path.exists(outputName_+"_"+strategy_+"_lag=" + str(lag_) + "_summary.csv"):
                    os.remove(outputName_+"_"+strategy_+"_lag=" + str(lag_) + "_summary.csv")
                if os.path.exists(outputName_+"_"+strategy_+"_lag=" + str(lag_)+".csv"):
                    os.remove(outputName_+"_"+strategy_+"_lag=" + str(lag_)+".csv")
                if os.path.exists(outputName_ +"_"+strategy_+"_lag=" + str(lag_)+"_weight.csv"):
                    os.remove(outputName_ +"_"+strategy_+"_lag=" + str(lag_)+"_weight.csv")        
        
        #出力のヘッダ調整
        targetWeight_=  targetWeight_.reset_index()
        for ccy_ in ['AUDUSD','CADUSD','CHFUSD','EURUSD','GBPUSD','NZDUSD','JPYUSD']:
            targetWeight_ = targetWeight_.rename(columns = {ccy_: ccy_+"_Fwd"})    
        targetWeight_["NOKUSD_Fwd"] = 0 
        targetWeight_["SEKUSD_Fwd"] = 0 
        targetWeight_["start_time"]  = pd.Series(targetWeight_["start_time"].map(lambda x: x.strftime('%Y/%m/%d')))
        
        df_ = df_[["start_time","total"]]
        df_ = df_[df_["start_time"] <= date_  ]
        
        #既存のファイルがあればくっつけて出力
        NumFiles_ = len(os.listdir(path=DIRECTORY+'test/output/prod')) 
        if NumFiles_ ==0:
            targetWeight_ = targetWeight_.rename(columns = { "start_time":""})    
            targetWeight_.to_csv(DIRECTORY+"test/output/prod/WeightFX"+"_"+ date_.strftime('%Y%m%d') +  ".csv",index=False)
            
            df_.to_csv( DIRECTORY+"test/output/performance/performance"+"_"+ date_.strftime('%Y%m%d') +  ".csv",index=False)
            performanceSummary2(df_, "total" ).to_csv( DIRECTORY+"test/output/performance/performance_summary"+"_"+ date_.strftime('%Y%m%d') +  ".csv")
            
        else:
            #############+++++++++++++++++++++++++++++++++++##########################
            fileList_ =os.listdir(DIRECTORY+"test/output/prod") 
            fileList_ = [ int( x.replace("WeightFX_","").replace(".csv","")) for x in fileList_ if "WeightFX_" in x ]  
            datePre_ = str(np.max(fileList_) ) 
            #############+++++++++++++++++++++++++++++++++++##########################
            
            targetWeightPre_ = pd.read_csv(DIRECTORY+"test/output/prod/WeightFX"+"_"+  datePre_ +  ".csv")
            targetWeightPre_ = targetWeightPre_.rename(columns = { "Unnamed: 0":"start_time"})    
            
            targetWeightOutput_ = pd.concat([targetWeightPre_, targetWeight_])
            targetWeightOutput_ = targetWeightOutput_.drop_duplicates("start_time")
            targetWeightOutput_ = targetWeightOutput_.rename(columns = { "start_time":""}) 
            targetWeightOutput_.to_csv(DIRECTORY+"test/output/prod/WeightFX" +"_"+ date_.strftime('%Y%m%d') +  ".csv",index=False)
            
            dfPre_ = pd.read_csv(DIRECTORY+"test/output/performance/performance"+"_"+ datePre_ +  ".csv")
            dfPre_["start_time"] =  pd.to_datetime(dfPre_["start_time"])
            df_ = pd.concat([dfPre_, df_])
            df_ = df_.drop_duplicates("start_time")
            df_[["start_time","total"]].to_csv( DIRECTORY+"test/output/performance/performance"+"_"+ date_.strftime('%Y%m%d') +  ".csv",index=False)
            performanceSummary2(df_, "total" ).to_csv( DIRECTORY+"test/output/performance/performance_summary"+"_"+ date_.strftime('%Y%m%d') +  ".csv")




def testForProd_NY17NY17_NY17NY17_NY17TK1630_A(LastSimulationPeriod_,date_):
    testForProd(  calculateFactorReturn = makeFactorReturnA_NY17TK1630,calculateFactorReturn2 = makeFactorReturnA_TK1630,
          simulationPeriod_ =range(LastSimulationPeriod_-5,LastSimulationPeriod_) , calculateWeight = makeWeightA_TK1630,
          fileName_ = DIRECTORY+"test/input/input_by_train/train_result_NY17NY17_A", outputName_ = "test/output/prod/test_result_NY17NY17_NY17NY17_NY17TK1630_A",
          strategyName_ = "strategy_A" , date_ = date_)

def testForProd_NY17NY17_NY17NY17_NY17TK1630_B(LastSimulationPeriod_,date_):
    testForProd(  calculateFactorReturn = makeFactorReturnB_NY17TK1630, calculateFactorReturn2 = makeFactorReturnB_TK1630,
          simulationPeriod_ =range(2010,LastSimulationPeriod_) , calculateWeight = makeWeightB_TK1630,
          fileName_ = DIRECTORY+"test/input/input_by_train/train_result_NY17NY17_B",  outputName_ = "test/output/prod/test_result_NY17NY17_NY17NY17_NY17TK1630_B",
          strategyName_ = "strategy_B", date_ = date_ )

def testForProd_NY17NY17_NY17NY17_NY17TK1630_C(LastSimulationPeriod_,date_):
    testForProd(  calculateFactorReturn = makeFactorReturnC_NY17TK1630, calculateFactorReturn2 = makeFactorReturnC_TK1630,
          simulationPeriod_ =range(2010,LastSimulationPeriod_), calculateWeight = makeWeightC_TK1630,
          fileName_ =DIRECTORY+ "test/input/input_by_train/train_result_NY17NY17_C", outputName_ = "test/output/prod/test_result_NY17NY17_NY17NY17_NY17TK1630_C",
          strategyName_ = "strategy_C", date_ = date_ )

def testForProd_NY17NY17_NY17NY17_NY17TK1630_TOTAL(date_):
    
    testForProd(  calculateFactorReturn = None , calculateFactorReturn2 = None ,
          simulationPeriod_ = None  , calculateWeight = None ,
          fileName_ = None ,
          outputName_ = "test/output/prod/test_result_NY17NY17_NY17NY17_NY17TK1630",
          strategyName_ = "total", date_ = date_ )
