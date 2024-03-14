from nicegui import ui, app
import sqlite3
import datetime
import pandas as pd
import plotly.graph_objects as go
import akshare as ak
import numpy as np




conn = sqlite3.connect('stock_trading_records.db')
cur = conn.cursor()

ui.dark_mode().enable()
ui.page_title("Stock_transaction_tool")

label_style = 'color: #6E93D6; font-size: 200%; font-weight: 300'




def get_all_records():
    all_records = pd.read_sql(
        "select code,stock_name,timestamp,action,price,quantity,amount,fee from stock_trading_record order by timestamp desc", con=conn)
    # print(all_records.shape)
    return all_records


df_all_records = get_all_records()

df_etf = ak.fund_etf_spot_em()


def group_table_by_action(df, action):
    res = df[df['action'] == action].groupby(['code', 'stock_name']).agg(
        {'amount': 'sum', 'quantity': 'sum'})
    res.reset_index(inplace=True)
    return res


def get_overview_table():
    df = df_all_records.copy()

    df_buy = group_table_by_action(df, 'BUY')
    df_sell = group_table_by_action(df, 'SELL')
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
    df.fillna(0)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df[['差幅', '涨跌幅']] = df[['差幅', '涨跌幅']].map(lambda x: '%.2f%%' % x)
    df[['amount', '现价值']] = df[['amount', '现价值']].map(lambda x: '%.2f' % x)
    df[['差价', 'cost', 'profit']] = df[[
        '差价', 'cost', 'profit']].map(lambda x: '%.3f' % x)
    df = df.sort_values(by=['quantity', 'amount'], ascending=False)
    return df


df_overview = get_overview_table()

all_stock_codes = list(df_overview['code'].values)


def get_total_profit(df_overview) -> float:
    return round(df_overview['profit'].apply(pd.to_numeric).sum(), 2)


total_profit = get_total_profit(df_overview)


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
    update_2_tables_ui()
    with ui.dialog() as dialog, ui.card():
        ui.label('New transaction added!').style(
            'color: green; font-size: 200%')
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

with ui.row():
    ui.label('Overview').style(label_style)
    ui.space()
    ui_total_profit = ui.label().bind_text(globals(), 'total_profit').style(
        'color:green;font-size: 100%; font-weight: 300' if total_profit > 0 else 'color:red;font-size: 100%; font-weight: 300;margin-top:15px')


@ui.refreshable
def overtiew_table_ui() -> None:
    ui.table.from_pandas(df_overview, pagination=10).add_slot('body-cell-profit', '''
    <q-td key="profit" :props="props">
        <q-badge :color="props.value < 0 ? 'red' : 'green'">
            {{ props.value }}
        </q-badge>
    </q-td>
''')


overtiew_table_ui()

ui.separator()

def add_trace_to_fig(df_all_records, action, code):
    df = df_all_records[df_all_records['action'] == action].copy()
    ts = df[df['code'] == code]['timestamp'].to_list()
    prices = df[df['code'] == code]['price'].to_list()
    quantity = df[df['code'] == code]['quantity'].to_list()
    size_buy = list(map(lambda x: x/100, quantity))
    fig.add_trace(go.Scatter(x=ts, y=prices, text=quantity,
                  marker_size=size_buy, hoverinfo='y + text', name=action))


def update_plot() -> None:
    fig.data = []
    add_trace_to_fig(df_all_records, 'BUY', ui_code_selector.value)
    add_trace_to_fig(df_all_records, 'SELL', ui_code_selector.value)
    ui_plot.update()


with ui.row():
    ui.label('Transcations').style(label_style)
    ui.space()
    ui_code_selector = ui.select(
        all_stock_codes, value=all_stock_codes[0], on_change=update_plot)


fig = go.Figure()
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
ui_plot = ui.plotly(fig).classes('w-full h-60')
update_plot()


@ui.refreshable
def all_records_table_ui() -> None:
    ui.table.from_pandas(
        df_all_records_price, row_key='code', pagination=5).bind_filter_from(ui_code_selector, 'value').add_slot('body-cell-profit', '''
    <q-td key="profit" :props="props">
        <q-badge :color="props.value < 0 ? 'red' : 'green'">
            {{ props.value }}
        </q-badge>
    </q-td>
''')


def update_2_tables_ui() -> None:
    global df_etf, df_all_records_price, df_overview, total_profit
    df_etf = ak.fund_etf_spot_em()
    df_all_records_price = bind_price_to_all_records()
    df_overview = get_overview_table()
    total_profit = get_total_profit(df_overview)
    overtiew_table_ui.refresh()
    all_records_table_ui.refresh()


all_records_table_ui()
ui.button('update', on_click=update_2_tables_ui)

ui.run()
