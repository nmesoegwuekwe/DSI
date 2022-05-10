"""
Utility functions for forecasting. Includes:
    - Functions to create supervised learning set (for ID horizon forecasts)
    - Function to create historical lagged predictors based on Partial Autocorrelation Function
    - Evaluation functions for point and probabilistic predictions
"""
import pandas as pd
import numpy as np
from scipy.ndimage.interpolation import shift
from statsmodels.tsa.stattools import pacf
import matplotlib.pyplot as plt
from sklearn.inspection import permutation_importance

############################## Preprocessing, data manipulation, preliminary analysis

def clean_entsoe_data(df, freq, impute = False):
    ''' Data to fill missing values and remove duplicates for daylightsavings
    Not needed if everything is in UTC'''
    #freq = number of observations in an hour (1 for hourly, 4 for 15-min)
    types = (df.dtypes == 'float64').values + (df.dtypes == 'int64').values
    ind = np.where(types)[0]    #Quantitative indexes           
    if impute is False:
        #Simply replace (works for quant+categorical values)
        #Check for NaNs
        if any(df.iloc[:,ind[0]].isnull()):
            print('Index of NaNs \n', df.index[df.iloc[:,ind[0]].isnull()] )
            NaN_ind = np.where(df.iloc[:,ind[0]].isnull())[0]
    
            #Replace NaNs
            df.iloc[NaN_ind] = df.iloc[NaN_ind-freq].values

        #Check for duplicates and average them
        if any(df.index.duplicated()):
            print('Duplicated Indices \n', df.index[df.index.duplicated()])
            df  = df.loc[~df.index.duplicated(keep='first')]    
    else:
        #Impute missing values (only for quantitative)
        #Check for NaNs
        if any(df.iloc[:,ind[0]].isnull()):
            print('Index of NaNs \n', df.index[df.iloc[:,ind[0]].isnull()] )
            NaN_ind = np.where(df.iloc[:,ind[0]].isnull())[0]
            #Linear Interpolation (for quantitative values only)
            for i in ind:    
                y_0 = df.iloc[NaN_ind[0]-1, i]   #Start
                y_t = df.iloc[NaN_ind[-1]+1, i]  #Stop
                dx = freq + 1
                dy = (y_0-y_t)/dx
                df.iloc[NaN_ind,i] = np.arange(1,dx)*dy+y_0
        #Check for duplicates and average them
        if any(df.index.duplicated()):
            print('Duplicated Indices \n', df.index[df.index.duplicated()])
            dupl_ind = np.where(df.index.duplicated())[0]   #Index of duplicated values
            ave = (df.iloc[dupl_ind,types] + df.iloc[dupl_ind-freq,types])/2    #Average value
            df.iloc[dupl_ind] = ave
            df  = df.loc[~df .index.duplicated(keep='last')]
    return df

def feat_imp(model, testX, testY, number_feat = 10):
    ''' Estimates feature importance using the permutation importance, saves output, plots results'''
    
    result = permutation_importance(model, testX, testY, n_repeats=25, random_state=2, n_jobs=-1)
    
    forest_importances = pd.Series(result.importances_mean, index=testX.columns)
    n_feat = number_feat
    index = forest_importances.values.argsort()[::-1]
    
    fig, ax = plt.subplots()
    forest_importances[index[:n_feat]].plot.barh(xerr=result.importances_std[index[:n_feat]], ax=ax)
    ax.set_title("Feature importances using permutation on full model")
    ax.set_ylabel("Mean Accuracy Decrease")
    fig.tight_layout()
    plt.show()
    
def create_supervised(data, look_back, n_seq, train_split, overlap = True):
    '''Function that creates supervised learning set at t = train_split
    X = [X_t, X_t-1, .., X_t-look_back]
    Y = [Y_t+1, Y_t+2, .., Y_t+n_seq]
    If overlap == True: sets overlap, last values of trainY are first values of validX and split is made excactly @ t = train_split
    if overlap == False: sets don't overlap, split is actually made at train_split+look_back
    First is more easy to handle and appropriate for rolling estimation, second more theoretical sound'''
    back = []
    forward = []
    if (isinstance(data, pd.Series)):
        #Lagged Values
        for i in range(look_back+1):
            back.append(data.shift(i))        
    else:
        for i in range(look_back+1):
            back.append(shift(data[:,0], i, cval=np.NaN))        
    X = np.asarray(back).T
    X = X[~np.isnan(X).any(axis=1)]            
    #Values to forecast/ Lead values
    for i in range(n_seq+1):
        forward.append(shift(X[:,0], -i, cval=np.NaN))
    Y = np.asarray(forward).T[:,1:]
    Y = Y[~np.isnan(Y).any(axis=1)]
    X = X[:len(Y),:]
    trainX = X[:train_split]
    trainY = Y[:train_split]
    if overlap:
        testX = X[(train_split-look_back-1) :]
        testY = Y[(train_split-look_back-1) :]    
    else:
        testX = X[train_split:]
        testY = Y[train_split:]            
    return trainX, trainY, testX, testY

def supervised_set(df, var_name, lag, lead, operational_lag = 0):
    '''Create supervised learning set as follows: X = [X_t, X_t-1, .., X_t-look_back], Y = [Y_t+1, Y_t+2, .., Y_t+n_seq]
    To be used for rolling horizon forecasts (e.g., intraday forecasting)
    df = pandas DataFrame
    var_name = column name, str
    lag = number of historical lags, int
    lead = forecast horizon/ lead time, int
    operational_lag = operational delay/ lag in publishing data, int'''
    
    lag_pred = df[var_name].copy().to_frame()
    lead_pred =  df[var_name].copy().to_frame()

    for lag_t in range(1, lag + 1):
        lag_pred[var_name +'_lag_' + str(lag_t)] = df[var_name].shift(lag_t).dropna()

    for lead_t in range(1, lead + 1):
        lead_pred[var_name +'_lead_' + str(lead_t)] = df[var_name].shift(-lead_t).dropna()

    lag_pred = lag_pred[lag:-lead]
    lead_pred = lead_pred[lag:-lead].drop(var_name, axis = 1)
    
    if operational_lag>0:
        lag_pred = lag_pred.iloc[:,operational_lag:]
        
    return lag_pred, lead_pred    

def lagged_predictors_pd(df, col_name, freq = 1, d = 200, operational_lag = 0, thres = .05, plot = True, da_auction = True):
    ''' Evaluates Partial Autocorrelation function, creates lagged predictors for selected column, updates dataframe
        Mainly to be used for batch forecasts in DA horizon.
    Inputs:
        df: dataframe, col_name: target variable, freq: 1 if hourly observations, 
        d: maximum lags to evaluate, operational_lag: the real-time delay in historical lags, 
        thres: threshold for selection, plot: whether to plot the PACF function
        da_auction: denotes batch DA forecasting (DA prices, Reserve Capacity prices). In this case, operational_lag = 24.
    Outputs: Returns updated df with new columns and list of names for the new columns'''
    
    PACF = pacf(df[col_name], nlags = d)
    if plot==True:
        plt.plot(PACF)
        plt.show()
    Lags = np.argwhere(abs(PACF) > thres) - 1
    
    if da_auction:
        starting_point = (int(freq*24)-1) + operational_lag
    else:
        starting_point = operational_lag
        
    Lags = Lags[Lags> starting_point]
    print('Selected Lags: ', Lags)
    name = col_name+'_'
    name_list = []
    for lag in Lags:
        #temp_name = name+str(int(1//freq)*lag)
        temp_name = name+str(lag)
        df[temp_name] = df[col_name].shift(lag)
        name_list.append(temp_name)
    return df, name_list

def crosscorr(datax, datay, lag=0):
    """ Lag-N cross correlation between x and y. 
    Inputs:
        -lag : int, default 0
        -datax, datay : pandas.Series objects of equal length
    Output: crosscorr : float
    """
    return [datax.corr(datay.shift(l)) for l in range(lag)]


######################### Forecast evaluation
#!!!!!!!
'''2-D arrays used throughout'''

def eval_point_pred(predictions, actual, digits = None):
    ''' Returns point forecast metrics: MAPE, RMSE, MAE '''
    assert predictions.shape == actual.shape, "Shape missmatch"
    
    mape = np.mean(abs( (predictions-actual)/actual) )
    rmse = np.sqrt( np.mean(np.square( predictions-actual) ) )
    mae = np.mean(abs(predictions-actual))
    if digits is None:
        return mape,rmse, mae
    else: 
        return round(mape, digits), round(rmse, digits), round(mae, digits)
    
def pinball(prediction, target, quantiles):
    ''' Estimates Pinball loss '''
    num_quant = len(quantiles)
    pinball_loss = np.maximum( (np.tile(target, (1,num_quant)) - prediction)*quantiles,(prediction - np.tile(target , (1,num_quant) ))*(1-quantiles))
    return pinball_loss  

def CRPS(target, quant_pred, quantiles, digits = None):
    ''' Estimates CRPS (Needs check) '''
    n = len(quantiles)
    #Conditional prob
    p = 1. * np.arange(n) / (n - 1)
    #Heaviside function
    H = quant_pred > target 
    if digits == None:
        return np.trapz( (H-p)**2, quant_pred).mean()
    else:
        return round(np.trapz( (H-p)**2, quant_pred).mean(), digits)

def pit_eval(target, quant_pred, quantiles, plot = False, nbins = 20):
    '''Evaluates Probability Integral Transformation
        returns np.array and plots histogram'''
    #n = len(target)
    #y = np.arange(1, n+1) / n
    y = quantiles
    PIT = [ y[np.where(quant_pred[i,:] >= target[i])[0][0]] if any(quant_pred[i,:] >= target[i]) else 1 for i in range(len(target))]
    PIT = np.asarray(PIT).reshape(len(PIT))
    if plot:
        plt.hist(PIT, bins = nbins)
        plt.show()
    return PIT

def reliability_plot(target, pred, quantiles, boot = 100, label = None, plot = True):
    ''' Reliability plot with error consistency bars '''
    cbands = []
    for j in range(boot):
        #Surgate Observations
        Z = np.random.uniform(0,1,len(pred))
        
        Ind = 1* (Z.reshape(-1,1) < np.tile(quantiles,(len(pred),1)))
        cbands.append(np.mean(Ind, axis = 0))
    
    ave_proportion = np.mean(1*(pred>target), axis = 0)
    cbands = 100*np.sort( np.array(cbands), axis = 0)
    lower = int( .05*boot)
    upper = int( .95*boot)
 
    ave_proportion = np.mean(1*(pred>target), axis = 0)
    if plot:
        plt.vlines(100*quantiles, cbands[lower,:], cbands[upper,:])
        plt.plot(100*quantiles,100*ave_proportion, '-*')
        plt.plot(100*quantiles,100*quantiles, '--')
        plt.legend(['Observed', 'Target'])
        plt.show()
    return

def brier_score(predictions, actual, digits = None):
    ''' Evaluates Brier Score '''
    if digits == None:
        return np.mean(np.square(predictions-actual))
    else:
        return round(np.mean(np.square(predictions-actual)), digits)
    
def PINAW_plot(target, pred, quantiles, plot = True):
    '''Plots Prediction Interval Normalized Average Width (PINAW)/ sharpness evaluation
    Makes sense only if there are several models to compare '''
    
    PINAW = np.zeros(( int(len(quantiles)/2)))
    PIs = []
    for j in range(int(len(quantiles)/2)):
        lower = pred[:,j]
        upper = pred[:,-1-j]
        PINAW[j] = 100*np.mean(upper - lower)/(target.max()-target.min())
        PIs.append(quantiles[-1-j] - quantiles[j])
    plt.figure(dpi = 600, facecolor='w', edgecolor='k')
    plt.plot(PIs[::-1], PINAW.T[::-1])
    plt.ylabel('[%]')
    plt.xlabel('Prediction Intervals [%]')
    plt.title('Prediction Interval Normalized Average Width')
    plt.show()

def energy_score(target, pred_scenarios, step):
    '''Estimates Energy Score of trajectories
        step: length of trajectory vector/ forecast horizon'''
    ES = []
    n_scen = pred_scenarios.shape[1]

    for i in range(step, len(target), step):
        dist = np.linalg.norm(pred_scenarios[i-step:i] - target[i-step:i], axis = 0).mean()
        t = 0
        for j in range(n_scen):
            t = t + np.linalg.norm(pred_scenarios[i-step:i, j:j+1] - pred_scenarios[i-step:i],  axis = 0).sum()
        t = t/(2*n_scen**2)
        ES.append(dist - t)
    return(np.array(ES).mean())

################################### Other functions
def find_freq(freq_str):
    if (freq_str == '1h') or (freq_str == 'H') :
        return 1
    elif freq_str == '15min':
        return 4
    elif freq_str == '4h':
        return 1/4
    else:
        print('Check time series frequency')
        return

def VaR(data, quant = .05, digits = 3):
    ''' Estimates Value at Risk at quant level'''
    if digits is None:
        return np.quantile(data, q = quant)
    else:
        return round(np.quantile(data, q = quant), digits)

def CVaR(data, quant = .05, digits = 3):
    ''' Estimates Conditional Value at Risk at quant level'''
    VaR = np.quantile(data, q = quant)
    if digits is None:
        return data[data<=VaR].mean()
    else:
        return round(data[data<=VaR].mean(), digits)
    