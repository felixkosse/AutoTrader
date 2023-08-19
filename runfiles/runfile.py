# runfile.py
from autotrader import AutoTrader
from autotrader import AutoPlot

at = AutoTrader()
at.configure(show_plot=True, verbosity=1, feed='yahoo',
             mode='continuous', update_interval='1h') 
at.add_strategy('macd') 
at.backtest(start = '4/4/2023', end = '10/8/2023')
at.virtual_account_config(leverage=30)
at.run()