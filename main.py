from nicegui import ui,app
import re,os
import sqlite3
import datetime

import pandas as pd


conn=sqlite3.connect('stock_trading_records.db')
cur=conn.cursor()





def get_all_records():
    all_records=pd.read_sql("select code,stock_name,timestamp,action,price,quantity,amount,fee from stock_trading_record order by timestamp desc",con=conn)
    print(all_records.shape)
    return all_records

def get_overview_table():
    df=get_all_records()
    temp=df.groupby(['code','stock_name','action']).agg({'amount':sum,'quantity':sum})
    temp.columns=['total_amount','total_quantity']
    temp.reset_index(inplace=True)
    print(temp)
    temp=temp.sort_values(['code','action'],ascending=[True,True])
    temp['stock_quantity']=temp['total_quantity']-temp['total_quantity'].shift(-1)
    temp['stock_amount']=temp['total_amount']-temp['total_amount'].shift(-1)
    temp=temp[temp['action']=='BUY']

    for index, row in temp.iterrows():
        if int(row['stock_quantity'])<0:
            temp.loc[index,'stock_quantity']=row['total_quantity']
            temp.loc[index,'stock_amount']=row['total_amount']

    
    temp.drop(columns=['action'])

    return temp



def close_app():
     cur.close()
     conn.close()

app.on_shutdown(close_app)


def input_new_transaction():
    amount=price.value*quantity.value
    row=[(toggle_action.value, str(datetime.datetime.now()).split('.')[0],price.value,quantity.value,amount,fee.value,code.value,name.value)]
    insert_command='insert into stock_trading_record (action,timestamp,price,quantity,amount,fee,code,stock_name) values (?,?,?,?,?,?,?,?)' 
    cur.executemany(insert_command,row)
    sql='insert into sharks (id,name,sharktype,length) values(100,"test","testt",1000)'
    cur.execute(sql)
    conn.commit()
    ui_all_records.update_rows(get_all_records().to_dict(orient='records'))
    ui_overview_table.update_rows(get_overview_table().to_dict(orient='record'))
    ui.notify('Input successfully!')



ui.label('Trading transaction input:').style('color: #6E93D6; font-size: 200%; font-weight: 300')
toggle_action = ui.toggle(['BUY', 'SELL'], value='BUY')


with ui.row():
    
    code=ui.input(label='Code', placeholder='stock code',
         validation={'Input too long': lambda value: len(value) == 6 }).style('width:15%')
    name=ui.input(label='Name', placeholder='stock name',
         validation={'Input too long': lambda value: len(value) < 20}).style('width:15%')
    price=ui.number(label='Price',format='%.3f',step=0.1).props('clearable').style('width:15%')
   
    quantity=ui.number(label='Quantity',  placeholder='step by 100', value=100, step=100,
         validation={'Input ': lambda value: value >0 }).style('width:15%')

    fee=ui.number(label='Fee', placeholder='trasaction cost',step=0.1,
         validation={'Input too long': lambda value: value >0 }).style('width:15%')
ui.button('Record',on_click=input_new_transaction)

ui.separator()

ui_overview_table=ui.table.from_pandas(get_overview_table())

ui_all_records=ui.table.from_pandas(get_all_records())

ui.separator()


def show_value(e):
    ui.notify(e.value)

ui.label('Hello world')
ui.button('Click me!', on_click=lambda: ui.notify('You clicked me!'))



ui.run()