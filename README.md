# Description

Here are some python scripts running with Current Cost sensor (http://www.currentcost.com/) for :
- sending power data from holiday home to your NAS at home on a quarter hour basis
- "debugging" locally what consummes the more power

The data are read from serial XML input according to the specification http://www.currentcost.com/cc128/xml.htm

The sensor reader publishes data to Redis : 
- One consumer stores the data into a Redis list (for a batch to send data every night not implemented yet)
- Another one pushes the data with flask (http://flask.pocoo.org/) and Server Sent Events (http://www.w3.org/TR/2011/WD-eventsource-20110208/) to local http clients for local monitoring.

The 2 scripts (current_cost.py and current_cost_server.py) are hosted an a small Raspberry Pi : http://www.raspberrypi.org/

This is a work in progress.
