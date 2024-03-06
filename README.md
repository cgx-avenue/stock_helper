# stock_helper
A tool for tracing stock transactions, mainly focusing on recording, cost calculation, etc. 
## 2024-03-05
At the beginning I want to use Flask + Vue.js for this project. But during searching on the Internet, I found NiceGUI seems to be a good alternative for this simple and quick use case.
https://nicegui.io/
Let's try and see how it works and how well it works.

## Environment
### Python
1. Conda environment
```shell
conda create -n shenv python=3.10
conda activiate shenv

```
2. Install dependencies
``` shell



```


### Database
Sqlite3
```bash
sudo apt update 
sudo apt install sqlite3
sqlite3 --version
# change to project folder and then
sqlite3 stock_trading_records.db

```
Then the terminal will enter sql mode.
```sql
-- to activate creation of db file, input a line only with ;
; 
-- create table
CREATE TABLE stock_trading_record (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	"action" TEXT,
	"timestamp" TEXT,
	price REAL,
	quantity INTEGER,
	amount REAL,
	fee REAL,
	code TEXT,
	stock_name TEXT
);
CREATE INDEX stock_trading_record_id_IDX ON stock_trading_record (id,code,stock_name);



```