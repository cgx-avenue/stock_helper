from nicegui import ui, app
import re
import os
import sqlite3
import datetime
import pandas as pd
import plotly.graph_objects as go
import akshare as ak

conn = sqlite3.connect('stock_trading_records.db')
cur = conn.cursor()

ui.page_title("Stock_transaction_tool")

label_style = 'color: #6E93D6; font-size: 200%; font-weight: 300'


def get_all_records():
    all_records = pd.read_sql(
        "select code,stock_name,timestamp,action,price,quantity,amount,fee from stock_trading_record order by timestamp desc", con=conn)
    print(all_records.shape)
    return all_records

# get all transactions from database as data source
df_all_records = get_all_records()

# use akshare interface to get all ETF real-time prices
df_etf = ak.fund_etf_spot_em()


def get_overview_table():
    df = df_all_records.copy()

    def group_table(df, action):
        res = df[df['action'] == action].groupby(['code', 'stock_name']).agg(
            {'amount': sum, 'quantity': sum})
        res.reset_index(inplace=True)
        return res

    df_buy = group_table(df, 'BUY')
    df_sell = group_table(df, 'SELL')
    df_agg = df_buy.join(df_sell.set_index(
        'code'), on='code', rsuffix='_sell').fillna(0)
    df_agg['amount'] = df_agg['amount']-df_agg['amount_sell']
    df_agg['quantity'] = df_agg['quantity']-df_agg['quantity_sell']
    df_agg.sort_values('quantity', ascending=True)

    df_agg = df_agg.drop(
        ['stock_name_sell', 'amount_sell', 'quantity_sell'], axis=1)
    df_agg['cost'] = df_agg['amount'].apply(
        lambda x: float(x))/df_agg['quantity']

    df = df_agg.join(df_etf.set_index('代码'), on='code')
    df = df.drop(['stock_name', '成交量', '成交额', '流通市值', '总市值'], axis=1)
    df[["最新价", "涨跌额"]] = df[["最新价", "涨跌额"]].apply(pd.to_numeric)

    df['现价值'] = df['最新价']*df['quantity']
    df['差价'] = (df['最新价']-df['cost'])
    df['差幅'] = (100*(df['最新价']-df['cost'])/df['cost']
                )

    df['cost'] = df['cost']
    df['profit'] = (df['现价值']-df['amount'])
    df[['差幅', '涨跌幅']] = df[['amount', '涨跌幅']].map(lambda x: '%.2f%%' % x)
    df[['amount', '现价值']] = df[['amount', '现价值']].map(lambda x: '%.2f' % x)
    df[['差价', 'cost', 'profit']] = df[[
        '差价', 'cost', 'profit']].map(lambda x: '%.3f' % x)
    return df

df_overview = get_overview_table()

codes = list(df_overview['code'].values)
total_profit=round( df_overview['profit'].apply(pd.to_numeric).sum(),2)


def bind_price_to_all_records():
    # process detailed transaction data
    df = df_all_records.copy().join(df_etf.set_index('代码'), on='code')
    df = df.drop(['stock_name', '成交量', '成交额', '流通市值', '总市值', '涨跌额',
                 '涨跌幅', '开盘价', '最高价', '最低价', '昨收', '换手率'], axis=1)
    df[["price", "quantity", 'amount', 'fee']] = df[[
        "price", "quantity", 'amount', 'fee']].apply(pd.to_numeric)

    df['差价'] = (df['最新价']-df['price']).apply(lambda x: '%.3f' % x)
    df['差幅'] = (100*(df['最新价']-df['price'])/df['price']
                ).apply(lambda x: '%.2f%%' % x)
    df['profit'] = (df['最新价']-df['price'])*df['quantity']

    df['profit'] = df['profit'].mask(
        df['action'] == 'SELL', df['profit']*(-1)).apply(lambda x: '%.3f' % x)

    return df


df_all_records_price = bind_price_to_all_records()


def close_app():
    cur.close()
    conn.close()


app.on_shutdown(close_app)


def input_new_transaction():
    amount = price.value*quantity.value
    row = [(action.value, str(datetime.datetime.now()).split('.')[
            0], price.value, quantity.value, amount, fee.value, code.value, name.value)]
    insert_command = 'insert into stock_trading_record (action,timestamp,price,quantity,amount,fee,code,stock_name) values (?,?,?,?,?,?,?,?)'
    cur.executemany(insert_command, row)

    conn.commit()
    df_all_records = get_all_records()
    ui_all_records.update_rows(df_all_records.to_dict(orient='records'))
    update_overview_table_ui()
    with ui.dialog() as dialog, ui.card():
        ui.label('Insertion done!').style('color: green; font-size: 200%')
        ui.button('Close', on_click=dialog.close)


with ui.expansion('Add new transaction!', icon='add').classes('w-full').style(label_style):
    with ui.row():
        code = ui.input(label='Code', placeholder='stock code',
                        validation={'Input too long': lambda value: len(value) == 6}).style('width:8%').props('clearable')
        name = ui.input(label='Name', placeholder='stock name',
                        validation={'Input too long': lambda value: len(value) < 20}).style('width:15%').props('clearable')
        price = ui.number(label='Price', format='%.3f', step=0.1).props(
            'clearable').style('width:10%')
        quantity = ui.number(label='Quantity',  placeholder='step by 100', value=100, step=100,
                             validation={'Input ': lambda value: value > 0}).style('width:6%').props('clearable')
        fee = ui.number(label='Fee', placeholder='trasaction cost', step=0.1,
                        validation={'Input too long': lambda value: value > 0}).style('width:6%').props('clearable')
        action = ui.radio(['BUY', 'SELL'], value='BUY').props('inline')

        ui.button('Add', icon='add', on_click=input_new_transaction)


ui.separator()

ui.label('Overview').style(label_style)
ui_total_profit=ui.label('Total profit: {0}'.format(total_profit)).style('font-size: 100%; font-weight: 300')





@ui.refreshable
def overtiew_table_ui() -> None:
    ui.table.from_pandas(df_overview).add_slot('body-cell-profit', '''
    <q-td key="profit" :props="props">
        <q-badge :color="props.value < 0 ? 'red' : 'green'">
            {{ props.value }}
        </q-badge>
    </q-td>
''')


def update_overview_table_ui() -> None:
    global df_etf, df_overview
    df_etf = ak.fund_etf_spot_em()
    df_overview = get_overview_table()
    overtiew_table_ui.refresh()


overtiew_table_ui()
# ui.button('update', on_click=update_overview_table_ui)

ui.separator()


def update_plot() -> None:
    fig.data = []
    df_buy = df_all_records[df_all_records['action'] == 'BUY'].copy()
    df_sell = df_all_records[df_all_records['action'] == 'SELL'].copy()
    ts_buy = df_buy[df_all_records['code'] ==
                    ui_code_selector.value]['timestamp'].to_list()
    prices_buy = df_buy[df_all_records['code']
                        == ui_code_selector.value]['price'].to_list()
    quantity_buy = df_buy[df_all_records['code']
                          == ui_code_selector.value]['quantity'].to_list()
    size_buy = list(map(lambda x: x/100, quantity_buy))
    ts_sell = df_sell[df_all_records['code'] ==
                      ui_code_selector.value]['timestamp'].to_list()
    prices_sell = df_sell[df_all_records['code']
                          == ui_code_selector.value]['price'].to_list()
    quantity_sell = df_sell[df_all_records['code']
                            == ui_code_selector.value]['quantity'].to_list()
    size_sell = list(map(lambda x: x/100, quantity_sell))

    fig.add_trace(go.Scatter(x=ts_buy, y=prices_buy, text=quantity_buy,
                  marker_size=size_buy, hoverinfo='y + text', name='Buy'))
    fig.add_trace(go.Scatter(x=ts_sell, y=prices_sell, text=quantity_sell,
                  marker_size=size_sell, hoverinfo='y + text', name='Sell'))

    ui_plot.update()


with ui.row():
    ui.label('Transcations').style(
        label_style)
    ui.space()
    ui_code_selector = ui.select(codes, value=codes[0], on_change=update_plot)


fig = go.Figure()
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
ui_plot = ui.plotly(fig).classes('w-full h-60')
update_plot()


@ui.refreshable
def all_records_table_ui() -> None:
    ui.table.from_pandas(
        df_all_records_price, row_key='code').bind_filter_from(ui_code_selector, 'value').add_slot('body-cell-profit', '''
    <q-td key="profit" :props="props">
        <q-badge :color="props.value < 0 ? 'red' : 'green'">
            {{ props.value }}
        </q-badge>
    </q-td>
''')


def update_all_records_table_ui() -> None:
    global df_etf, df_all_records_price,df_overview
    df_etf = ak.fund_etf_spot_em()
    df_all_records_price = bind_price_to_all_records()
    df_overview=get_overview_table()
    overtiew_table_ui.refresh()
    all_records_table_ui.refresh()


all_records_table_ui()
ui.button('update', on_click=update_all_records_table_ui)


ui.separator()


def show_value(e):
    ui.notify(e.value)


ui.run()
