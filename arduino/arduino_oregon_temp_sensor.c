/*
 * from :
 * connectingStuff, Oregon Scientific v2.1 Emitter
 * http://connectingstuff.net/blog/encodage-protocoles-oregon-scientific-sur-arduino/
 *
 * Copyright (C) 2013 olivier.lebrun@gmail.com
 * ---------------
 * and @bam_thomas
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

// DS18S20 Temperature chip i/o
OneWire ds(8);  // on pin 8

// ================= one wire part
byte ONEWIRE_ADDR[8];

void setup_onewire() {
  if ( !ds.search(ONEWIRE_ADDR)) {
    Serial.print("No more addresses.\n");
    ds.reset_search();
    return;
  }
  if ( OneWire::crc8( ONEWIRE_ADDR, 7) != ONEWIRE_ADDR[7]) {
    Serial.print("onewire CRC is not valid!\n");
    return;
  }

  if ( ONEWIRE_ADDR[0] == 0x28) {
    Serial.print("Device DS18B20 found.\n");
  }
  else {
    Serial.print("Device is not recognized: 0x");
    Serial.println(ONEWIRE_ADDR[0],HEX);
    return;
  }
}

float read_temperature() {
  byte i;
  byte present = 0;
  byte data[12];

  ds.reset();
  ds.select(ONEWIRE_ADDR);
  ds.write(0x44,1);         // start conversion, with parasite power on at the end

  delay(1000);     
  
  present = ds.reset();
  ds.select(ONEWIRE_ADDR);    
  ds.write(0xBE);         // Read Scratchpad

  for ( i = 0; i < 9; i++) {
    data[i] = ds.read();
  }

  int high_byte, low_byte, temp_read, sign_bit, sign, temperature_celsius_x_100, temperature_celsius_int_part, temperature_celsius_fract_part;
  float temperature_celsius;
  low_byte = data[0];
  high_byte = data[1];
  temp_read = (high_byte << 8) + low_byte;
  sign_bit = temp_read & 0x8000;  // most sig bit
  sign = 1;
  
  if (sign_bit) {
    temp_read = (temp_read ^ 0xffff) + 1; // 2's comp
    sign = -1;
  }
  temperature_celsius_x_100 = (6 * temp_read) + temp_read / 4;    // multiply by (100 * 0.0625) or 6.25
  temperature_celsius = (float)temperature_celsius_x_100 * sign / 100;
  return temperature_celsius;
}

// ====================== oregon part 
const byte OREGON_TX_PIN = 4;
const unsigned long TIME = 512;
 
#define SEND(BIT) digitalWrite(OREGON_TX_PIN, BIT)
 
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
 
// ================================================
// ================================================

void setup(void) {
  Serial.begin(9600);
  pinMode(OREGON_TX_PIN, OUTPUT);

  Serial.println("\n[Oregon V2.1 encoder]");
 
  SEND(LOW); 
  
  byte ID[] = {0x1A,0x2D};
  setType(OregonMessageBuffer, ID);
  setChannel(OregonMessageBuffer, 0x20);
  setId(OregonMessageBuffer, 0xBB);
  
  setup_onewire();
}

void loop(void) {
  float temperature = read_temperature();
  setBatteryLevel(OregonMessageBuffer, 0); // 0 : low, 1 : high
  setTemperature(OregonMessageBuffer, temperature);
 
  // Calculate the checksum
  calculateAndSetChecksum(OregonMessageBuffer);
 
  // Show the Oregon Message
  Serial.print("sending temp ");
  Serial.println(temperature);
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
  
  delay(5000);
}