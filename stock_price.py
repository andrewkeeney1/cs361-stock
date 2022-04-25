from flask import Flask, render_template, redirect, request, flash, session
import sqlite3
import yfinance as yfin
from pandas_datareader import data as pdr
from datetime import date, timedelta
from passlib.hash import pbkdf2_sha256
from sqlite3 import Error
from functools import wraps

app = Flask(__name__)
app.secret_key = ['beepboop']
yfin.pdr_override()

def session_check(func):
    @wraps(func)
    def session_wrapper(*args, **kwargs):
        if not session['username']:
            return redirect('/')
        return func(*args, **kwargs)
    return session_wrapper

@app.route('/')
def home():
    """
    Home page.  Create a new DB if one doesn't exist
    """
    conn = sqlite3.connect('stocks.db')
    conn.execute('''CREATE TABLE if not exists USER 
                 (ID            INTEGER      PRIMARY KEY     NOT NULL,
                 USERNAME         TEXT        NOT NULL UNIQUE,
                 PASSWORD         TEXT        NOT NULL,
                 MONTHLY_INCOME   INT         NOT NULL, 
                 SAVINGS_GOAL     INT         NOT NULL);    
                 ''')
    conn.execute('''CREATE TABLE if not exists STOCKS 
             (ID            INTEGER      PRIMARY KEY     NOT NULL,
             TICKER         TEXT         NOT NULL,
             COST_BASIS     INT          NOT NULL,
             SHARES_OWNED   INT          NOT NULL,
             USERNAME       TEXT         NOT NULL);    
             ''')
    conn.execute('''CREATE TABLE if not exists BUDGET 
                 (ID            INTEGER      PRIMARY KEY     NOT NULL,
                 NAME           TEXT         NOT NULL,
                 AMOUNT         INT          NOT NULL,
                 EXP_DATE       DATE         NOT NULL,
                 CATEGORY       TEXT         NOT NULL,
                 DESCRIPTION    TEXT         NOT NULL,
                 USERNAME       TEXT         NOT NULL);
                 ''')
    conn.commit()
    conn.close()

    return render_template("index.html")

@app.route('/login', methods = ['POST', 'GET'])
def login():
    username = request.form['username']
    password = request.form['password']


    conn = sqlite3.connect('stocks.db')
    # query for the user login
    cursor = conn.execute("SELECT ID, USERNAME, PASSWORD from USER WHERE USERNAME = (?)", (username,))
    uName = cursor.fetchall()
    print(len(uName))


    # check for the user
    if len(uName) == 0:
        print("Error 1!")
        flash("That username doesn't exist!")
        return redirect('/')

    # check password
    if password != uName[0][2]:
        print("Error 2!")
        flash("Wrong password!")
        return redirect('/')

    #if not pbkdf2_sha256.verify(pWord[0], hash):
        # how to do we determine current user session?
        #error: flash message
    #    return redirect('/')

    session['username'] = username
    return redirect('/budget')

@app.route('/new_user', methods = ['POST', 'GET'])
def register():
    if request.method == "GET":
        return render_template("new_user.html")

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']
        income = request.form['income']
        savings = request.form['savings']

        # passwords match confirmation
        if password != confirm:
            #flash('Passwords do not match!')
            print("pword no match")
            return redirect('/new_user')

        try:
            conn = sqlite3.connect('stocks.db')
            cursor = conn.execute("SELECT USERNAME from USER WHERE USERNAME = (?)", username)
            #flash('Username already taken!')
            print("username taken")
            return redirect('/new_user')

        except sqlite3.Error:
            conn = sqlite3.connect('stocks.db')
            # hash password
            conn.execute("INSERT INTO USER (ID, USERNAME, PASSWORD, MONTHLY_INCOME, SAVINGS_GOAL) VALUES (NULL, ?, ?, ?, ?)",(username, password, income, savings))
            conn.commit()
            conn.close()

        #flash('Account creation successful')

        session['username'] = username
        return redirect('/budget')

@app.route('/profile')
@session_check
def profile():
    conn = sqlite3.connect('stocks.db')
    cursor = conn.execute("SELECT * from USER WHERE USERNAME = (?)", (session['username'],))
    user_info = (cursor.fetchall())
    return render_template("profile.html", user = user_info)

@app.route('/update_pw', methods = ['POST', 'GET'])
@session_check
def update_password():
    cur_pw = request.form['cur_pw']
    new_pw = request.form['new_pw']
    confirm_new_pw = request.form['confirm']

    conn = sqlite3.connect('stocks.db')
    cursor = conn.execute("SELECT PASSWORD from USER WHERE USERNAME = (?)", (session['username'],))
    pw = cursor.fetchone()

    if new_pw != confirm_new_pw:
        print("passwords don't match!")
        return redirect('/profile')

    elif cur_pw != pw[0]:
        print("wrong old pw!")
        return redirect('/profile')

    else:
        conn.execute('UPDATE USER SET PASSWORD = (?) WHERE USERNAME = (?)', (new_pw ,session['username']))
        conn.commit()
        conn.close()
        return redirect('/profile')

@app.route('/update_income', methods = ['POST', 'GET'])
@session_check
def update_income():
    income = request.form['income']

    conn = sqlite3.connect('stocks.db')
    conn.execute('UPDATE USER SET MONTHLY_INCOME = (?) WHERE USERNAME = (?)', (income, session['username']))
    conn.commit()
    conn.close()
    return redirect('/profile')

@app.route('/update_savings', methods = ['POST', 'GET'])
@session_check
def update_savings():
    savings = request.form['savings']

    conn = sqlite3.connect('stocks.db')
    conn.execute('UPDATE USER SET SAVINGS_GOAL = (?) WHERE USERNAME = (?)', (savings, session['username']))
    conn.commit()
    conn.close()
    return redirect('/profile')

@app.route('/budget')
@session_check
def budget():
    conn = sqlite3.connect('stocks.db')
    cursor = conn.execute("SELECT ID, NAME, AMOUNT, EXP_DATE, CATEGORY, DESCRIPTION from BUDGET WHERE USERNAME = (?)", (session['username'],))
    budget_info = (cursor.fetchall())
    cursor2 = conn.execute("SELECT MONTHLY_INCOME, SAVINGS_GOAL from USER WHERE USERNAME = (?)",(session['username'],))
    user_info = (cursor2.fetchall())
    cursor3 = conn.execute("SELECT SUM(AMOUNT)from BUDGET WHERE USERNAME = (?)", (session['username'],))
    spent_this_month = (cursor3.fetchall())


    if len(budget_info) > 0:
        remaining_funds = user_info[0][0] - spent_this_month[0][0]
        return (render_template("budget.html", data = budget_info, user_info = user_info, spent = spent_this_month, remaining_funds = remaining_funds))
    else:
        new_user = "Start here!"
        return (render_template("budget.html", new_user = new_user, user_info = [[]], spent = [[]]))

@app.route('/add_expense', methods = ['POST', 'GET'])
@session_check
def expense():
    name = request.form['expName']
    amount = request.form['amount']
    exp_date = request.form['date']
    category = request.form['category']
    description = request.form['notes']

    # add an expense to the DB
    conn = sqlite3.connect('stocks.db')
    conn.execute("INSERT INTO BUDGET (ID, NAME, AMOUNT, EXP_DATE, CATEGORY, DESCRIPTION, USERNAME) VALUES (NULL, ?, ?, ?, ?, ?, ?)", (name, amount, exp_date, category, description, session['username']))
    conn.commit()
    conn.close()

    # redirect to the budget page.
    return redirect('/budget')

@app.route('/del_expense', methods = ['POST', 'GET'])
@session_check
def delete_expense():
    expense_id = request.form['del']

    # delete an expense from the DB.
    conn = sqlite3.connect('stocks.db')
    conn.execute("DELETE FROM BUDGET WHERE ID=(?)", expense_id)
    conn.commit()
    conn.close()

    # redirect to the budget page.
    return redirect('/budget')

@app.route('/stocks')
@session_check
def display():
    """
    DB Select statements for table data.
    :return: Jinja2 template.
    """

    # connect to DB and query stocks table.
    conn = sqlite3.connect('stocks.db')
    cursor = conn.execute("SELECT ID, TICKER, SUM(COST_BASIS*SHARES_OWNED)/SUM(SHARES_OWNED), SUM (SHARES_OWNED) from STOCKS WHERE USERNAME = (?) GROUP BY TICKER;", (session['username'],))
    stocks = (cursor.fetchall())

    # will be list of lists that combines query data and yfinance API call/ math based on query and API data.
    db_list = []

    # populate db_list with DB data, plus yfinance/ath
    for stock in range(len(stocks)):
        db_list.append(list(stocks[stock]))  # convert DB tuple to list.
        print(db_list)
        # next line gets the current rounded price using yfinance API.
        if date.today().weekday() == 6:
            yesterday = date.today() - timedelta(days=2)
            db_list[stock].append(round(pdr.get_data_yahoo(stocks[stock][1], period = "1d")["Close"].loc[yesterday.strftime("%Y-%m-%d")], 2))
        elif date.today().weekday() == 5:
            yesterday = date.today() - timedelta(days=1)
            db_list[stock].append(round(pdr.get_data_yahoo(stocks[stock][1], period="1d")["Close"].loc[yesterday.strftime("%Y-%m-%d")], 2))
        else:
            db_list[stock].append(round(pdr.get_data_yahoo(stocks[stock][1], period="1d")["Close"].loc[date.today().strftime("%Y-%m-%d")], 2))
        # current market value equal to previous line (current price) * shares owned (shares owned from DB).
        db_list[stock].append(round(db_list[stock][3] * db_list[stock][4], 2))
        # gain/ loss
        db_list[stock].append(round((((db_list[stock][5])/(db_list[stock][2] * db_list[stock][3]))-1)* 100, 2))

    # variables to roll up total cost basis and MV from each row.
    cost_basis = 0
    market_value = 0
    print(db_list)


    for _ in range(len(db_list)):
        cost_basis += round(db_list[_][2] * db_list[_][3], 2)
        market_value += round(db_list[_][3] * db_list[_][4], 2)

    if cost_basis:
        gain_loss = str(round(market_value/cost_basis - 1)) + "%"
    else:
        gain_loss = 0

    conn.close()

    return render_template("stocks.html", data = db_list, cb = cost_basis, mv=market_value, gl= gain_loss)

@app.route('/add_stock', methods = ['POST', 'GET'])
@session_check
def purchase():
    ticker = request.form['ticker']
    shares = request.form['shares']
    price = round(int(request.form['price']),2)

    # add a stock purchase to the DB
    conn = sqlite3.connect('stocks.db')
    conn.execute("INSERT INTO STOCKS (ID, TICKER,COST_BASIS,SHARES_OWNED, USERNAME) VALUES (NULL, ?, ?, ?, ?)", (ticker, shares, price, session['username']))
    conn.commit()
    conn.close()

    # redirect to the stocks page.
    return redirect('/stocks')

@app.route('/del_stock', methods = ['POST', 'GET'])
@session_check
def delete_stock():
    stock_id = request.form['del']

    # delete a stock from the DB.
    conn = sqlite3.connect('stocks.db')
    conn.execute("DELETE FROM STOCKS WHERE ID=(?)", (stock_id,))
    conn.commit()
    conn.close()

    # redirect to the stocks page.
    return redirect('/stocks')

@app.route('/advanced_stats', methods = ['POST', 'GET'])
@session_check
def advanced_stats():
    return render_template("advanced_info.html")

@app.route('/loan_calc', methods = ['POST', 'GET'])
@session_check
def loan_calculator():
    return render_template("loan_calculator.html")

@app.route('/logout', methods = ['POST', 'GET'])
@session_check
def log_out():
    session['username'] = None
    return redirect("/")

if __name__ == "__main__":
    app.run(port=7001, debug=True)


