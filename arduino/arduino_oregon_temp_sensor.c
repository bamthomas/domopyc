/*
 * connectingStuff, Oregon Scientific v2.1 Emitter
 * http://connectingstuff.net/blog/encodage-protocoles-oregon-scientific-sur-arduino/
 *
 * Copyright (C) 2013 olivier.lebrun@gmail.com
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
*/

const byte TX_PIN = 4;
const unsigned long TIME = 512;

#define SEND(BIT) digitalWrite(TX_PIN, BIT)

byte OregonMessageBuffer[9];


inline void sendOregonBit(const uint8_t bitToSend)
{
  SEND(!bitToSend);
  delayMicroseconds(TIME);
  SEND(bitToSend);
  delayMicroseconds(TIME*2);
  SEND(!bitToSend);
  delayMicroseconds(TIME);
}

/**
 * \brief    Send a byte over RF
 * \param    data   byte to send
 */
inline void sendByte(const byte data)
{
  for(int i = 0; i < 8; i++) {
    sendOregonBit(bitRead(data, i));
  }
}

/**
 * \brief    Send a buffer over RF
 * \param    data   Data to send
 * \param    size   size of data to send
 */
void sendData(byte *data, byte size)
{
  for(byte i = 0; i < size; ++i) {
    sendByte(data[i]);
  }
}

/**
 * \brief    Send an Oregon message
 * \param    data   The Oregon message
 */
void sendOregonMessage(byte *data, byte size)
{
    sendPreamble();
    sendData(data, size);
    sendPostamble();
}

/**
 * The preamble consists of 16 "1" bits
 */
inline void sendPreamble(void)
{
  byte preamble[] = {0xFF,0xFF};
  sendData(preamble, 2);
}

/**
 *  The postamble consists of 8 "0" bits
 */
inline void sendPostamble(void)
{
  byte postamble[] = {0x00};
  sendData(postamble, 1);
}


/******************************************************************/
/******************************************************************/
/******************************************************************/

/**
 * \brief    Set the sensor type
 * \param    data       Oregon message
 * \param    type       Sensor type
 */
inline void setType(byte *data, byte* type)
{
  data[0] = type[0];
  data[1] = type[1];
}

/**
 * \brief    Set the sensor channel
 * \param    data       Oregon message
 * \param    channel    Sensor channel (0x10, 0x20, 0x30)
 */
inline void setChannel(byte *data, byte channel)
{
    data[2] = channel;
}

/**
 * \brief    Set the sensor ID
 * \param    data       Oregon message
 * \param    ID         Sensor unique ID
 */
inline void setId(byte *data, byte ID)
{
  data[3] = ID;
}

/**
 * \brief    Set the sensor battery level
 * \param    data       Oregon message
 * \param    level      Battery level (0 = low, 1 = high)
 */
void setBatteryLevel(byte *data, byte level)
{
  if(!level) data[4] = 0x0C;
  else data[4] = 0x00;
}

/**
 * \brief    Set the sensor temperature
 * \param    data       Oregon message
 * \param    temp       the temperature
 */
void setTemperature(byte *data, float temp)
{
  // Set temperature sign
  if(temp < 0)
  {
    data[6] = 0x08;
    temp *= -1;
  }
  else
  {
    data[6] = 0x00;
  }

  // Determine decimal and float part
  int tempInt = (int)temp;
  int td = (int)(tempInt / 10);
  int tf = (int)round((float)((float)tempInt/10 - (float)td) * 10);

  int tempFloat =  (int)round((float)(temp - (float)tempInt) * 10);

  // Set temperature decimal part
  data[5] = (td << 4);
  data[5] |= tf;

  // Set temperature float part
  data[4] |= (tempFloat << 4);
}

/**
 * \brief    Sum data for checksum
 * \param    count      number of bit to sum
 * \param    data       Oregon message
 */
int Sum(byte count, const byte* data)
{
  int s = 0;

  for(byte i = 0; i<count;i++)
  {
    s += (data[i]&0xF0) >> 4;
    s += (data[i]&0xF);
  }

  if(int(count) != count)
    s += (data[count]&0xF0) >> 4;

  return s;
}

/**
 * \brief    Calculate checksum
 * \param    data       Oregon message
 */
void calculateAndSetChecksum(byte* data)
{
    data[8] = ((Sum(8, data) - 0xa) & 0xFF);
}

/******************************************************************/
/******************************************************************/
/******************************************************************/

void setup()
{
  pinMode(TX_PIN, OUTPUT);

  Serial.begin(9600);
  Serial.println("\n[Oregon V2.1 encoder]");

  SEND(LOW);

  byte ID[] = {0x1A,0x2D};
  setType(OregonMessageBuffer, ID);
  setChannel(OregonMessageBuffer, 0x20);
  setId(OregonMessageBuffer, 0xBB);
}

void loop()
{
  setBatteryLevel(OregonMessageBuffer, 0); // 0 : low, 1 : high
  setTemperature(OregonMessageBuffer, 11.2);


  // Calculate the checksum
  calculateAndSetChecksum(OregonMessageBuffer);

  // Show the Oregon Message
  for (byte i = 0; i < sizeof(OregonMessageBuffer); ++i)   {
    Serial.print(OregonMessageBuffer[i] >> 4, HEX);
    Serial.print(OregonMessageBuffer[i] & 0x0F, HEX);
  }
  Serial.print("\n--\n");

  // Send the Message over RF
  sendOregonMessage(OregonMessageBuffer, sizeof(OregonMessageBuffer));
  // Send a "pause"
  SEND(LOW);
  delayMicroseconds(TIME*16);
  // Send a copie of the first message. The v2.1 protocol send the
  // message two time
  sendOregonMessage(OregonMessageBuffer, sizeof(OregonMessageBuffer));

  SEND(LOW);
  delay(60000);
}
