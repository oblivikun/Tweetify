import sqlite3

connection = sqlite3.connect("data.db")
cursor = connection.cursor()

cursor.execute("create table accounts (username text, password text, bio text)")
cursor.execute("create table communities (id int, owner text, name text, desc text, staff text)")
cursor.execute("create table messages (communityid int, username text, message text, imageurl text, ipaddress text)")
cursor.execute("create table dms (sender text, receiver text, message text, ipaddress text)")

connection.commit()
connection.close()

