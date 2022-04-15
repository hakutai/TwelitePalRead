#!/usr/bin/python3
# coding: utf8

##########################################################################
#
# TWELITE PAL からデータを読み込み、表示
#
# usage : twelitePalRead DEVICE-NAME
#
#
#
##########################################################################

from serial import *
from sys import stdout, stdin, stderr, exit
import threading
import datetime

# 大域変数
serialPort = None	# シリアルポート
readThread = None	# 読み出しスレッド
isExit = False		# プログラム終了フラグ

# センサーパルの種類
palIdList   = { '81' : '開閉', '82' : '環境', '83' : '動作', '84' : '通知' }
sensorList = { 	'00' : { 'name':'磁気',    'unit':'',   'datatype':'00' },
				'01' : { 'name':'温度',    'unit':'℃', 'datatype':'05' },
				'02' : { 'name':'湿度',    'unit':'％', 'datatype':'01' },
				'03' : { 'name':'照度',    'unit':'lux','datatype':'02' },
				'04' : { 'name':'加速度',  'unit':'mg', 'datatype':'15' },
				'05' : { 'name':'イベント','unit':'',   'datatype':'12' },
				'30' : { 'name':'ADC',     'unit':'mV', 'datatype':'11' }}

#

# データパケットの表示
def printDataPacket(l):

	return True

# 受信メッセージの表示
def printPayload(l):

	dt_now = datetime.datetime.now()

	sizeData = l[14]			# 受信データ数

	print("---DataNo 0x%04x" % (l[5] << 8 | l[6]) , dt_now.strftime('%H:%M'))
	print(" Device ID : %02x " % l[11])
	print(" LQI       : %d / %.2f [dbm]" % (l[4],(7 * l[4] - 1970) / 20.))

	index = 15
	for kData in range(sizeData):
		sensorID = format(l[index + 1],'02x')
		sensor = sensorList[sensorID]
		sensorName  = sensor['name']
		sensorValue = None
		valueUnit   = sensor['unit']

		if sensorID == '00':				# 磁気
			sensorValue = l[index + 4]
		elif sensorID == '01':				# 温度
			sensorValue = (l[index + 4] << 8 | l[index + 5]) / 100
		elif sensorID == '02':				# 湿度
			sensorValue = (l[index + 4] << 8 | l[index + 5]) / 100
		elif sensorID == '03':				# 照度
			sensorValue = l[index + 4] << 24 | l[index + 5] << 16 \
						| l[index + 6] <<  8 | l[index + 7]
		elif sensorID == '04':				# 加速度
			sensorValue = "X:"+str(l[index + 4]<<8 | l[index + 5])+"mg,"  \
						+ "Y:"+str(l[index + 6]<<8 | l[index + 7])+"mg," 
#						+ "Z:"+str(l[index + 8] << 8 | l[index + 9]) + "mg"
		elif sensorID == '05':				# イベント
			sensorValue = l[index + 4]
		elif sensorID == '30':				# ADC
			sensorValue = l[index + 4] << 8 | l[index + 5]
			if l[index + 2] == 8:
				sensorName = '電源電圧'
			elif l[index + 2] == 1:
				sensorName = 'ADC1'

		print(sensorName,end=":")
		print(sensorValue,end="")
		print(valueUnit,end=" /")

		index += 4 + l[index + 3]

	print(" ")


	return True


# デバイスから受信データを取得し、バイト単位でリストに格納するスレッド
def readThread():
	global serialPort, isExit

	while True:
		if isExit: return		# 終了

		readData = serialPort.readline().rstrip()

		isCommand = False
		isStr	  = False

		if len(readData) > 0:
			c = readData[0]
			if isinstance(c,str):
				if c == ':': isCommand = True
				isStr = True
			else:
				if c == 58: isCommand = True

		if not isCommand: continue

		try:
			lst = {}
			if isStr:
				lst = map(ord,readData[1:].decode('hex'))
			else:
				import codecs
				s = readData[1:].decode("ascii")
				lst = codecs.decode(s, "hex_codec")

			chksum = sum(lst) & 0xff
			lst = lst[0:len(lst)-1]

			if chksum == 0:
				printPayload(lst)
			else:
				print ("checksum error")

		except:
			if len(readData) > 0:
				print ("Decord Error (%s)" % readData)

# 終了処理
def DoTerminate():
	global readThread, isExit

	# スレッド停止
	isExit = True

	print ("... quitting")
	time.sleep(0.5)		# スリープでスレッドの終了待ちをする

	exit(0)	

# メイン
if __name__ == '__main__':
	
	if len(sys.argv) != 2:
		print("Usage: %s {serial port name}" % sys.argv[0])
		exit(1)

	# open serial port
	try:
		serialPort = Serial(sys.argv[1], 115200, timeout=0.1)
		print ("open serial port: %s" % sys.argv[1])
	except:
		print ("cannot open serial port: %s" % sys.argv[1])
		exit(1)

	# 読み出しスレッドの開始
	readThread = threading.Thread(target=readThread)
	readThread.setDaemon(True)
	readThread.start()

	# stdinからの入力処理
	while True:
		try:
			sText = stdin.readline().rstrip()

			if len(sText) > 0:
				if sText[0] == 'q':
					DoTerminate()

		except KeyboardInterrupt:  # Ctrl-C
			Doterminate()
		except SystemExit:
			exit(0)
		except:
			print("... unknown exception detected")
			break
	
	exit(0)
