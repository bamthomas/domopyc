#!/bin/sh

CREATE_TABLE_SQL='CREATE TABLE `current_cost` (
  `id` mediumint(9) NOT NULL AUTO_INCREMENT,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `watt` int(11) DEFAULT NULL,
  `minutes` int(11) DEFAULT NULL,
  `nb_data` int(11) DEFAULT NULL,
  `temperature` float DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8'

LOAD_DATA_SQL="LOAD data local infile '/share/current_cost/current_cost_2012-12-12.csv' into table current_cost FIELDS TERMINATED BY ';' LINES TERMINATED BY '\n' ignore 1 lines (timestamp, watt, minutes, nb_data, temperature);"

