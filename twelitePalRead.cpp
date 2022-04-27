#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define SERIAL_PORT		"/dev/ttyUSB0"
#define	SERIAL_BAUDRATE	B115200

typedef struct {
			int		id;
			char	name[256];
			char	unit[16];
			int		dataType;
} S_SensorList;

#define		SizeOfSensorList	7
S_SensorList	sensorList[SizeOfSensorList] = {
		{ 0x00, "磁気",     ":",   0x00 },
		{ 0x01, "温度",     "℃",  0x05 },
		{ 0x02, "湿度",     "％",  0x01 },
		{ 0x03, "照度",     "lux", 0x02 },
		{ 0x04, "加速度",   "mg",  0x15 },
		{ 0x05, "イベント", "",    0x12 },
		{ 0x30, "ADC",      "mV",  0x11 } };

int		Readln(int handle, char *buffer, int maxSize);
void 	PrintPayload(const char *payload);

int main(int argc, char *argv[])
{
	int				serialHandler;
	struct termios	newTio,oldTio;
	char			buf[256];
	int				len;
	long			checksum;

	serialHandler = open(SERIAL_PORT,O_RDONLY);
	if (serialHandler < 0) {
		printf("Serial port open error\n");
		return -1;
	}

	ioctl(serialHandler, TCGETS, &oldTio);
	newTio = oldTio;

	cfmakeraw(&newTio);
	newTio.c_cflag = (SERIAL_BAUDRATE | CS8 | CLOCAL | CREAD);
	newTio.c_iflag = (IGNPAR);
	ioctl(serialHandler,TCSETS,&newTio);

	while (true) {
		len = Readln(serialHandler, buf, sizeof(buf));

		checksum = 0;
		for (int i = 0; i < len; i++) {
			checksum += buf[i];
		}
//		if ((checksum & 0xff) == 0) printf(" OK!\n");
//		else						printf(" NG\n");
	
		if (len > 0) {
			PrintPayload(buf);
		}
	}

	return 0;
}

/*******************************************************/
/*******************************************************/
/*******************************************************/
void PrintPayload(const char *payload) {
	time_t		t = time(NULL);
	char		dtNow[64];	
	int			sizeOfPayload;
	int			sizeData;
	int			idx;
	int			sensorIdx,sensorID;
	char		sensorName[256],sensorVal[256],valueUnit[256];

	strftime(dtNow,sizeof(dtNow),"%H:%M",localtime(&t));
	printf("---DataNo %04x %s\n",payload[5] << 8 | payload[6],
		dtNow);

	printf(" Device ID : %02x ",payload[11]);
	printf(" LQI : %d / %.2f [dbm]\n",payload[4],
						(7 * payload[4] - 1970) / 20.);

	idx = 14;
	sizeData = payload[idx++];
//printf("data size:%d\n",sizeData);

	for (int i = 0; i < sizeData; i++ ) {
		for (sensorIdx = 0; sensorIdx < SizeOfSensorList; sensorIdx++) {
			if (payload[idx + 1] == sensorList[sensorIdx].id)
				break;
		}
		if (sensorIdx >= SizeOfSensorList) {
			printf("unknow sennsorID\n");
			break;
		}
		sensorID = sensorList[sensorIdx].id;
		strcpy(sensorName,sensorList[sensorIdx].name);
		strcpy(valueUnit,sensorList[sensorIdx].unit);

		switch (sensorID) {
			case 0x00:					// 磁気
					sprintf(sensorVal,"%d",payload[idx + 4]);
					break;
			case 0x01:					// 温度
					sprintf(sensorVal,"%.2lf",(payload[idx + 4] << 8 
								|  payload[idx + 5]) / 100.);
					break;
			case 0x02:					// 湿度
					sprintf(sensorVal,"%.2lf",(payload[idx + 4] << 8 
								|  payload[idx + 5]) / 100.);
					break;
			case 0x03:					// 照度
					sprintf(sensorVal,"%d",payload[idx + 4] << 24 
								|  payload[idx + 5] << 16
								|  payload[idx + 6] <<  8
								|  payload[idx + 7]);
					break;
			case 0x04:					// 加速度
					sprintf(sensorVal,"X:%dmg,Y:%dmg,Z:%dmg",
						payload[idx + 4] << 8 | payload[idx + 5],
						payload[idx + 6] << 8 | payload[idx + 7],
						payload[idx + 8] << 8 | payload[idx + 9]);
					break;
			case 0x05:					// イベント
					sprintf(sensorVal,"%d",payload[idx+4]);
					break;
			case 0x30:					// ADC
					sprintf(sensorVal,"%d",payload[idx + 4] << 8
								| payload[idx + 5]);
					if (payload[idx + 2] == 8)
						strcpy(sensorName,"電源電圧");
					else 			//if (payload[idx + 2] == 1)
						strcpy(sensorName,"ADC1");
					break;
			default:
//					printf("error");
					break;
		}

		printf("%s:%s%s / ",sensorName,sensorVal,valueUnit);
		idx += 4 + payload[idx + 3];
	}
	printf("\n");
}


/*******************************************************/
/*******************************************************/
/*******************************************************/
int Readln(int handle, char *buffer, int maxSize) {
	int		retVal = 0;
	char	tmpBuf[maxSize];
	char	*pBuf;

	pBuf = buffer;
	while (true) {
		retVal = read(handle,tmpBuf,maxSize);

		if (retVal > 0) {
			for (int i = 0; i < retVal; i++) {
				if (tmpBuf[i] == 0x0d || tmpBuf[i] == 0x0a) {
					goto EXIT;
				}
				*pBuf++ = tmpBuf[i];
			}
		}
	}

EXIT:
	*pBuf = 0x00;

	// ASCII to BINARY
	retVal = pBuf - buffer;
	pBuf = buffer;
	for (int i = 1; i < retVal; i += 2) {
		*pBuf  = (buffer[i] - 0x30) > 10 ? buffer[i] - 0x41 + 10 
				: buffer[i] - 0x30;
		*pBuf  = *pBuf << 4;
		*pBuf += (buffer[i+1] - 0x30) > 10 ? buffer[i+1] - 0x41 + 10 
				: buffer[i+1] - 0x30;
		pBuf++;
	}
	*pBuf = 0x00;

	return pBuf - buffer;
}
