[![Build Status](https://travis-ci.org/bamthomas/DomoPyc.png)](https://travis-ci.org/bamthomas/DomoPyc)
# Goal

This is a framework start, utilities to build a backend for a domotic application.

The idea is that domotic applications should be :
* *event driven*, so we use a data bus (redis at the moment because of its lightweight and convenience)
* *asynchronous*, so we based every IO access (Redis, mysql, web) on python asyncio layer : most of the time, the machine should be idled. A [Raspberry Pi](http://www.raspberrypi.org/) should be able to cope with the load
* *decoupled* : a lot of standards and devices are available and we would like them to coopérate
* *transparent* : we should be able to know what's going on in our home and what is sent on the wire

# Installing 
You must have at least python 3.4. 
For the moment it is a bit pedestrian...

For a raspberry pi with Raspbian:
```
# installing python 3.4
sudo apt-get install build-essential openssl libssl-dev
wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tar.xz
tar xzf Python-3.4.3.tar.xz
./configure
make
sudo make install

# installing pip/virtualenv
sudo easy_install pip
sudo pip install virtualenv

# databases
sudo apt-get install mysql redis-server
mysql -u<admin_user> -p<admin_pass> mysql -e 'create database domopyc'
mysql -u<admin_user> -p<admin_pass> mysql -e  "grant all on domopyc.* to 'domopyc'@'%' identified by 'password'"

# supervisord
sudo easy_install supervisor

# then get the source of domopyc and modify the parameters in domopyc.conf
python setup.py sdist

# and finally install within a virtualenv (that's what I did). In /home/pi
virtualenv --python=python3.4 venv
. venv/bin/activate
pip install domopyc-1.0b17.tar.gz
```

Then I run the main script with supervisor cf [supervisord.conf](install/supervisord.conf), and I start supervisord with init script cf https://github.com/Supervisor/initscripts.

## adding a user

```
# in a python shell
In [4]: hashlib.sha224('my_pass'.encode()).hexdigest()
Out[4]: '0c65c07645b657df12081b26cb954e0f2e3a5ef27755d03090b7bbdc'
```
Then in the domopyc config file, add or update the users section :
```
[users]
my_user=0c65c07645b657df12081b26cb954e0f2e3a5ef27755d03090b7bbdc
```

# Architecture

![Architecture](doc/domopyc.png)

**D**ata **AQ**uisition modules are responsible for reading from sensors (ex from Current Cost http://www.currentcost.com/) or sending events to emitters (ex [RFXtrx433E](http://www.rfxcom.com/epages/78165469.sf/en_GB/?ViewObjectPath=%2FShops%2F78165469)). They send data on the databus on the appropriate channel.

Then subscribers modules process the data. Most of the time, we need to average data, store history, or display live parameters to users.

For example, we could push power data from current cost sensor to a browser every 6 seconds (for "debuging" power consuption), while storing average every 30 minutes into a "cold data" base.

# Current cost

The data are read from serial XML input according to the specification http://www.currentcost.com/cc128/xml.htm


This is a work in progress.
