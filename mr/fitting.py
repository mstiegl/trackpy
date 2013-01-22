# Copyright 2012 Daniel B. Allan
# dallan@pha.jhu.edu, daniel.b.allan@gmail.com
# http://pha.jhu.edu/~dallan
# http://www.danallan.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses>.

from __future__ import division
import numpy as np
import pandas as pd
from pandas import DataFrame, Series
from scipy import optimize, stats

def parse_output(output):
    "Parse the output from scipy.optimize.leastsq, and respond appropriately."
    x, cov_x, infodict, mesg, ier = output
    if not ier in [1, 2, 3, 4]:
        raise Warning, "A solution was not found. Message:\n%s" % mesg
    return x

def fit(data, func, guess_params, log_residual=False, exog_columns=False):
    """Perform a least-sqaured fit on each column of a DataFrame. 

    Parameters
    ----------
    data : a DataFrame or Series indexed by the exogenous ("x") variable.
        Missing values will be ignored.
    func : model function of the form f(x, *params)
    guess_params : a sequence of parameters to be optimized
    log_residual : boolean, default False
        Compute the residual in log space.
    exog_columns : boolean, default False

    Returns
    -------
    best_params : DataFrame with a column of best fit params for each 
        column of data.

    Raises
    ------
    a Warning if the fit fails to converge

    Notes
    -----
    This wraps scipy.optimize.leastsq, which itself wraps an old Fortran 
    MINPACK implementation of the Levenburg-Marquardt algorithm. 
    """
    pd.set_option('use_inf_as_null', True)
    data = data.dropna()
    data_index = Series(data.index.values, index=data.index, dtype=np.float64)
    # If the guess_params have an index, retain it.
    try:
        if not issubclass(type(guess_params.index), pd.core.index.Index):
            raise TypeError
        param_index = guess_params.index
    except:
        param_index = np.arange(len(guess_params))
    fits = DataFrame(index=param_index)
    data = DataFrame(data) # Maybe convert Series to DataFrame.
    for col in data:
        if not exog_columns:
            def err(params):
                f = data_index.apply(lambda x: func(x, *params))
                if log_residual:
                    e = (np.log(data[col]) - np.log(f)).fillna(0)
                else:
                    e = (data[col] - f).fillna(0)
                return e.values
        else:
            def err(params):
                f = data[col].apply(lambda x: func(x, *params))
                if log_residual:
                    e = (np.log(data_index) - np.log(f)).fillna(0) 
                else:
                    e = (data_index - f).fillna(0)
                return e.values
        output = optimize.leastsq(err, guess_params, full_output=True)
        best_params = parse_output(output)
        fits[col] = Series(best_params, index=param_index)
    pd.reset_option('use_inf_as_null')
    return fits.T # a column for each fit parameter 


def fit_powerlaw(data):
    """Fit a powerlaw by doing a linear regression in log space."""
    data = DataFrame(data)
    fits = []
    for col in data:
        slope, intercept, r, p, stderr = \
            stats.linregress(data.index.values, data[col].values)
        fits.append(Series([slope, np.exp(intercept)], index=['A', 'n']))
    return pd.concat(fits, axis=1, keys=data.columns)

def bound_fit(data, func, guess_params, transform, untransform, 
              log_residual=False, exog_columns=False):
    """Perform a least-sqaured fit on each column of a DataFrame. 

    Parameters
    ----------
    data : a DataFrame or Series indexed by the exogenous ("x") variable.
        Missing values will be ignored.
    func : model function of the form f(x, *params)
    guess_params : a sequence of parameters to be optimized
    transform : function that transforms open-ended parameters on (-inf, inf) 
        into bounded, real variables
    untransform : function that transforms bounded, real variables into
       open-ended parameters on (-inf, inf)
    log_residual : boolean, default False
        Compute the residual in log space.
    exog_columns : boolean, default False

    Returns
    -------
    best_params : DataFrame with a column of best fit params for each 
        column of data.

    Raises
    ------
    a Warning if the fit fails to converge

    Notes
    -----
    This wraps scipy.optimize.leastsq, which itself wraps an old Fortran 
    MINPACK implementation of the Levenburg-Marquardt algorithm. 
    """
    pd.set_option('use_inf_as_null', True)
    data = data.dropna()
    data_index = Series(data.index.values, index=data.index, dtype=np.float64)
    # If the guess_params have an index, retain it.
    try:
        if not issubclass(type(guess_params.index), pd.core.index.Index):
            raise TypeError
        param_index = guess_params.index
    except:
        param_index = np.arange(len(guess_params))
    fits = DataFrame(index=param_index)
    data = DataFrame(data) # Maybe convert Series to DataFrame.
    for col in data:
        ut_guess_params = untransform(data[col], *guess_params)
        if not exog_columns:
            def err(params):
                f = data_index.apply(lambda x: func(x, *params))
                if log_residual:
                    e = (np.log(data[col]) - np.log(f))
                    e.fillna(2*e.mean(), inplace=True)
                else:
                    e = (data[col] - f)
                return e.values
        else:
            def err(params):
                f = data[col].apply(lambda x: func(x, *params))
                if log_residual:
                    e = (np.log(data_index) - np.log(f))
                    e.fillna(2*e.mean(), inplace=True) 
                else:
                    e = (data_index - f)
                return e.values
        output = optimize.leastsq(err, ut_guess_params, full_output=True)
        ut_best_params = parse_output(output)
        t_best_params = transform(data[col], *ut_best_params)
        fits[col] = Series(t_best_params, index=param_index)
    pd.reset_option('use_inf_as_null')
    return fits.T # a column for each fit parameter 
