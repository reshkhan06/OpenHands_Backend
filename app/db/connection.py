import sqlite3

con = sqlite3.connect("donation.sqlit.db")
cur = con.cursor()

con.close()
