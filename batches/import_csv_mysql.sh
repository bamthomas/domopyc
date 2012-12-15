#!/bin/sh

MYSQL=/usr/local/mysql/bin/mysql
USER=test
PASS=test
BASE=test

CREATE_TABLE_SQL='CREATE TABLE IF NOT EXISTS `current_cost` (
  `id` mediumint(9) NOT NULL AUTO_INCREMENT,
  `timestamp` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `watt` int(11) DEFAULT NULL,
  `minutes` int(11) DEFAULT NULL,
  `nb_data` int(11) DEFAULT NULL,
  `temperature` float DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8'

if [ -z "$1" ]
then
    CSV_FILENAME=/share/current_cost/current_cost_`date --date='yesterday' '+%Y-%m-%d'`.csv
else
    CSV_FILENAME=$1
fi

LOAD_DATA_SQL="LOAD data local infile '${CSV_FILENAME}' into table current_cost FIELDS TERMINATED BY ';' LINES TERMINATED BY '\n' ignore 1 lines (timestamp, watt, minutes, nb_data, temperature);"

${MYSQL} -u${USER} -p${PASS} ${BASE} -e "${CREATE_TABLE_SQL}"
${MYSQL} -u${USER} -p${PASS} ${BASE} -e "${LOAD_DATA_SQL}"
if [ $? -eq 0 ]
then
    logger -p local7.info "import of ${CSV_FILENAME} succeded, removing file"
    rm -f ${CSV_FILENAME}
else
    logger -p local7.error "import of ${CSV_FILENAME} failed, leaving file on disk"
fi
