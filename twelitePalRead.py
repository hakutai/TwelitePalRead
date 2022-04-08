#!/usr/bin/python3
# coding: utf8

##########################################################################
#
# TWELITE PAL からデータを読み込み、表示
#
# usage : twelitePalRead DEVICE-NAME
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
#palTyep = {"81" : "OpenClose", "82" : "Ambient", "83" : "Motion", "84" : "Notice" }
palTyep   = { '81' : '開閉', '82' : '環境', '83' : '動作', '84' : '通知' }
senseType = { '00' : '磁気', '01' : '温度', '02' : '湿度', '03' : '照度', '04' : '加速度', '05' : 'イベント', '30' : 'ADC' }

#

# データパケットの表示
def printDataPacket(l):

	return True

# 受信メッセージの表示
def printPayload(l):

	dt_now = datetime.datetime.now()

	print("---DataNo 0x%04x" % (l[5] << 8 | l[6]) , dt_now.strftime('%H:%M'))
	print(" Device ID : %02x " % l[11])
	print(" LQI       : %d / %.2f [dbm]" % (l[4],(7 * l[4] - 1970) / 20.))
	print(" ADC       : %d mV" % (l[19] << 8 | l[20]))
	print(" ADC1      : %d mV" % (l[25] << 8 | l[26]))
	print(" Temp      : %.2f C" % ((l[31] << 8 | l[32]) / 100.))
	print(" mide      : %.2f %%" % ((l[37] << 8 | l[38]) / 100.))
	print(" lux       : %d" % (l[43] << 24 | l[44] << 16 | l[45] << 8 | l[46]))

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
