#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoPlot Cleanup
"""

import pandas as pd
import numpy as np
import os

# Bokeh
from bokeh.models.annotations import Title
from bokeh.plotting import figure, output_file, show, save
from bokeh.models import (
    CustomJS,
    ColumnDataSource,
    HoverTool,
    CrosshairTool
)
from bokeh.layouts import gridplot, layout
from bokeh.transform import factor_cmap, cumsum
from bokeh.palettes import Category20c
from math import pi


class AutoPlot():
    '''
    AutoPlot.
    
    Attributes
    ----------
    data : df
        The base data.
        

    Methods
    -------
    __init__(data):
        Initialise AutoPlot with the lowest timeframe data being used for 
        plotting.
    
    add_tool(tool_name):
        Add bokeh tool to plot.
    
    '''
    def __init__(self, data):
        self.max_indis_over     = 3
        self.max_indis_below    = 2
        self._modified_data     = None
        self.fig_tools          = "pan,wheel_zoom,box_zoom,undo,redo,reset,save,crosshair"
        self.ohlc_height        = 400
        self.ohlc_width         = 800
        self.top_fig_height     = 150
        self.bottom_fig_height  = 150
        # self.total_height       = 1000
        self.plot_validation_balance = True
        
        # Modify data index
        self.data               = self._reindex_data(data)
        
        # Load JavaScript code for auto-scaling 
        with open(os.path.join(os.path.dirname(__file__), 'lib/autoscale.js'),
                  encoding = 'utf-8') as _f:
            self._autoscale_code = _f.read()
        
        
    def add_tool(self, tool_name):
        '''
        Adds a tool to the plot. 
        
            Parameters:
                tool_name (str): name of tool to add (see Bokeh documentation).
        '''
        
        self.fig_tools          = self.fig_tools + "," + tool_name
    
    
    def _reindex_data(self, data):
        '''
        Resets index of data to obtain integer indexing.
        '''
        
        modified_data           = data.copy()
        modified_data['date']   = modified_data.index
        modified_data           = modified_data.reset_index(drop = True)
        modified_data['data_index'] = modified_data.index
        
        return modified_data
    
    
    ''' ------------------- FIGURE MANAGEMENT METHODS --------------------- '''
    def plot(self, backtest_dict=None, cumulative_PL=None, indicators=None, 
             instrument=None, show_fig=True):
        ''' 
        Creates chart of price data and indicators. 
        '''
        
        # Preparation ------------------------------------------------------- #
        if backtest_dict is None:
            if instrument is not None:
                title_string = "AutoTrader IndiView - {}".format(instrument)
            else:
                title_string = "AutoTrader IndiView"
            
            output_file("indiview-chart.html",
                        title = title_string)
            
        else:
            if instrument is None:
                instrument = backtest_dict['instrument']
            
            title_string = "Backtest chart for {} ({} candles)".format(instrument, 
                                                                       backtest_dict['interval'])
            output_file("{}-backtest-chart.html".format(instrument),
                        title = "AutoTrader Backtest Results - {}".format(instrument))
        
        source = ColumnDataSource(self.data)
        source.add((self.data.Close >= self.data.Open).values.astype(np.uint8).astype(str),
                   'change')
        
        
        # Plotting ---------------------------------------------------------- #
        # OHLC candlestick plot
        candle_plot = self._plot_candles(source)
        
        top_figs = []
        bottom_figs = []
        
        if backtest_dict is not None:
            
            NAV             = backtest_dict['NAV']
            trade_summary   = backtest_dict['trade_summary']
            indicators      = backtest_dict['indicators']
            open_trades     = backtest_dict['open_trades']
            cancelled_trades = backtest_dict['cancelled_trades']
            
            # Top plots
            top_fig = self._plot_line(NAV, candle_plot, new_fig=True, 
                                      legend_label='Net Asset Value', 
                                      hover_name='NAV')
            if cumulative_PL is not None:
                self._plot_line(cumulative_PL, top_fig, 
                                legend_label='Cumulative P/L', 
                                hover_name='P/L')
            top_figs.append(top_fig)
            
            # Overlay trades 
            self._plot_trade_history(trade_summary, candle_plot)
            if len(cancelled_trades) > 0:
                self._plot_trade_history(cancelled_trades, candle_plot, cancelled_summary=True)
            if len(open_trades) > 0:
                self._plot_trade_history(open_trades, candle_plot, open_summary=True)
        
        # Indicators
        if indicators is not None:
            bottom_figs = self._plot_indicators(indicators, candle_plot)
        
        
        # Compile plots for final figure ------------------------------------ #
        # Auto-scale y-axis of candlestick chart - TODO - improve
        autoscale_args      = dict(y_range  = candle_plot.y_range, 
                                   source   = source)
        candle_plot.x_range.js_on_change('end', CustomJS(args = autoscale_args, 
                                                         code = self._autoscale_code))
        
        plots               = top_figs + [candle_plot] + bottom_figs
        linked_crosshair    = CrosshairTool(dimensions='both')
        
        titled  = 0
        t       = Title()
        t.text  = title_string
        for plot in plots:
            if plot is not None:
                plot.xaxis.major_label_overrides = {
                    i: date.strftime('%b %d') for i, date in enumerate(pd.to_datetime(self.data["date"]))
                }
                plot.xaxis.bounds   = (0, self.data.index[-1])
                plot.sizing_mode    = 'stretch_width'
                
                if titled == 0:
                    plot.title = t
                    titled = 1
                
                if plot.legend:
                    plot.legend.visible             = True
                    plot.legend.location            = 'top_left'
                    plot.legend.border_line_width   = 1
                    plot.legend.border_line_color   = '#333333'
                    plot.legend.padding             = 5
                    plot.legend.spacing             = 0
                    plot.legend.margin              = 0
                    plot.legend.label_text_font_size = '8pt'
                    plot.legend.click_policy        = "hide"
                
                plot.add_tools(linked_crosshair)
                plot.min_border_left    = 0
                plot.min_border_top     = 3
                plot.min_border_bottom  = 6
                plot.min_border_right   = 10
                plot.outline_line_color = 'black'
    
        # Construct final figure
        fig                 = gridplot(plots, 
                                       ncols            = 1, 
                                       toolbar_location = 'right',
                                       toolbar_options  = dict(logo = None), 
                                       merge_tools      = True
                                       )
        fig.sizing_mode     = 'stretch_width'
        
        if show_fig:
            show(fig)
        else:
            save(fig)
    
    
    def _plot_multibot_backtest(self, multibot_backtest_results, NAV, cpl_dict):
        ''' 
        Creates multi-bot backtest figure. 
        
            Parameters:
                multibot_backtest_results (df): dataframe of bot backtest results.
                
                NAV (list): Net asset value.
                
                cpl_dict (dict): cumulative PL of each bot.
        '''
        
        # TODO - merge this into self.plot method?
        # First, clean up individual plots (pie, etc) into new methods
        
        # Preparation ----------------------------------- #
        output_file("candlestick.html",
                    title = "AutoTrader Multi-Bot Backtest Results")
        
        linked_crosshair = CrosshairTool(dimensions='both')
        if len(multibot_backtest_results) < 3:
            multibot_backtest_results['color'] = Category20c[3][0:len(multibot_backtest_results)]
        else:
            multibot_backtest_results['color'] = Category20c[len(multibot_backtest_results)]
            
        MBR = ColumnDataSource(multibot_backtest_results)
        
        # ----------------------- Account Balance -------------------------- #
        navfig = figure(plot_width = self.ohlc_width,
                        plot_height = self.top_fig_height,
                        title = None,
                        active_drag = 'pan',
                        active_scroll = 'wheel_zoom')
        
        # Add glyphs
        navfig.line(self.data.index, 
                    NAV, 
                    line_color = 'black',
                    legend_label = 'Backtest Net Asset Value')
        
        navfig.xaxis.major_label_overrides = {
                    i: date.strftime('%b %d') for i, date in enumerate(pd.to_datetime(self._modified_data["date"]))
                }
        navfig.xaxis.bounds = (0, self._modified_data.index[-1])
        navfig.sizing_mode = 'stretch_width'
        navfig.legend.location = 'top_left'
        navfig.legend.border_line_width   = 1
        navfig.legend.border_line_color   = '#333333'
        navfig.legend.padding             = 5
        navfig.legend.spacing             = 0
        navfig.legend.margin              = 0
        navfig.legend.label_text_font_size = '8pt'
        navfig.add_tools(linked_crosshair)
        
        # ----------------------- Win rate bar chart ----------------------- #
        instruments = multibot_backtest_results.index.values
        
        winrate = figure(x_range = instruments,
                         title = "Bot win rate (%)",
                         toolbar_location = None,
                         tools = 'hover',
                         tooltips = "@index: @win_rate%",
                         plot_height = 250)
        
        winrate.vbar(x = 'index', 
                     top = 'win_rate',
                     width = 0.9,
                     color = 'color',
                     source = MBR)
        
        winrate.sizing_mode = 'stretch_width'
        
        
        # ----------------- Pie chart of trades per bot --------------------- #
        pie_data = pd.Series(multibot_backtest_results.no_trades).reset_index(name='value').rename(columns={'index':'instrument'})
        pie_data['angle'] = pie_data['value']/pie_data['value'].sum() * 2*pi
        if len(multibot_backtest_results) < 3:
            pie_data['color'] = Category20c[3][0:len(multibot_backtest_results)]
        else:
            pie_data['color'] = Category20c[len(multibot_backtest_results)]

        pie = figure(title = "Trade distribution", 
                     toolbar_location = None,
                     tools = "hover", 
                     tooltips="@instrument: @value",
                     x_range=(-1, 1),
                     y_range=(0.0, 2.0),
                     plot_height = 250)
        
        pie.wedge(x=0, y=1, radius=0.3,
                  start_angle=cumsum('angle', include_zero=True), 
                  end_angle=cumsum('angle'),
                  line_color="white", 
                  fill_color='color',
                  legend_field='instrument',
                  source=pie_data)
        
        pie.axis.axis_label=None
        pie.axis.visible=False
        pie.grid.grid_line_color = None
        pie.sizing_mode = 'stretch_width'
        pie.legend.location = "top_left"
        pie.legend.border_line_width   = 1
        pie.legend.border_line_color   = '#333333'
        pie.legend.padding             = 5
        pie.legend.spacing             = 0
        pie.legend.margin              = 0
        pie.legend.label_text_font_size = '8pt'
        
        # --------------- Bar plot for avg/max win/loss -------------------- #
        win_metrics = ['Average Win', 'Max. Win']
        lose_metrics = ['Average Loss', 'Max. Loss']
        
        abs_max_loss = -1.2*max(multibot_backtest_results.max_loss)
        abs_max_win = 1.2*max(multibot_backtest_results.max_win)
        
        pldata = {'instruments': instruments,
                'Average Win': multibot_backtest_results.avg_win.values,
                'Max. Win': multibot_backtest_results.max_win.values - 
                            multibot_backtest_results.avg_win.values,
                'Average Loss': -multibot_backtest_results.avg_loss.values,
                'Max. Loss': multibot_backtest_results.avg_loss.values - 
                             multibot_backtest_results.max_loss.values}
        
        TOOLTIPS = [
                    ("Instrument:", "@instruments"),
                    ("Max win", "@{Max. Win}"),
                    ("Avg. win", "@{Average Win}"),
                    ("Max Loss", "@{Max. Loss}"),
                    ("Avg. loss", "@{Average Loss}"),
                    ]
        
        plbars = figure(x_range=instruments,
                        y_range=(abs_max_loss, abs_max_win),
                        title="Win/Loss breakdown",
                        toolbar_location=None,
                        tools = "hover",
                        tooltips = TOOLTIPS,
                        plot_height = 250)

        plbars.vbar_stack(win_metrics,
                     x='instruments',
                     width = 0.9,
                     color = ('#008000', '#FFFFFF'),
                     line_color='black',
                     source = ColumnDataSource(pldata),
                     legend_label = ["%s" % x for x in win_metrics])

        plbars.vbar_stack(lose_metrics,
                     x = 'instruments',
                     width = 0.9,
                     color = ('#ff0000' , '#FFFFFF'),
                     line_color='black',
                     source = ColumnDataSource(pldata),
                     legend_label = ["%s" % x for x in lose_metrics])
        
        plbars.x_range.range_padding = 0.1
        plbars.ygrid.grid_line_color = None
        plbars.legend.location = "bottom_center"
        plbars.legend.border_line_width   = 1
        plbars.legend.border_line_color   = '#333333'
        plbars.legend.padding             = 5
        plbars.legend.spacing             = 0
        plbars.legend.margin              = 0
        plbars.legend.label_text_font_size = '8pt'
        plbars.axis.minor_tick_line_color = None
        plbars.outline_line_color = None
        plbars.sizing_mode = 'stretch_width'
    
    
        # --------------------- Cumulative PL ------------------------------ #
        cplfig = figure(plot_width = navfig.plot_width,
                        plot_height = self.top_fig_height,
                        title = None,
                        active_drag = 'pan',
                        active_scroll = 'wheel_zoom',
                        x_range = navfig.x_range)
        
        # self.data['data_index'] = self.data.reset_index(drop=True).index
        
        if len(multibot_backtest_results) < 3:
            colors = Category20c[3][0:len(multibot_backtest_results)]
        else:
            colors = Category20c[len(multibot_backtest_results)]
        
        
        for ix, instrument in enumerate(cpl_dict):
            cpldata = cpl_dict[instrument].copy().to_frame()
            cpldata['date'] = cpldata.index
            cpldata         = cpldata.reset_index(drop = True)
            
            cpldata = pd.merge(self.data, cpldata, left_on='date', right_on='date')
            
            cplfig.line(cpldata.data_index.values,
                        cpldata.Profit.values,
                        legend_label = "{}".format(instrument),
                        line_color = colors[ix])
        
        cplfig.legend.location = 'top_left'
        cplfig.legend.border_line_width   = 1
        cplfig.legend.border_line_color   = '#333333'
        cplfig.legend.padding             = 5
        cplfig.legend.spacing             = 0
        cplfig.legend.margin              = 0
        cplfig.legend.label_text_font_size = '8pt'
        cplfig.sizing_mode = 'stretch_width'
        cplfig.add_tools(linked_crosshair)
        
        cplfig.xaxis.major_label_overrides = {
                    i: date.strftime('%b %d') for i, date in enumerate(pd.to_datetime(self._modified_data["date"]))
                }
        cplfig.xaxis.bounds   = (0, self.data.index[-1])
        
        # -------------------- Construct final figure ---------------------- #     
        final_fig = layout([  
                                   [navfig],
                            [winrate, pie, plbars],
                                   [cplfig]
                        ])
        final_fig.sizing_mode = 'scale_width'
        show(final_fig)
    
        
    def _plot_indicators(self, indicators, linked_fig):
        ''' 
        Plots indicators based on indicator type. If inidcator type is 
        "over", it will be plotted on top of linked_fig. If indicator type is 
        "below", it will be plotted on a new figure below the OHLC chart.
        '''
        
        x_range   = self.data.index
        
        plot_type = {'MACD'        : 'below',
                     'MA'          : 'over',
                     'RSI'         : 'below',
                     'STOCHASTIC'  : 'below',
                     'Heikin-Ashi' : 'below',
                     'Supertrend'  : 'over',
                     'Swings'      : 'over',
                     'Engulfing'   : 'below',
                     'Crossover'   : 'below',
                     'over'        : 'over',
                     'below'       : 'below'}
        
        # Plot indicators
        indis_over              = 0
        indis_below             = 0
        bottom_figs             = []
        colours                 = ['red', 'blue', 'orange', 'green']
        
        for indicator in indicators:
            indi_type = indicators[indicator]['type']
            
            if indi_type in plot_type:
                # The indicator plot type is recognised
                if plot_type[indi_type] == 'over' and indis_over < self.max_indis_over:
                    if indi_type == 'Supertrend':
                        self._plot_supertrend(indicators[indicator]['data'], 
                                              linked_fig)
                        
                        indis_over     += 1 # Count as 2 indicators
                    elif indi_type == 'Swings':
                        self._plot_swings(indicators[indicator]['data'], 
                                          linked_fig)
                    else:
                        # Generic overlay indicator - plot as line
                        linked_fig.line(x_range, 
                                        indicators[indicator]['data'], 
                                        line_width = 1.5, 
                                        legend_label = indicator,
                                        line_color = colours[indis_over])
                    indis_over     += 1
                    
                elif plot_type[indi_type] == 'below' and indis_below < self.max_indis_below:
                    if indi_type == 'MACD':
                        new_fig     = self._plot_macd(x_range,
                                                      indicators[indicator], 
                                                      linked_fig)
                        new_fig.title = indicator
                    
                    elif indi_type == 'Heikin-Ashi':
                        
                        HA_data     = self._reindex_data(indicators[indicator]['data'])
                        source      = ColumnDataSource(HA_data)
                        source.add((HA_data.Close >= HA_data.Open).values.astype(np.uint8).astype(str),
                                   'change')
                        new_fig     = self._plot_candles(source)
                        new_fig.x_range = linked_fig.x_range
                        new_fig.y_range = linked_fig.y_range
                        new_fig.title = indicator
                        indis_below   += self.max_indis_below # To block any other new plots below.
                    
                    else:
                        new_fig = figure(plot_width     = linked_fig.plot_width,
                                         plot_height    = 130,
                                         title          = None,
                                         tools          = linked_fig.tools,
                                         active_drag    = linked_fig.tools[0],
                                         active_scroll  = linked_fig.tools[1],
                                         x_range        = linked_fig.x_range)
                        
                        # Add glyphs
                        new_fig.line(x_range, 
                                     indicators[indicator]['data'],
                                     line_color         = 'black', 
                                     legend_label       = indicator)
                        
                    indis_below    += 1
                    bottom_figs.append(new_fig)
            else:
                # The indicator plot type is not recognised - plotting on new fig
                if indis_below < self.max_indis_below:
                    print("Indicator type '{}' not recognised in AutoPlot.".format(indi_type))
                    new_fig = self._plot_line(indicators[indicator]['data'], 
                                              linked_fig, new_fig=True, 
                                              legend_label=indicator, 
                                              hover_name=indicator)
                    
                    indis_below    += 1
                    bottom_figs.append(new_fig)
                
        return bottom_figs
    
    
    def _plot_line(self, plot_data, linked_fig, new_fig=False, fig_height=150,
                   fig_title=None, legend_label=None, hover_name=None):
        '''
        Generic method to plot data as a line.
        '''
        
        # Initiate figure
        if new_fig:
            fig = figure(plot_width     = linked_fig.plot_width,
                         plot_height    = fig_height,
                         title          = fig_title,
                         tools          = self.fig_tools,
                         active_drag    = 'pan',
                         active_scroll  = 'wheel_zoom',
                         x_range        = linked_fig.x_range)
        else:
            fig = linked_fig
        
        # Add glyphs
        source = ColumnDataSource(self.data)
        source.add(plot_data, 'plot_data')
        fig.line('data_index', 'plot_data', 
                 line_color         = 'black',
                 legend_label       = legend_label,
                 source             = source)
        
        if hover_name is None:
            hover_name = 'Data'
        
        fig_hovertool = HoverTool(tooltips = [("Date", "@date{%b %d %H:%M}"),
                                              (hover_name, "$@{plot_data}{%0.2f}")
                                              ], 
                                  formatters={'@{plot_data}' : 'printf',
                                              '@date' : 'datetime'},
                                  mode = 'vline')
        
        fig.add_tools(fig_hovertool)
        
        return fig
    
    
    ''' ------------------------ OVERLAY PLOTTING ------------------------- '''
    
    def _plot_candles(self, source):
        ''' Plots OHLC data onto new figure. '''
        bull_colour             = "#D5E1DD"
        bear_colour             = "#F2583E"
        candle_colours          = [bear_colour, bull_colour]
        colour_map              = factor_cmap('change', candle_colours, ['0', '1'])
        
        candle_tooltips         = [("Date", "@date{%b %d %H:%M:%S}"),
                                   ("Open", "@Open{0.0000}"), 
                                   ("High", "@High{0.0000}"), 
                                   ("Low", "@Low{0.0000}"),
                                   ("Close", "@Close{0.0000}")]
    
        candle_plot = figure(plot_width     = self.ohlc_width, 
                             plot_height    = self.ohlc_height, 
                             tools          = self.fig_tools,
                             active_drag    = 'pan',
                             active_scroll  = 'wheel_zoom')
    
        candle_plot.segment('index', 'High',
                            'index', 'Low', 
                            color   = "black",
                            source  = source)
        candles = candle_plot.vbar('index', 0.7, 'Open', 'Close', 
                                   source       = source,
                                   line_color   = "black", 
                                   fill_color   = colour_map)
        
        candle_hovertool = HoverTool(tooltips   = candle_tooltips, 
                                  formatters    = {'@date':'datetime'}, 
                                  mode          = 'vline',
                                  renderers     = [candles])
        
        candle_plot.add_tools(candle_hovertool)
        
        return candle_plot
    
    def plot_swings(self, swings, linked_fig):
        '''
        Plots swing detection indicator.
        '''
        swings = pd.merge(self.data, swings, left_on='date', right_index=True)
        
        linked_fig.scatter(list(swings.index),
                            list(swings.Last.values),
                            marker = 'dash',
                            size = 15,
                            fill_color = 'black',
                            legend_label = 'Last Swing Price Level')
    
    def plot_supertrend(self, st_data, linked_fig):
        ''' Plots supertrend indicator. '''
        # Extract supertrend data
        # uptrend     = st_data['uptrend']
        # dntrend     = st_data['downtrend']
        
        # reset index 
        st_data['date']         = st_data.index 
        st_data                 = st_data.reset_index(drop = True)
        
        # Add glyphs
        linked_fig.scatter(st_data.index,
                    st_data['uptrend'],
                    size = 5,
                    fill_color = 'blue',
                    legend_label = 'Up trend support')
        linked_fig.scatter(st_data.index,
                    st_data['downtrend'],
                    size = 5,
                    fill_color = 'red',
                    legend_label = 'Down trend support')
    
    
    ''' ----------------------- TOP FIG PLOTTING -------------------------- '''
    
    def _plot_trade(self, x_data, y_data, marker_type, marker_colour, 
                    label, linked_fig, scatter_size=15):
        '''
        Plots individual trade.
        '''
        
        linked_fig.scatter(x_data, y_data,
                           marker       = marker_type,
                           size         = scatter_size,
                           fill_color   = marker_colour,
                           legend_label = label)
    
    def _plot_trade_history(self, trade_summary, linked_fig, 
                            cancelled_summary=False, open_summary=False):
        ''' Plots trades taken over ohlc chart. '''
        
        ts = trade_summary
        # TODO - merge should work with left_on='date', right_index=True,
        # meaning this can be deleted below - test it
        ts['date']   = ts.index 
        ts           = ts.reset_index(drop = True)
        
        trade_summary = pd.merge(self.data, ts, left_on='date', right_on='date')
        
        # Backtesting signals
        long_trades             = trade_summary[trade_summary.Size > 0]
        shorts_trades           = trade_summary[trade_summary.Size < 0]
        
        if cancelled_summary is False and open_summary is False:
            
            exit_summary = pd.merge(self.data, ts, left_on='date', right_on='Exit_time')
            
            profitable_longs        = long_trades[(long_trades['Profit'] > 0)]
            unprofitable_longs      = long_trades[(long_trades['Profit'] < 0)]
            profitable_shorts       = shorts_trades[(shorts_trades['Profit'] > 0)]
            unprofitable_shorts     = shorts_trades[(shorts_trades['Profit'] < 0)]
            
            # Profitable long trades
            if len(profitable_longs) > 0:
                self._plot_trade(list(profitable_longs.data_index.values),
                                 list(profitable_longs.Entry.values), 
                                 'triangle', 'lightgreen', 
                                 'Profitable long trades', linked_fig)
    
            # Profitable short trades
            if len(profitable_shorts) > 0:
                self._plot_trade(list(profitable_shorts.data_index.values),
                                 list(profitable_shorts.Entry.values),
                                 'inverted_triangle', 'lightgreen',
                                 'Profitable short trades', linked_fig)
            
            # Unprofitable long trades
            if len(unprofitable_longs) > 0:
                self._plot_trade(list(unprofitable_longs.data_index.values),
                                 list(unprofitable_longs.Entry.values),
                                 'triangle', 'orangered',
                                 'Unprofitable long trades', linked_fig)
            
            # Unprofitable short trades
            if len(unprofitable_shorts) > 0:
                self._plot_trade(list(unprofitable_shorts.data_index.values),
                                 list(unprofitable_shorts.Entry.values),
                                 'inverted_triangle', 'orangered',
                                 'Unprofitable short trades', linked_fig)
        else:
            if cancelled_summary:
                long_legend_label = 'Cancelled long trades'
                short_legend_label = 'Cancelled short trades'
                fill_color = 'black'
                price = 'Order_price'
            else:
                long_legend_label = 'Open long trades'
                short_legend_label = 'Open short trades'
                fill_color = 'white'
                price = 'Entry'
        
            # Partial long trades
            if len(long_trades) > 0:
                linked_fig.scatter(list(long_trades.data_index.values),
                                   list(long_trades[price].values),
                                   marker = 'triangle',
                                   size = 15,
                                   fill_color = fill_color,
                                   legend_label = long_legend_label)
            
            # Partial short trades
            if len(shorts_trades) > 0:
                linked_fig.scatter(list(shorts_trades.data_index.values),
                                   list(shorts_trades[price].values),
                                   marker = 'inverted_triangle',
                                   size = 15,
                                   fill_color = fill_color,
                                   legend_label = short_legend_label)
        
        
        # Stop loss  levels
        if None not in trade_summary.Stop_loss.values:
            self._plot_trade(list(trade_summary.data_index.values),
                             list(trade_summary.Stop_loss.values),
                             'dash', 'black', 'Stop loss', linked_fig)
        
        # Take profit levels
        if None not in trade_summary.Take_profit.values:
            self._plot_trade(list(trade_summary.data_index.values),
                             list(trade_summary.Take_profit.values),
                             'dash', 'black', 'Take profit', linked_fig)
        
        # Position exits
        if cancelled_summary is False and open_summary is False:
            self._plot_trade(list(exit_summary.data_index),
                             list(exit_summary.Exit_price.values),
                             'circle', 'black', 'Position exit', linked_fig)
    
    
    ''' --------------------- BOTTOM FIG PLOTTING ------------------------- '''
    
    def _plot_macd(self, x_range, macd_data, linked_fig):
        ''' Plots MACD indicator. '''
        # Initialise figure
        fig = figure(plot_width     = linked_fig.plot_width,
                     plot_height    = self.bottom_fig_height,
                     title          = None,
                     tools          = linked_fig.tools,
                     active_drag    = linked_fig.tools[0],
                     active_scroll  = linked_fig.tools[1],
                     x_range        = linked_fig.x_range)
        
        histcolour = []
        for i in range(len(macd_data['histogram'])):
            if np.isnan(macd_data['histogram'][i]):
                histcolour.append('lightblue')
            else:
                if macd_data['histogram'][i] < 0:
                    histcolour.append('red')
                else:
                    histcolour.append('lightblue')
        
        # Add glyphs
        fig.line(x_range, macd_data['macd'], line_color = 'blue')
        fig.line(x_range, macd_data['signal'], line_color = 'red')
        fig.quad(top = macd_data['histogram'],
                 bottom = 0,
                 left = x_range - 0.3,
                 right = x_range + 0.3,
                 fill_color = histcolour)
        if 'crossvals' in macd_data:
            fig.scatter(x_range,
                        macd_data['crossvals'],
                        marker = 'dash',
                        size = 15,
                        fill_color = 'black',
                        legend_label = 'Last Crossover Value')
    
        return fig
    
    ''' -------------------- MISCELLANEOUS PLOTTING ----------------------- '''
    