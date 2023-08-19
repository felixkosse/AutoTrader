from finta import TA
from autotrader import Order, indicators


class SimpleMACD:
    """Simple MACD Strategy
    
    Rules
    ------
    1. Trade in direction of trend, as per 200EMA.
    2. Entry signal on MACD cross below/above zero line.
    3. Set stop loss at recent price swing.
    4. Target 1.5 take profit.
    """
    
    def __init__(self, parameters, data, instrument):
        """Define all indicators used in the strategy.
        """
        self.name = "Simple MACD Trend Strategy"
        self.params = parameters
        self.instrument = instrument
        
        # Initial feature generation (for plotting only)
        self.generate_features(data)

        # Construct indicators dict for plotting
        self.indicators = {'MACD (12/26/9)': {'type': 'MACD',
                                              'macd': self.MACD.MACD,
                                              'signal': self.MACD.SIGNAL},
                           'EMA (200)': {'type': 'MA',
                                         'data': self.ema}
                        }
        

    def generate_features(self, data):
        """Updates MACD indicators and saves them to the class attributes."""
        # Save data for other functions
        self.data = data

        # 200EMA
        self.ema = TA.EMA(self.data, self.params['ema_period'])

        # MACD
        self.MACD = TA.MACD(self.data, self.params['MACD_fast'], 
                            self.params['MACD_slow'], self.params['MACD_smoothing'])
        self.MACD_CO = indicators.crossover(self.MACD.MACD, self.MACD.SIGNAL)
        self.MACD_CO_vals = indicators.cross_values(self.MACD.MACD, 
                                                    self.MACD.SIGNAL,
                                                    self.MACD_CO)

        # Price swings
        self.swings = indicators.find_swings(self.data)


    def generate_signal(self, data):
        """Define strategy to determine entry signals."""
        # Feature calculation
        self.generate_features(data)

        # Look for entry signals (index -1 for the latest data)
        if self.data.Close.values[-1] > self.ema[-1] and \
            self.MACD_CO[-1] == 1 and \
            self.MACD_CO_vals[-1] < 0:
                # Long entry signal detected! Calculate SL and TP prices
                stop, take = self.generate_exit_levels(signal=1)
                new_order = Order(direction=1, stop_loss=stop, take_profit=take)

        elif self.data.Close.values[-1] < self.ema[-1] and \
            self.MACD_CO[-1] == -1 and \
            self.MACD_CO_vals[-1] > 0:
                # Short entry signal detected! Calculate SL and TP prices
                stop, take = self.generate_exit_levels(signal=-1)
                new_order = Order(direction=-1, stop_loss=stop, take_profit=take)

        else:
            # No trading signal, return a blank Order
            new_order = Order()

        return new_order

    def generate_exit_levels(self, signal):
        """Function to determine stop loss and take profit prices."""
        RR = self.params['RR']
        if signal == 1:
            # Long signal
            stop = self.swings.Lows[-1]
            take = self.data.Close[-1] + RR*(self.data.Close[-1] - stop)
        else:
            # Short signal
            stop = self.swings.Highs[-1]
            take = self.data.Close[-1] - RR*(stop - self.data.Close[-1])
        return stop, take