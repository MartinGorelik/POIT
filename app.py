from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect
import MySQLdb  
import time
import math
import random
import ConfigParser
import serial

ser = serial.Serial('/dev/ttyS3',9600)
ser.baurate = 9600

async_mode = None

app = Flask(__name__)

config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print myhost

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


def background_thread(args):
    count = 0
    i = 0
    dataCounter = 0 
    dataList = []  
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)          
    while True:
        if args:
          A = dict(args).get('A')
          dbV = dict(args).get('db_value')
        else:
          A = 0
          dbV = 'nieco' 
        A = int(A)
        ser.write(str(int(9)))
        kom = ser.readline()
        ser.write(str(A))
        data = kom.split(':')
        cas = time.time()
        dataCounter +=1
        socketio.sleep(0.5)
        if dbV == 'start':
            count += 1
            print(data)
            socketio.emit('my_response',{'data': data[0], 'data2': data[1], 'count': cas, 'time':cas}, namespace='/test')
            dataDict = {
                "t": time.time(),
                "poradie": dataCounter,
                "U1": data[0],
                "U2": data[1]
                }
            dataList.append(dataDict)
            if len(dataList)>0:
                print (str(dataList))
                fuj = str(dataList).replace("'", "\"")
                print fuj
                cursor = db.cursor()
                cursor.execute("SELECT MAX(id) FROM graph")
                maxid = cursor.fetchone()
                cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (maxid[0] + 1, fuj))
                db.commit()
            fuj = str(dataList).replace("'", "\"")
            print fuj
            fo = open("static/files/test.txt","a+")
            fo.write("%s\r\n" %fuj)    
            dataList = []
            dataCounter = 0

@app.route('/read/<string:num>', methods=['GET', 'POST'])
def readmyfile(num):
    fo = open("static/files/test.txt","r")
    rows = fo.readlines()
    return rows[int(num)-1]
    
@app.route('/db')
def db():
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute('''SELECT  hodnoty FROM  graph ''')
  rv = cursor.fetchall()
  return str(rv)    

@app.route('/dbdata/<string:num>', methods=['GET', 'POST'])
def dbdata(num):
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  print num
  cursor.execute("SELECT hodnoty FROM  graph WHERE id=%s", num)
  rv = cursor.fetchone()
  return str(rv[0])

@socketio.on('my_event', namespace='/test')
def test_message(message):   
    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['A'] = message['value']
    emit('my_response',
         {'data': message['value'], 'count': session['receive_count'], 'ampl':1})
    
# @socketio.on('save', namespace='/test')
# def message(message):   
#     print (message)
    
@socketio.on('db_event', namespace='/test')
def db_message(message):   
#    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['db_value'] = message['value']    
#    emit('my_response',
#         {'data': message['value'], 'count': session['receive_count']})

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    emit('my_response', {'data': 'Connected', 'count': 0})

@app.route('/')
def index():
    return render_template('tabs.html', async_mode=socketio.async_mode)

@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()
    
@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
